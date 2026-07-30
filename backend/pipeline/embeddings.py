"""
PaperVerify — Stage 3: Embeddings + Vector Store.

Generates embeddings using sentence-transformers and stores them in ChromaDB.
Features:
- SHA-256 based caching (re-upload same PDF → skip re-embedding)
- Short paper bypass (< 5 pages → skip retrieval, process whole doc)
- Lazy model loading (singleton)
"""
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import CACHE_DIR, SHORT_PAPER_THRESHOLD
from models.schemas import Chunk
from utils.logging_util import logger

# ── Globals ───────────────────────────────────────────────────────────
_embedding_model = None
_chroma_client = None


def _get_embedding_model():
    """Lazy-load the sentence-transformer model (singleton)."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: all-MiniLM-L6-v2 ...")
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Embedding model loaded.")
    return _embedding_model


def _get_chroma_client() -> chromadb.ClientAPI:
    """Get or create the ChromaDB client."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.Client(ChromaSettings(anonymized_telemetry=False))
        logger.info("ChromaDB client initialized (in-memory)")
    return _chroma_client


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(8192), b""):
            sha256.update(block)
    return sha256.hexdigest()


def _get_cache_path(file_hash: str) -> Path:
    """Get the cache file path for a given file hash."""
    return CACHE_DIR / f"{file_hash}.json"


def _load_cached_embeddings(file_hash: str) -> list[list[float]] | None:
    """Load cached embeddings if they exist."""
    cache_path = _get_cache_path(file_hash)
    if cache_path.exists():
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            logger.info(f"Loaded cached embeddings ({len(data)} vectors)")
            return data
        except (json.JSONDecodeError, IOError):
            logger.warning("Cache file corrupted, will re-embed")
            return None
    return None


def _save_embeddings_cache(file_hash: str, embeddings: list[list[float]]):
    """Save embeddings to cache."""
    cache_path = _get_cache_path(file_hash)
    with open(cache_path, "w") as f:
        json.dump(embeddings, f)
    logger.info(f"Saved {len(embeddings)} embeddings to cache")


async def embed_and_store(
    chunks: list[Chunk],
    session_id: str,
    pdf_path: Path,
    total_pages: int,
) -> tuple[str, bool]:
    """
    Generate embeddings and store in ChromaDB.

    Args:
        chunks: List of text chunks to embed.
        session_id: Session identifier (used as collection name).
        pdf_path: Path to the PDF (for hash-based caching).
        total_pages: Total number of pages in the document.

    Returns:
        (collection_name, is_short_paper) tuple.
    """
    is_short_paper = total_pages < SHORT_PAPER_THRESHOLD
    if is_short_paper:
        logger.info(
            f"Short paper ({total_pages} pages) — will skip retrieval, "
            "process whole doc directly"
        )

    # Check cache
    file_hash = compute_file_hash(pdf_path)
    cached = _load_cached_embeddings(file_hash)

    # Generate embeddings
    if cached and len(cached) == len(chunks):
        embeddings = cached
    else:
        model = _get_embedding_model()
        texts = [chunk.text for chunk in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        raw_embeddings = model.encode(texts, show_progress_bar=False)
        embeddings = [emb.tolist() for emb in raw_embeddings]
        _save_embeddings_cache(file_hash, embeddings)

    # Store in ChromaDB
    client = _get_chroma_client()

    # Delete existing collection if it exists (re-processing)
    try:
        client.delete_collection(name=session_id)
    except Exception:
        pass

    collection = client.create_collection(
        name=session_id,
        metadata={"hnsw:space": "cosine"},
    )

    # Add all chunks with metadata
    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        embeddings=embeddings,
        documents=[chunk.text for chunk in chunks],
        metadatas=[
            {
                "page_number": chunk.page_number,
                "section_guess": chunk.section_guess,
                "word_count": chunk.word_count,
                "chunk_id": chunk.chunk_id,
            }
            for chunk in chunks
        ],
    )

    logger.info(
        f"Stored {len(chunks)} chunks in ChromaDB collection '{session_id}'"
    )

    return session_id, is_short_paper


def get_collection(session_id: str):
    """Get a ChromaDB collection by session ID."""
    client = _get_chroma_client()
    return client.get_collection(name=session_id)


def query_similar(session_id: str, query_text: str, n_results: int = 5) -> list[dict]:
    """Query similar chunks from the collection."""
    model = _get_embedding_model()
    query_embedding = model.encode([query_text])[0].tolist()

    collection = get_collection(session_id)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
    )

    matches = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            matches.append({
                "text": doc,
                "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                "distance": results["distances"][0][i] if results["distances"] else 0,
            })

    return matches


def get_claim_embeddings(session_id: str, claims_texts: list[str]) -> list[list[float]]:
    """Generate embeddings for claim texts (used for concept map clustering)."""
    model = _get_embedding_model()
    raw = model.encode(claims_texts, show_progress_bar=False)
    return [emb.tolist() for emb in raw]


def cleanup_collection(session_id: str):
    """Delete a ChromaDB collection."""
    try:
        client = _get_chroma_client()
        client.delete_collection(name=session_id)
        logger.info(f"Deleted ChromaDB collection '{session_id}'")
    except Exception:
        pass
