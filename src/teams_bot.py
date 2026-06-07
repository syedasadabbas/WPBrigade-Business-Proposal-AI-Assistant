from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import Optional

from botbuilder.core import ActivityHandler, TurnContext

import config
from src.proposal_generator import ProposalGenerator

logger = logging.getLogger(__name__)

# Patterns that signal the user is asking about the retrieved proposals rather than answering
# the current clarification question.
_PROPOSALS_INQUIRY_RE = re.compile(
    r"\b(tell me (more )?about|more (info|information|detail)|"
    r"what (are|were) (the |those )?proposal|show (me )?the proposal|"
    r"which proposal|found proposal|retrieved proposal|what did you find|"
    r"what proposals?|those proposal)\b",
    re.IGNORECASE,
)


class UserSession:
    AWAITING_REQUIREMENTS = "awaiting_requirements"
    AWAITING_ANSWER = "awaiting_answer"
    GENERATING = "generating"
    IDLE = "idle"

    def __init__(self):
        self.session_id: str = uuid.uuid4().hex
        self.state = self.AWAITING_REQUIREMENTS
        self.requirements: str = ""
        self.retrieved_examples: list = []
        self.gaps: str = ""
        self.clarifications: list = []
        self.pending_questions: list[str] = []
        self.round: int = 0
        self.proposal_text: Optional[str] = None


