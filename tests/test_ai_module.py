"""Tests for AIModule — mocks the Anthropic client."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ai_module import AIModule, ProposalSession


def _mock_client(response_text: str = "Mock AI response"):
    content_block = MagicMock()
    content_block.text = response_text
    msg = MagicMock()
    msg.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = msg
    return client


@patch("src.ai_module.anthropic.Anthropic")
def test_analyse_requirements(MockAnthropic):
    MockAnthropic.return_value = _mock_client("Industry: Tech")
    ai = AIModule()
    result = ai.analyse_requirements("Build a web app for healthcare")
    assert "Industry" in result or result == "Industry: Tech"


@patch("src.ai_module.anthropic.Anthropic")
def test_identify_gaps(MockAnthropic):
    MockAnthropic.return_value = _mock_client("Missing: budget info")
    ai = AIModule()
    result = ai.identify_gaps("Need a mobile app", [])
    assert isinstance(result, str)


@patch("src.ai_module.anthropic.Anthropic")
def test_generate_questions(MockAnthropic):
    MockAnthropic.return_value = _mock_client("1. What is the budget?\n2. What is the timeline?")
    ai = AIModule()
    questions = ai.generate_questions("Build an app", "Missing budget", [], max_questions=3)
    assert len(questions) <= 3
    assert all(isinstance(q, str) for q in questions)


@patch("src.ai_module.anthropic.Anthropic")
def test_generate_proposal(MockAnthropic):
    proposal_text = "# Executive Summary\nThis proposal covers..."
    MockAnthropic.return_value = _mock_client(proposal_text)
    ai = AIModule()
    session = ProposalSession(
        requirements="Build an e-commerce site",
        retrieved_examples=[],
        clarifications=[{"question": "Budget?", "answer": "$50,000"}],
    )
    result = ai.generate_proposal(session)
    assert "Executive Summary" in result
    assert session.final_proposal == result
