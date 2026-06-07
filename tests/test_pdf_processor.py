"""Tests for PDF processor (uses a synthetic in-memory PDF)."""
import io
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_processor import PDFProcessor, Proposal


def _make_dummy_pdf(tmp_path: Path, filename: str, content: str) -> Path:
    """Create a minimal single-page PDF using reportlab if available, else fpdf2."""
    pdf_path = tmp_path / filename
    try:
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(str(pdf_path))
        # Write content as multiple text lines
        y = 750
        for line in content.split("\n"):
            c.drawString(50, y, line)
            y -= 15
        c.save()
    except ImportError:
        try:
            from fpdf import FPDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=12)
            for line in content.split("\n"):
                pdf.cell(200, 10, txt=line, ln=True)
            pdf.output(str(pdf_path))
        except ImportError:
            pytest.skip("Neither reportlab nor fpdf2 installed — skipping PDF test")
    return pdf_path


def test_extract_chunks(tmp_path):
    content = " ".join([f"word{i}" for i in range(200)])
    pdf_path = _make_dummy_pdf(tmp_path, "test.pdf", content)

    processor = PDFProcessor(chunk_size=50, chunk_overlap=10)
    proposal = processor.extract(pdf_path)

    assert isinstance(proposal, Proposal)
    assert proposal.proposal_id == "test"
    assert len(proposal.chunks) > 0
    assert all(c.proposal_id == "test" for c in proposal.chunks)


def test_extract_directory_empty(tmp_path):
    processor = PDFProcessor()
    results = processor.extract_directory(tmp_path)
    assert results == []
