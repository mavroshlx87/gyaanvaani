"""Download free, public-domain mythology texts for the RAG knowledge base.

All texts are public domain (published before 1929) from Project Gutenberg
and Internet Archive. No copyright issues for commercial use.

Usage:
    python data/download_sources.py
"""

import os
import urllib.request
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.logger import setup_logger

logger = setup_logger("downloader")

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rag_sources")

# Public domain texts (all pre-1929, legal for commercial use)
SOURCES = [
    {
        "name": "Ramayana - Griffith Translation (1870)",
        "filename": "ramayana_griffith.txt",
        "url": "https://www.gutenberg.org/cache/epub/24869/pg24869.txt",
        "format": "txt"
    },
    {
        "name": "Mahabharata - Kisari Mohan Ganguli Translation (1883-1896)",
        "filename": "mahabharata_ganguli_vol1.txt",
        "url": "https://www.gutenberg.org/cache/epub/15474/pg15474.txt",
        "format": "txt"
    },
    {
        "name": "Panchatantra - Arthur Ryder Translation (1925)",
        "filename": "panchatantra_ryder.txt",
        "url": "https://www.gutenberg.org/cache/epub/25545/pg25545.txt",
        "format": "txt"
    },
    {
        "name": "Hitopadesha - Wilkins Translation (1886)",
        "filename": "hitopadesha_wilkins.txt",
        "url": "https://www.gutenberg.org/cache/epub/10824/pg10824.txt",
        "format": "txt"
    },
    {
        "name": "Indian Fairy Tales - Joseph Jacobs (1892)",
        "filename": "indian_fairy_tales_jacobs.txt",
        "url": "https://www.gutenberg.org/cache/epub/7128/pg7128.txt",
        "format": "txt"
    },
]


def download_sources():
    """Download all public-domain source texts."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for source in SOURCES:
        filepath = os.path.join(OUTPUT_DIR, source["filename"])

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

    logger.info(f"\nAll texts saved to: {OUTPUT_DIR}")
    logger.info("Next step: python -m shared.rag_store  (to index into ChromaDB)")


if __name__ == "__main__":
    download_sources()
