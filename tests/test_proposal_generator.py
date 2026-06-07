"""Integration test for ProposalGenerator pipeline (all external calls mocked)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.proposal_generator import ProposalGenerator


def _mock_ai():
    ai = MagicMock()
    ai.analyse_requirements.return_value = "Domain: IT"
    ai.identify_gaps.return_value = "Missing: timeline"
    ai.generate_questions.return_value = ["What is the timeline?"]

    def _gen_proposal(session):
        session.final_proposal = "# Proposal\nContent here..."
        return session.final_proposal

    ai.generate_proposal.side_effect = _gen_proposal
    return ai


@patch("src.proposal_generator.PDFProcessor")
@patch("src.proposal_generator.SearchEngine")
@patch("src.proposal_generator.AIModule")
def test_pipeline_no_clarification(MockAI, MockSE, MockPP):
    MockAI.return_value = _mock_ai()
    MockSE.return_value.load.return_value = False

    gen = ProposalGenerator()
    gen._index_ready = False

    session = gen.run(
        requirements="Build a CRM system",
        ask_question_fn=lambda q: "N/A",
        max_clarification_rounds=0,
    )
    assert session.requirements == "Build a CRM system"
    assert session.final_proposal is not None


@patch("src.proposal_generator.PDFProcessor")
@patch("src.proposal_generator.SearchEngine")
@patch("src.proposal_generator.AIModule")
def test_pipeline_with_clarification(MockAI, MockSE, MockPP):
    ai_mock = _mock_ai()
    # Second call returns no more questions
    ai_mock.generate_questions.side_effect = [["What is the budget?"], []]
    MockAI.return_value = ai_mock
    MockSE.return_value.load.return_value = False

    gen = ProposalGenerator()
    gen._index_ready = False

    answers = iter(["$100k"])
    session = gen.run(
        requirements="Build a CRM system",
        ask_question_fn=lambda q: next(answers, "N/A"),
        max_clarification_rounds=2,
    )
    assert len(session.clarifications) >= 1
