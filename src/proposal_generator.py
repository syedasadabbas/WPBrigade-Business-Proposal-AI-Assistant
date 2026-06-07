from __future__ import annotations

from pathlib import Path
from typing import Callable

import config
from src.ai_module import AIModule, ProposalSession
from src.pdf_processor import PDFProcessor
from src.search_engine import SearchEngine


class ProposalGenerator:
    def __init__(self):
        self.processor = PDFProcessor(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP,
        )
        self.search_engine = SearchEngine(
            model_name=config.EMBEDDING_MODEL,
            index_dir=config.INDEX_DIR,
        )
        self.ai = AIModule()
        self._index_ready = False

    def ensure_index(self, force_rebuild: bool = False) -> None:
        if not force_rebuild and self.search_engine.load():
            self._index_ready = True
            return

        proposals = self.processor.extract_directory(config.PROPOSALS_DIR)
        if not proposals:
            print("No PDFs found in data/proposals/. Index not built.")
            self._index_ready = False
            return

        self.search_engine.build(proposals)
        self._index_ready = True

    def run(
        self,
        requirements: str,
        ask_question_fn: Callable[[str], str],
        max_clarification_rounds: int = config.MAX_CLARIFICATION_ROUNDS,
    ) -> ProposalSession:
        session = ProposalSession(requirements=requirements)

        if self._index_ready:
            session.retrieved_examples = self.search_engine.search_proposals(
                requirements, top_k=config.TOP_K_RESULTS
            )

        gaps = self.ai.identify_gaps(requirements, session.retrieved_examples)

        for round_num in range(max_clarification_rounds):
            questions = self.ai.generate_questions(
                requirements, gaps, session.clarifications, max_questions=3
            )
            if not questions:
                break

            for q in questions:
                answer = ask_question_fn(q)
                session.clarifications.append({"question": q, "answer": answer})

        self.ai.generate_proposal(session)
        return session
