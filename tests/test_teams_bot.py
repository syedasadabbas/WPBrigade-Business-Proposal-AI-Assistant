import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.teams_bot import ProposalBot, UserSession


def _make_bot():
    generator = MagicMock()
    generator._index_ready = False
    generator.ai.identify_gaps.return_value = "Missing: budget"
    generator.ai.generate_questions.return_value = ["What is the budget?"]
    generator.ai.generate_proposal.return_value = "# Proposal\nContent here."
    generator.search_engine.search_proposals.return_value = []
    return ProposalBot(generator)


def _make_context(text: str, conversation_id: str = "conv1"):
    activity = MagicMock()
    activity.text = text
    activity.conversation.id = conversation_id
    activity.recipient.id = "bot"
    ctx = MagicMock()
    ctx.activity = activity
    ctx.send_activity = AsyncMock()
    return ctx


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_help_command():
    bot = _make_bot()
    ctx = _make_context("/help")
    run(bot.on_message_activity(ctx))
    ctx.send_activity.assert_called_once()
    msg = ctx.send_activity.call_args[0][0]
    assert "/new" in msg


def test_new_command_resets_session():
    bot = _make_bot()
    conv_id = "conv2"
    bot._sessions[conv_id] = UserSession()
    bot._sessions[conv_id].state = UserSession.IDLE

    ctx = _make_context("/new", conv_id)
    run(bot.on_message_activity(ctx))
    assert bot._sessions[conv_id].state == UserSession.AWAITING_REQUIREMENTS


def test_requirements_flow():
    bot = _make_bot()
    ctx = _make_context("We need a web portal for project management", "conv3")

    def fake_step1(session):
        session.retrieved_examples = []
        session.gaps = "Missing budget"
        session.pending_questions = ["What is the budget?"]

    bot._pipeline_step1 = fake_step1
    run(bot.on_message_activity(ctx))
    assert ctx.send_activity.call_count >= 1
