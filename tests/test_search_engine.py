import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_processor import Proposal, ProposalChunk
from src.search_engine import SearchEngine


def _make_proposals():
    chunks = [
        ProposalChunk("p1", "proposal1.pdf", 1, 0, "AI software development services for healthcare"),
        ProposalChunk("p1", "proposal1.pdf", 1, 1, "Cloud infrastructure and DevOps automation"),
        ProposalChunk("p2", "proposal2.pdf", 1, 0, "Marketing campaign for e-commerce retail brand"),
    ]
    p1 = Proposal("p1", "proposal1.pdf", "...", 1, {}, chunks[:2])
    p2 = Proposal("p2", "proposal2.pdf", "...", 1, {}, chunks[2:])
    return [p1, p2]


def _patch_ml(vecs: np.ndarray):
    """Patch the module-level ML globals used by SearchEngine."""
    import src.search_engine as se
    mock_model = MagicMock()
    mock_model.encode.return_value = vecs
    se._SentenceTransformer = lambda name: mock_model
    se._faiss = __import__("faiss")
    se._load_ml_deps = lambda: None
    return mock_model


def test_build_and_search(tmp_path):
    vecs = np.random.rand(10, 8).astype("float32")
    mock_model = _patch_ml(vecs[:3])

    engine = SearchEngine(model_name="mock", index_dir=tmp_path)
    engine.build(_make_proposals())

    mock_model.encode.return_value = vecs[3:4]
    results = engine.search("software development", top_k=2)
    assert len(results) <= 2
    assert all(r.score >= 0 for r in results)


def test_persist_and_reload(tmp_path):
    vecs = np.random.rand(10, 8).astype("float32")
    _patch_ml(vecs[:3])

    engine = SearchEngine(model_name="mock", index_dir=tmp_path)
    engine.build(_make_proposals())

    engine2 = SearchEngine(model_name="mock", index_dir=tmp_path)
    assert engine2.load() is True
    assert len(engine2._chunks) == 3
