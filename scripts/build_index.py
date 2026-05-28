#!/usr/bin/env python3
"""
scripts/build_index.py
Build a FAISS vector index from PDFs in data/papers.

Run with the project's venv Python:
  & .venv\Scripts\python.exe scripts/build_index.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path (so imports like `utils` and `rag` work)
ROOT_DIR = str(Path(__file__).resolve().parent.parent)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from utils.config import PAPERS_DIR, VECTORSTORE_DIR
from rag.pdf_loader import load_all_pdfs
from rag.chunker import chunk_pages
from rag.embedder import ResearchEmbedder
from utils.disk_cache import cache_clear


def main():
    print(f"Building index from: {PAPERS_DIR}")
    print(f"Vectorstore dir:    {VECTORSTORE_DIR}")

    emb = ResearchEmbedder(str(VECTORSTORE_DIR))

    try:
        pages = load_all_pdfs(str(PAPERS_DIR))
    except Exception as e:
        print(f"Error loading PDFs: {e}")
        sys.exit(1)

    chunks = chunk_pages(pages)

    if not chunks:
        print("No chunks generated — aborting index build.")
        sys.exit(1)

    emb.build_index(chunks)
    cache_clear()

    print("\n✅ Index build finished successfully.")


if __name__ == '__main__':
    main()