class ProposalBot(ActivityHandler):
    def __init__(self, generator: ProposalGenerator):
        super().__init__()
        self.generator = generator
        self._sessions: dict[str, UserSession] = {}

    async def on_message_activity(self, turn_context: TurnContext) -> None:
        conversation_id = turn_context.activity.conversation.id
        text = (turn_context.activity.text or "").strip()
        session = self._sessions.setdefault(conversation_id, UserSession())

        # Global commands that work in any state.
        cmd = text.lower()

        if cmd in ("/new", "new", "/restart"):
            self._sessions[conversation_id] = UserSession()
            await turn_context.send_activity(
                "New proposal session started. "
                "Please describe your business proposal requirements."
            )
            return

        if cmd in ("/help", "help"):
            await turn_context.send_activity(self._help_text())
            return

        if cmd in ("/proposals", "proposals"):
            await self._show_proposals(turn_context, session)
            return

        if session.state == UserSession.AWAITING_REQUIREMENTS:
            await self._handle_requirements(turn_context, session, text)
        elif session.state == UserSession.AWAITING_ANSWER:
            await self._handle_answer(turn_context, session, text)
        elif session.state == UserSession.GENERATING:
            await turn_context.send_activity("Still generating your proposal, please wait.")
        else:
            await turn_context.send_activity(
                "Type /new to start creating a business proposal, or /help for usage."
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext) -> None:
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    "Welcome to the Business Proposal AI Assistant.\n\n"
                    "I can help you create professional business proposals by searching our "
                    "historical repository and generating tailored documents.\n\n"
                    + self._help_text()
                )

    async def _handle_requirements(
        self, turn_context: TurnContext, session: UserSession, text: str
    ) -> None:
        if not text:
            await turn_context.send_activity("Please enter your proposal requirements.")
            return

        # Classify intent before committing to the full proposal pipeline.
        # Runs synchronously in a thread to avoid blocking the event loop.
        loop = asyncio.get_event_loop()
        intent = await loop.run_in_executor(
            None, self.generator.ai.classify_intent, text
        )

        if intent == "general_question":
            answer = await loop.run_in_executor(
                None, self.generator.ai.answer_question, text
            )
            await turn_context.send_activity(answer)
            return

        if intent == "proposals_inquiry" and not session.retrieved_examples:
            await turn_context.send_activity(
                "No proposals have been retrieved yet. "
                "Please describe your proposal requirements first and the system will "
                "search the repository automatically."
            )
            return

        session.requirements = text
        session.state = UserSession.GENERATING

        await turn_context.send_activity(
            "Requirements received. Searching the proposal repository and analysing gaps."
        )

        await loop.run_in_executor(None, self._pipeline_step1, session)

        if session.pending_questions:
            session.state = UserSession.AWAITING_ANSWER
            q = session.pending_questions.pop(0)
            session.clarifications.append({"question": q})
            session.round += 1

            found = len(session.retrieved_examples)
            found_msg = (
                f"Found {found} relevant proposal(s) in the repository. "
                f"Use /proposals to see details.\n\n"
                if found else ""
            )
            await turn_context.send_activity(
                f"{found_msg}To generate the best proposal, I need a few more details.\n\n"
                f"Question {session.round}: {q}\n\n"
                "Type /skip to skip this question, or /proposals to review the retrieved examples."
            )
        else:
            await self._finish_proposal(turn_context, session)

    async def _handle_answer(
        self, turn_context: TurnContext, session: UserSession, text: str
    ) -> None:
        # If the user is asking about retrieved proposals rather than answering the question,
        # respond with proposal details and keep the state unchanged.
        if _PROPOSALS_INQUIRY_RE.search(text):
            await self._show_proposals(turn_context, session)
            current_q = next(
                (qa["question"] for qa in reversed(session.clarifications) if "answer" not in qa),
                None,
            )
            if current_q:
                await turn_context.send_activity(
                    f"To continue: Question {session.round}: {current_q}"
                )
            return

        final_answer = "N/A" if text.strip().lower() in ("skip", "/skip") else text
        for qa in reversed(session.clarifications):
            if "answer" not in qa:
                qa["answer"] = final_answer
                break

        if session.pending_questions and session.round < config.MAX_CLARIFICATION_ROUNDS:
            q = session.pending_questions.pop(0)
            session.clarifications.append({"question": q})
            session.round += 1
            await turn_context.send_activity(
                f"Question {session.round}: {q}\n\nType /skip to skip this question."
            )
        else:
            await turn_context.send_activity(
                "Thank you for the additional information. Generating your proposal now."
            )
            await self._finish_proposal(turn_context, session)

    async def _finish_proposal(
        self, turn_context: TurnContext, session: UserSession
    ) -> None:
        session.state = UserSession.GENERATING
        loop = asyncio.get_event_loop()
        proposal_text = await loop.run_in_executor(None, self._generate_proposal, session)
        session.state = UserSession.IDLE
        session.proposal_text = proposal_text

        for chunk in self._split_message(proposal_text, max_len=4000):
            await turn_context.send_activity(chunk)

        # Build download links and save files in the background (best effort).
        download_msg = await loop.run_in_executor(
            None, self._build_download_links, session
        )

        completion_msg = (
            "Proposal generation complete.\n\n"
            "Sections marked [REVIEW NEEDED] require human verification before submission.\n\n"
        )
        if download_msg:
            completion_msg += download_msg + "\n\n"
        completion_msg += "Type /new to create another proposal."

        await turn_context.send_activity(completion_msg)

    async def _show_proposals(self, turn_context: TurnContext, session: UserSession) -> None:
        loop = asyncio.get_event_loop()
        description = await loop.run_in_executor(
            None, self.generator.ai.describe_examples, session.retrieved_examples
        )
        await turn_context.send_activity(description)

    def _pipeline_step1(self, session: UserSession) -> None:
        if self.generator._index_ready:
            session.retrieved_examples = self.generator.search_engine.search_proposals(
                session.requirements, top_k=config.TOP_K_RESULTS
            )

        session.gaps = self.generator.ai.identify_gaps(
            session.requirements, session.retrieved_examples
        )
        questions = self.generator.ai.generate_questions(
            session.requirements,
            session.gaps,
            session.clarifications,
            max_questions=config.MAX_CLARIFICATION_ROUNDS,
        )
        session.pending_questions = questions[:]

    def _generate_proposal(self, session: UserSession) -> str:
        from src.ai_module import ProposalSession
        ps = ProposalSession(
            requirements=session.requirements,
            retrieved_examples=session.retrieved_examples,
            clarifications=[qa for qa in session.clarifications if "answer" in qa],
        )
        return self.generator.ai.generate_proposal(ps)

    @staticmethod
    def _build_download_links(session: UserSession) -> str:
        if not session.proposal_text:
            return ""
        try:
            from src.proposal_exporter import save_proposal
            save_proposal(session.session_id, session.proposal_text)
            base = config.BOT_BASE_URL.rstrip("/")
            sid = session.session_id
            return (
                "Download your proposal:\n"
                f"  Markdown : {base}/download/{sid}/md\n"
                f"  Plain text: {base}/download/{sid}/txt\n"
                f"  PDF       : {base}/download/{sid}/pdf"
            )
        except Exception as exc:
            logger.warning("Failed to build download links: %s", exc)
            return ""

    @staticmethod
    def _split_message(text: str, max_len: int = 4000) -> list[str]:
        chunks = []
        while len(text) > max_len:
            split_at = text.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()
        if text:
            chunks.append(text)
        return chunks

    @staticmethod
    def _help_text() -> str:
        return (
            "Commands:\n"
            "  /new        Start a new proposal\n"
            "  /proposals  Show details of proposals retrieved from the repository\n"
            "  /skip       Skip the current clarification question\n"
            "  /help       Show this help\n\n"
            "How it works:\n"
            "  1. Describe your proposal requirements in plain language.\n"
            "  2. The system searches the repository for relevant past proposals.\n"
            "  3. You will be asked a few questions to fill any gaps.\n"
            "  4. A complete proposal is generated with review annotations.\n\n"
            "You can also ask general questions about business proposals at any time."
        )
