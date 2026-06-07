from __future__ import annotations

import logging

import aiohttp
from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext, BotAdapter
from botbuilder.schema import Activity, ResourceResponse
from botframework.connector.auth import MicrosoftAppCredentials
from botframework.connector import ConnectorClient

import config
from src.proposal_generator import ProposalGenerator
from src.teams_bot import ProposalBot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_PLACEHOLDER = {"", "your_teams_app_id_here", "your_teams_app_password_here"}
_app_id = config.TEAMS_APP_ID if config.TEAMS_APP_ID not in _PLACEHOLDER else ""
_app_password = config.TEAMS_APP_PASSWORD if config.TEAMS_APP_PASSWORD not in _PLACEHOLDER else ""
_dev_mode = not _app_id


class _Adapter(BotFrameworkAdapter):
    """
    In production (Azure credentials present): standard Bot Framework auth.
    In development (no credentials): bypasses JWT validation and sends replies
    directly via HTTP so the Bot Framework Emulator works without Azure.
    """

    def _make_connector_client(self, service_url: str) -> ConnectorClient:
        return ConnectorClient(MicrosoftAppCredentials("", ""), base_url=service_url)

    async def process_activity(self, activity: Activity, auth_header: str, callback):
        if not _dev_mode:
            return await super().process_activity(activity, auth_header, callback)

        if activity.service_url:
            MicrosoftAppCredentials.trust_service_url(activity.service_url)

        turn_context = TurnContext(self, activity)
        turn_context.turn_state[BotAdapter.BOT_CONNECTOR_CLIENT_KEY] = (
            self._make_connector_client(activity.service_url)
        )
        return await self.run_pipeline(turn_context, callback)

    async def send_activities(self, context: TurnContext, activities):
        if not _dev_mode:
            return await super().send_activities(context, activities)

        # Post replies directly to the emulator to avoid the async/sync mismatch
        # in newer botframework-connector versions.
        service_url = (context.activity.service_url or "").rstrip("/")
        conv_id = context.activity.conversation.id
        responses = []

        for activity in activities:
            if activity.type == "endOfConversation":
                responses.append(ResourceResponse(id=""))
                continue

            url = f"{service_url}/v3/conversations/{conv_id}/activities"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        json=activity.serialize(),
                        headers={"Content-Type": "application/json"},
                    ) as resp:
                        try:
                            data = await resp.json(content_type=None)
                            responses.append(ResourceResponse(id=data.get("id", "")))
                        except Exception:
                            responses.append(ResourceResponse(id=""))
            except Exception as exc:
                logger.error("Failed to send activity to %s: %s", url, exc)
                responses.append(ResourceResponse(id=""))

        return responses


adapter = _Adapter(BotFrameworkAdapterSettings(app_id=_app_id, app_password=_app_password))


async def _on_error(context, error):
    logger.exception("Bot turn error: %s", error, exc_info=error)


adapter.on_turn_error = _on_error

_generator: ProposalGenerator | None = None
_bot: ProposalBot | None = None


async def messages(req: web.Request) -> web.Response:
    if "application/json" not in req.content_type:
        return web.Response(status=415)

    try:
        body = await req.json()
        activity = Activity().deserialize(body)
        auth_header = req.headers.get("Authorization", "")
        response = await adapter.process_activity(activity, auth_header, _bot.on_turn)
        if response:
            return web.json_response(data=response.body, status=response.status)
        return web.Response(status=201)
    except Exception as exc:
        logger.exception("Error processing activity: %s", exc)
        return web.Response(status=500)


async def download(req: web.Request) -> web.Response:
    session_id = req.match_info["session_id"]
    fmt = req.match_info["fmt"]

    valid_formats = {"md", "txt", "pdf"}
    if fmt not in valid_formats:
        return web.Response(status=400, text=f"Invalid format '{fmt}'. Use: md, txt, pdf.")

    from src.proposal_exporter import get_file
    path = get_file(session_id, fmt)

    if path is None:
        # Give a helpful message so the user knows what went wrong.
        logger.warning("Download requested for missing file: session=%s fmt=%s", session_id, fmt)
        return web.Response(
            status=404,
            text=(
                f"Proposal file '{fmt}' not found for this session.\n"
                "The file may have been cleared after a server restart. "
                "Generate a new proposal to get fresh download links."
            ),
        )

    content_type_map = {
        "md":  "text/markdown; charset=utf-8",
        "txt": "text/plain; charset=utf-8",
        "pdf": "application/pdf",
    }
    headers = {
        "Content-Disposition": f'attachment; filename="proposal.{fmt}"',
        "Content-Type": content_type_map[fmt],
    }
    return web.FileResponse(path=path, headers=headers)


async def health(req: web.Request) -> web.Response:
    return web.json_response({
        "status": "ok",
        "index_ready": _generator._index_ready if _generator else False,
        "mode": "development" if _dev_mode else "production",
    })


def create_app() -> web.Application:
    app = web.Application()
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/health", health)
    app.router.add_get("/download/{session_id}/{fmt}", download)
    return app


async def on_startup(app: web.Application) -> None:
    global _generator, _bot
    logger.info("Mode: %s", "development" if _dev_mode else "production")
    logger.info("Loading proposal index...")
    _generator = ProposalGenerator()
    _generator.ensure_index()
    _bot = ProposalBot(_generator)
    logger.info("Bot ready. Index ready: %s", _generator._index_ready)


if __name__ == "__main__":
    app = create_app()
    app.on_startup.append(on_startup)
    logger.info("Starting on port %d", config.TEAMS_BOT_PORT)
    web.run_app(app, host="0.0.0.0", port=config.TEAMS_BOT_PORT)
