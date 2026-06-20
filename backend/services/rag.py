from services.chunking import chunk_text
from services.embedding import get_embeddings_batch
from services.retrieval import (
    build_vector_store,
    load_vector_store,
    load_chunks,
    search,
    search_multiple,
)
from services.generation import answer_question
import os
import numpy as np
from core.config import config
import base64
import faiss

os.makedirs(config.index_dir, exist_ok=True)
os.makedirs(config.chunk_dir, exist_ok=True)


def create_vector_store(chunks, doc_id):
    texts = [c["text"] for c in chunks]
    embeddings = get_embeddings_batch(texts)
    return build_vector_store(chunks, doc_id, embeddings), chunks



def index_to_bytes(doc_id: str) -> bytes:
    """Read saved FAISS index from disk and return raw bytes."""
    path = os.path.join(config.index_dir, f"{doc_id}.index")
    with open(path, "rb") as f:
        return f.read()

def bytes_to_index(data: bytes, doc_id: str):
    """Write bytes back to disk as FAISS index."""
    path = os.path.join(config.index_dir, f"{doc_id}.index")
    os.makedirs(config.index_dir, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)
    return faiss.read_index(path)

__all__ = [
    "chunk_text", "create_vector_store", "index_to_bytes", "bytes_to_index",
    "load_chunks", "search", "search_multiple", "answer_question",
]