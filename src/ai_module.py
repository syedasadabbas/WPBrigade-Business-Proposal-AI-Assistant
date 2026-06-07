from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import anthropic

import config


@dataclass
class ConversationTurn:
    role: str
    content: str


@dataclass
class ProposalSession:
    requirements: str
    retrieved_examples: list[dict] = field(default_factory=list)
    clarifications: list[dict] = field(default_factory=list)
    history: list[ConversationTurn] = field(default_factory=list)
    final_proposal: Optional[str] = None


class AIModule:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.model = config.CLAUDE_MODEL

    def analyse_requirements(self, requirements: str) -> str:
        prompt = (
            "You are an expert business proposal analyst.\n"
            "Analyse the following new business proposal requirements and extract:\n"
            "- Industry / domain\n"
            "- Key objectives\n"
            "- Deliverables mentioned\n"
            "- Budget / timeline signals (if any)\n"
            "- Any ambiguities\n\n"
            f"Requirements:\n{requirements}"
        )
        return self._complete(prompt)

    def identify_gaps(self, requirements: str, examples: list[dict]) -> str:
        prompt = (
            "You are reviewing a new business proposal request against similar past proposals.\n\n"
            f"NEW REQUIREMENTS:\n{requirements}\n\n"
            f"RETRIEVED EXAMPLES:\n{self._format_examples(examples)}\n\n"
            "Identify:\n"
            "1. What information from the examples is relevant to the new request.\n"
            "2. What critical information is missing from the new requirements.\n"
            "3. Any conflicts or ambiguities.\n\n"
            "Be concise and structured."
        )
        return self._complete(prompt)

    def generate_questions(
        self,
        requirements: str,
        gaps: str,
        already_answered: list[dict],
        max_questions: int = 3,
    ) -> List[str]:
        answered_text = ""
        if already_answered:
            answered_text = "\n\nALREADY ANSWERED:\n" + "\n".join(
                f"Q: {qa['question']}\nA: {qa['answer']}" for qa in already_answered
            )

        prompt = (
            "You are helping create a business proposal and need to gather missing information.\n\n"
            f"ORIGINAL REQUIREMENTS:\n{requirements}\n\n"
            f"IDENTIFIED GAPS:\n{gaps}"
            f"{answered_text}\n\n"
            f"Generate at most {max_questions} specific, concise questions to fill the most critical gaps.\n"
            "Output only the questions, one per line, numbered."
        )
        raw = self._complete(prompt)
        questions = []
        for line in raw.splitlines():
            line = line.strip()
            if line and line[0].isdigit():
                question = line.split(".", 1)[-1].strip()
                if question:
                    questions.append(question)
        return questions[:max_questions]

    def classify_intent(self, text: str) -> str:
        """Classify a user message as: proposal_request | proposals_inquiry | general_question."""
        prompt = (
            "Classify the following message into exactly one label:\n"
            "  proposal_request   — the user wants to create a new business proposal\n"
            "  proposals_inquiry  — the user is asking about previously retrieved/found proposals\n"
            "  general_question   — any other question, conversation, or off-topic request\n\n"
            f"Message: {text}\n\n"
            "Reply with only the label, nothing else."
        )
        result = self._complete(prompt, max_tokens=15).lower().strip()
        for label in ("proposal_request", "proposals_inquiry", "general_question"):
            if label in result:
                return label
        return "proposal_request"

    def answer_question(self, question: str, context: str = "") -> str:
        ctx_block = f"\nCONTEXT:\n{context}\n" if context else ""
        prompt = (
            "You are a helpful business proposal assistant. "
            "Answer the following question concisely. "
            "If the question is unrelated to business proposals, politely say so and "
            "remind the user what you can help with."
            f"{ctx_block}\n"
            f"Question: {question}"
        )
        return self._complete(prompt, max_tokens=512)

    def describe_examples(self, examples: list[dict]) -> str:
        if not examples:
            return "No relevant proposals were found in the repository for your query."
        lines = ["Retrieved proposals from the repository:\n"]
        for i, ex in enumerate(examples, 1):
            score_pct = int(ex["score"] * 100)
            lines.append(f"{i}. {ex['filename']}  (relevance: {score_pct}%)")
            excerpts = ex.get("excerpts", [])
            if excerpts:
                snippet = excerpts[0][:400].replace("\n", " ").strip()
                lines.append(f"   Preview: {snippet}...")
        return "\n".join(lines)

    def generate_proposal(self, session: ProposalSession) -> str:
        clarifications_text = ""
        if session.clarifications:
            clarifications_text = "\nUSER-PROVIDED CLARIFICATIONS:\n" + "\n".join(
                f"Q: {qa['question']}\nA: {qa['answer']}" for qa in session.clarifications
            )

        prompt = (
            "You are an expert business proposal writer. "
            "Create a comprehensive, professional business proposal based on the information below.\n\n"
            "INSTRUCTIONS:\n"
            "- Follow standard business proposal structure: Executive Summary, Problem Statement, "
            "Proposed Solution, Deliverables, Timeline, Budget, Team, Terms.\n"
            "- Incorporate relevant elements from the retrieved examples.\n"
            "- Mark any section where information is uncertain or missing with "
            "[REVIEW NEEDED: <reason>] annotations inline.\n"
            "- Use realistic placeholder values where data is absent and annotate them.\n\n"
            f"NEW PROPOSAL REQUIREMENTS:\n{session.requirements}"
            f"{clarifications_text}\n\n"
            f"RELEVANT PAST PROPOSALS (for reference):\n{self._format_examples(session.retrieved_examples)}\n\n"
            "Generate the full proposal now."
        )
        proposal = self._complete(prompt, max_tokens=4096)
        session.final_proposal = proposal
        return proposal

    def _complete(self, prompt: str, max_tokens: int = 1024) -> str:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    @staticmethod
    def _format_examples(examples: list[dict]) -> str:
        if not examples:
            return "No relevant examples found."
        parts = []
        for i, ex in enumerate(examples, 1):
            excerpts = "\n---\n".join(ex.get("excerpts", [])[:3])
            parts.append(f"[Example {i}: {ex['filename']} | relevance={ex['score']:.2f}]\n{excerpts}")
        return "\n\n".join(parts)
