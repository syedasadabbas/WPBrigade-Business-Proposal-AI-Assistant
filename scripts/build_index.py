"""
Build (or rebuild) the FAISS index from all PDFs in data/proposals/.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --force
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pdf_processor import PDFProcessor
from src.search_engine import SearchEngine
import config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    args = parser.parse_args()

    proposals_dir = config.PROPOSALS_DIR
    index_dir = config.INDEX_DIR

    pdfs = list(proposals_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {proposals_dir}. Add PDF files and re-run.")
        sys.exit(0)

    print(f"Found {len(pdfs)} PDFs: {[p.name for p in pdfs]}")

    processor = PDFProcessor(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    engine = SearchEngine(model_name=config.EMBEDDING_MODEL, index_dir=index_dir)

    if not args.force and engine.load():
        print("Index already exists. Use --force to rebuild.")
        return

    proposals = processor.extract_directory(proposals_dir)
    total_chunks = sum(len(p.chunks) for p in proposals)
    print(f"Extracted {total_chunks} chunks from {len(proposals)} proposals.")

    engine.build(proposals)
    print("Index built successfully.")


if __name__ == "__main__":
    main()
