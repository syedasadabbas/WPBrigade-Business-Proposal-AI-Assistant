from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

_DOWNLOADS_DIR = Path(tempfile.gettempdir()) / "proposal_downloads"


def save_proposal(session_id: str, proposal_text: str) -> dict[str, Path]:
    d = _DOWNLOADS_DIR / session_id
    d.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}

    md_path = d / "proposal.md"
    md_path.write_text(proposal_text, encoding="utf-8")
    paths["md"] = md_path

    txt_path = d / "proposal.txt"
    # Strip Markdown formatting for the plain-text version.
    txt_path.write_text(_strip_markdown(proposal_text), encoding="utf-8")
    paths["txt"] = txt_path

    try:
        pdf_path = _render_pdf(d, proposal_text)
        paths["pdf"] = pdf_path
    except Exception as exc:
        logger.warning("PDF generation failed for session %s: %s", session_id, exc)

    return paths


def _strip_markdown(text: str) -> str:
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\*{1,2}(.+?)\*{1,2}", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\s*[-*]\s+", "- ", text, flags=re.MULTILINE)
    return text


def _sanitise(text: str) -> str:
    """Replace characters outside Latin-1 with their closest ASCII equivalent."""
    replacements = {
        "‘": "'", "’": "'", "“": '"', "”": '"',
        "–": "-", "—": "--", "…": "...", " ": " ",
    }
    for char, sub in replacements.items():
        text = text.replace(char, sub)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def _render_pdf(directory: Path, text: str) -> Path:
    from fpdf import FPDF

    class _PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 12)
            self.cell(0, 10, "Business Proposal", new_x="LMARGIN", new_y="NEXT", align="C")
            self.ln(4)

    pdf = _PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)

    for line in text.splitlines():
        if line.startswith("# "):
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, _sanitise(line[2:]))
            pdf.set_font("Helvetica", size=10)
        elif line.startswith("## "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, _sanitise(line[3:]))
            pdf.set_font("Helvetica", size=10)
        elif line.startswith("### "):
            pdf.set_font("Helvetica", "B", 11)
            pdf.multi_cell(0, 6, _sanitise(line[4:]))
            pdf.set_font("Helvetica", size=10)
        elif line.strip():
            pdf.multi_cell(0, 5, _sanitise(line))
        else:
            pdf.ln(3)

    out = directory / "proposal.pdf"
    pdf.output(str(out))
    return out


def get_file(session_id: str, fmt: str) -> Path | None:
    name_map = {"md": "proposal.md", "txt": "proposal.txt", "pdf": "proposal.pdf"}
    if fmt not in name_map:
        return None
    p = _DOWNLOADS_DIR / session_id / name_map[fmt]
    return p if p.exists() else None
