"""Setup RAG source texts for the knowledge base.

Uses local PDFs first (Ramayana, Mahabharata already in data/).
Downloads remaining texts from Project Gutenberg (public domain, pre-1929).

Usage:
    python data/download_sources.py
"""

import os
import shutil
import urllib.request
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.logger import setup_logger

logger = setup_logger("downloader")

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
RAG_DIR = os.path.join(DATA_DIR, "rag_sources")

# Local PDFs already in data/ — copy to rag_sources/
LOCAL_PDFS = [
    "Ramayana.of.Valmiki.by.Hari.Prasad.Shastri.pdf",
    "Mahabharat.pdf",
]

# Additional texts to download (only what we don't have locally)
REMOTE_SOURCES = [
    {
        "name": "Panchatantra - Arthur Ryder Translation (1925)",
        "filename": "panchatantra_ryder.txt",
        "url": "https://www.gutenberg.org/cache/epub/25545/pg25545.txt",
    },
    {
        "name": "Hitopadesha - Wilkins Translation (1886)",
        "filename": "hitopadesha_wilkins.txt",
        "url": "https://www.gutenberg.org/cache/epub/10824/pg10824.txt",
    },
    {
        "name": "Indian Fairy Tales - Joseph Jacobs (1892)",
        "filename": "indian_fairy_tales_jacobs.txt",
        "url": "https://www.gutenberg.org/cache/epub/7128/pg7128.txt",
    },
]


def setup_sources():
    """Copy local PDFs + download remaining texts to rag_sources/."""
    os.makedirs(RAG_DIR, exist_ok=True)

    # Step 1: Copy local PDFs
    logger.info("=== Local PDFs ===")
    for pdf in LOCAL_PDFS:
        src = os.path.join(DATA_DIR, pdf)
        dst = os.path.join(RAG_DIR, pdf)
        if os.path.exists(dst):
            logger.info(f"  ✓ Already in rag_sources: {pdf}")
            continue
        if os.path.exists(src):
            shutil.copy2(src, dst)
            size_mb = os.path.getsize(dst) / (1024 * 1024)
            logger.info(f"  ✓ Copied: {pdf} ({size_mb:.1f} MB)")
        else:
            logger.warning(f"  ✗ Not found: {src}")

    # Step 2: Download additional texts
    logger.info("=== Remote Downloads ===")
    for source in REMOTE_SOURCES:
        filepath = os.path.join(RAG_DIR, source["filename"])
        if os.path.exists(filepath):
            logger.info(f"  ✓ Already exists: {source['filename']}")
            continue

        logger.info(f"  ↓ Downloading: {source['name']}")
        try:
            urllib.request.urlretrieve(source["url"], filepath)
            size_kb = os.path.getsize(filepath) / 1024
            logger.info(f"    Saved: {source['filename']} ({size_kb:.0f} KB)")
        except Exception as e:
            logger.error(f"    Failed: {e}")
            logger.info(f"    Manual download: {source['url']}")

    # Summary
    files = [f for f in os.listdir(RAG_DIR) if f.endswith((".pdf", ".txt"))]
    logger.info(f"\n=== {len(files)} source texts ready in {RAG_DIR} ===")
    for f in sorted(files):
        size = os.path.getsize(os.path.join(RAG_DIR, f))
        logger.info(f"  {f} ({size/1024:.0f} KB)")
    logger.info("\nNext step: python -m shared.rag_store")


if __name__ == "__main__":
    setup_sources()
