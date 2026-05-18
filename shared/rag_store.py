"""RAG knowledge base for mythological source texts.

Uses ChromaDB (free, local vector store) to index PDF translations of
Ramayana, Mahabharata, etc. Used by the validator for fact-checking.

Setup:
  1. Run: python data/download_sources.py  (auto-downloads public domain texts)
  2. Run: python -m shared.rag_store       (indexes into ChromaDB, one-time)
  3. Validator queries this store automatically

Also supports manually placed PDF/TXT files in data/rag_sources/
"""

import os
import chromadb
from chromadb.utils import embedding_functions
from shared.logger import setup_logger

logger = setup_logger("rag_store")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rag_sources")
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma_db")

# ChromaDB's default embedding function (all-MiniLM-L6-v2, ~80MB, runs on CPU)
_ef = embedding_functions.DefaultEmbeddingFunction()


def get_collection():
    """Get or create the mythology collection."""
    client = chromadb.PersistentClient(path=DB_DIR)
    return client.get_or_create_collection("mythology_sources", embedding_function=_ef)


def index_sources():
    """One-time: parse all TXT/PDF files in data/rag_sources/ and index into ChromaDB."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DB_DIR, exist_ok=True)

    files = [f for f in os.listdir(DATA_DIR) if f.endswith((".txt", ".pdf"))]
    if not files:
        logger.warning(f"No files found in {DATA_DIR}.")
        logger.info("Run first: python data/download_sources.py")
        return

    collection = get_collection()
    if collection.count() > 0:
        logger.info(f"RAG store already has {collection.count()} chunks. Skipping re-index.")
        logger.info("Delete data/chroma_db/ to force re-index.")
        return

    total_chunks = 0

    for filename in files:
        path = os.path.join(DATA_DIR, filename)
        logger.info(f"Indexing: {filename}")

        if filename.endswith(".txt"):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            chunks = _chunk_text(text, chunk_size=500, overlap=50)
            for i, chunk in enumerate(chunks):
                if len(chunk.strip()) < 50:
                    continue
                collection.add(
                    documents=[chunk],
                    ids=[f"{filename}_c{i}"],
                    metadatas=[{"source": filename}]
                )
                total_chunks += 1

        elif filename.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text or len(text.strip()) < 50:
                    continue
                chunks = _chunk_text(text, chunk_size=500, overlap=50)
                for i, chunk in enumerate(chunks):
                    collection.add(
                        documents=[chunk],
                        ids=[f"{filename}_p{page_num}_c{i}"],
                        metadatas=[{"source": filename, "page": page_num}]
                    )
                    total_chunks += 1

    logger.info(f"Indexed {total_chunks} chunks from {len(files)} files")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def query(question: str, n_results: int = 5) -> str:
    """Query the RAG store and return relevant text passages."""
    collection = get_collection()
    if collection.count() == 0:
        return "RAG store is empty. Add PDFs to data/rag_sources/ and run: python -m shared.rag_store"

    results = collection.query(query_texts=[question], n_results=n_results)
    passages = results.get("documents", [[]])[0]
    return "\n---\n".join(passages) if passages else "No relevant passages found."


if __name__ == "__main__":
    index_sources()
