"""Phase 4 RAG package: chunk, Chroma, hybrid retrieve, gate."""

from src.rag.build import build_kb
from src.rag.chunk import Chunk, chunk_document, chunk_documents, chunk_text
from src.rag.models import RetrievalHit
from src.rag.retrieve import HybridRetriever, retrieve_chroma

__all__ = [
    "Chunk",
    "HybridRetriever",
    "RetrievalHit",
    "build_kb",
    "chunk_document",
    "chunk_documents",
    "chunk_text",
    "retrieve_chroma",
]
