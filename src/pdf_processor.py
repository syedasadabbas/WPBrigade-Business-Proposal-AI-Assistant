from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import pdfplumber


@dataclass
class ProposalChunk:
    proposal_id: str
    filename: str
    page: int
    chunk_index: int
    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Proposal:
    proposal_id: str
    filename: str
    full_text: str
    pages: int
    metadata: dict = field(default_factory=dict)
    chunks: List[ProposalChunk] = field(default_factory=list)


class PDFProcessor:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract(self, pdf_path: Path) -> Proposal:
        pages_text: list[str] = []
        metadata: dict = {}

        with pdfplumber.open(pdf_path) as pdf:
            metadata["pages"] = len(pdf.pages)
            if pdf.metadata:
                metadata.update({k: v for k, v in pdf.metadata.items() if v})
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages_text.append(text)

        full_text = self._clean("\n".join(pages_text))
        proposal = Proposal(
            proposal_id=pdf_path.stem,
            filename=pdf_path.name,
            full_text=full_text,
            pages=len(pages_text),
            metadata=metadata,
        )
        proposal.chunks = self._chunk(proposal, pages_text)
        return proposal

    def extract_directory(self, directory: Path) -> List[Proposal]:
        proposals = []
        for pdf_path in sorted(directory.glob("*.pdf")):
            try:
                proposals.append(self.extract(pdf_path))
            except Exception as exc:
                print(f"Failed to process {pdf_path.name}: {exc}")
        return proposals

    def _clean(self, text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()

    def _chunk(self, proposal: Proposal, pages_text: list[str]) -> List[ProposalChunk]:
        chunks: list[ProposalChunk] = []
        chunk_idx = 0

        for page_num, page_text in enumerate(pages_text, start=1):
            words = page_text.split()
            start = 0
            while start < len(words):
                end = min(start + self.chunk_size, len(words))
                chunk_text = " ".join(words[start:end]).strip()
                if chunk_text:
                    chunks.append(
                        ProposalChunk(
                            proposal_id=proposal.proposal_id,
                            filename=proposal.filename,
                            page=page_num,
                            chunk_index=chunk_idx,
                            text=chunk_text,
                            metadata={"source": proposal.filename, "page": page_num},
                        )
                    )
                    chunk_idx += 1
                start += self.chunk_size - self.chunk_overlap

        return chunks
