from __future__ import annotations

import pickle
from pathlib import Path
from typing import List

import numpy as np

from src.pdf_processor import Proposal, ProposalChunk

# ML dependencies are loaded on first instantiation to avoid loading torch at import time.
_faiss = None
_SentenceTransformer = None


def _load_ml_deps():
    global _faiss, _SentenceTransformer
    if _faiss is None:
        import faiss as _f
        from sentence_transformers import SentenceTransformer as _ST
        _faiss = _f
        _SentenceTransformer = _ST


class SearchResult:
    def __init__(self, chunk: ProposalChunk, score: float):
        self.chunk = chunk
        self.score = score

    def __repr__(self) -> str:
        return f"SearchResult(file={self.chunk.filename}, page={self.chunk.page}, score={self.score:.3f})"


class SearchEngine:
    def __init__(self, model_name: str, index_dir: Path):
        _load_ml_deps()
        self.model = _SentenceTransformer(model_name)
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._index = None
        self._chunks: list[ProposalChunk] = []

    def build(self, proposals: List[Proposal]) -> None:
        all_chunks: list[ProposalChunk] = []
        for proposal in proposals:
            all_chunks.extend(proposal.chunks)

        if not all_chunks:
            raise ValueError("No chunks found — check PDF extraction.")

        print(f"Encoding {len(all_chunks)} chunks...")
        embeddings = self._encode([c.text for c in all_chunks])

        dim = embeddings.shape[1]
        index = _faiss.IndexFlatIP(dim)
        _faiss.normalize_L2(embeddings)
        index.add(embeddings)

        self._index = index
        self._chunks = all_chunks
        self._save()
        print(f"Index built: {len(all_chunks)} chunks, dim={dim}.")

    def load(self) -> bool:
        index_path = self.index_dir / "faiss.index"
        chunks_path = self.index_dir / "chunks.pkl"
        if not index_path.exists() or not chunks_path.exists():
            return False
        _load_ml_deps()
        self._index = _faiss.read_index(str(index_path))
        with open(chunks_path, "rb") as f:
            self._chunks = pickle.load(f)
        print(f"Index loaded: {len(self._chunks)} chunks.")
        return True

    def _save(self) -> None:
        _faiss.write_index(self._index, str(self.index_dir / "faiss.index"))
        with open(self.index_dir / "chunks.pkl", "wb") as f:
            pickle.dump(self._chunks, f)

    def search(self, query: str, top_k: int = 3) -> List[SearchResult]:
        if self._index is None:
            raise RuntimeError("Index not built or loaded.")

        q_emb = self._encode([query])
        _faiss.normalize_L2(q_emb)
        scores, indices = self._index.search(q_emb, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append(SearchResult(chunk=self._chunks[idx], score=float(score)))
        return results

    def search_proposals(self, query: str, top_k: int = 3) -> list[dict]:
        raw = self.search(query, top_k=top_k * 4)
        seen: dict[str, dict] = {}
        for r in raw:
            pid = r.chunk.proposal_id
            if pid not in seen:
                seen[pid] = {
                    "proposal_id": pid,
                    "filename": r.chunk.filename,
                    "score": r.score,
                    "excerpts": [],
                }
            seen[pid]["excerpts"].append(r.chunk.text)
            seen[pid]["score"] = max(seen[pid]["score"], r.score)

        return sorted(seen.values(), key=lambda x: x["score"], reverse=True)[:top_k]

    def _encode(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False).astype("float32")
