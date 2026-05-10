import os
import json
import numpy as np
import faiss
from typing import List, Dict, Optional
from openai import OpenAI
from rank_bm25 import BM25Okapi
from core.config import config
from services.embedding import get_embedding


def build_vector_store(
    chunks: List[Dict],
    doc_id: str,
    embeddings: List[List[float]],
) -> faiss.IndexFlatL2:
    if not chunks:
        raise ValueError("No chunks provided")
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings length mismatch")

    os.makedirs(config.index_dir, exist_ok=True)
    dim = len(embeddings[0])
    index = faiss.IndexFlatL2(dim)
    index.add(np.array(embeddings, dtype="float32"))
    faiss.write_index(index, os.path.join(config.index_dir, f"{doc_id}.index"))
    return index


def load_vector_store(doc_id: str) -> Optional[faiss.IndexFlatL2]:
    path = os.path.join(config.index_dir, f"{doc_id}.index")
    if not os.path.exists(path):
        return None
    return faiss.read_index(path)


def load_chunks(doc_id: str) -> Optional[List[Dict]]:
    path = os.path.join(config.chunk_dir, f"{doc_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        data = json.load(f)
    normalised = []
    for i, item in enumerate(data):
        if isinstance(item, str):
            normalised.append({
                "text": item,
                "doc_id": doc_id,
                "page": i,
                "fileName": doc_id,
            })
        else:
            normalised.append(item)
    return normalised


# ── BM25 ─────────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> List[str]:
    return text.lower().split()


def bm25_search(query: str, chunks: List[Dict], k: int) -> List[Dict]:
    corpus = [_tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    top_indices = np.argsort(scores)[::-1][:k]
    return [chunks[i] for i in top_indices if scores[i] > 0]


# ── FAISS ─────────────────────────────────────────────────────────────────────

def faiss_search(
    index: faiss.IndexFlatL2,
    query: str,
    chunks: List[Dict],
    k: int,
    client: OpenAI = None,
) -> List[Dict]:
    query_vec = get_embedding(query, client=client)
    _, indices = index.search(np.array([query_vec], dtype="float32"), k)
    return [chunks[i] for i in indices[0] if 0 <= i < len(chunks)]


# ── HYBRID ────────────────────────────────────────────────────────────────────

def search(
    index: faiss.IndexFlatL2,
    query: str,
    chunks: List[Dict],
    k: int = None,
    client: OpenAI = None,
) -> List[Dict]:
    k = k or config.RETRIEVAL_TOP_K
    fetch_k = k * 2

    faiss_results = faiss_search(index, query, chunks, fetch_k, client)
    bm25_results = bm25_search(query, chunks, fetch_k)

    scores: Dict[str, float] = {}
    id_to_chunk: Dict[str, Dict] = {}

    for rank, chunk in enumerate(faiss_results):
        key = chunk["text"]
        scores[key] = scores.get(key, 0) + config.FAISS_WEIGHT * (1 / (rank + 1))
        id_to_chunk[key] = chunk

    for rank, chunk in enumerate(bm25_results):
        key = chunk["text"]
        scores[key] = scores.get(key, 0) + config.BM25_WEIGHT * (1 / (rank + 1))
        id_to_chunk[key] = chunk

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [id_to_chunk[key] for key, _ in ranked[:k]]


def search_multiple(
    doc_ids: List[str],
    query: str,
    k: int = None,
    client: OpenAI = None,
) -> List[Dict]:
    k = k or config.RETRIEVAL_TOP_K
    all_chunks: List[Dict] = []
    for doc_id in doc_ids:
        index = load_vector_store(doc_id)
        chunks = load_chunks(doc_id)
        if index is None or chunks is None:
            continue
        results = search(index, query, chunks, k=k, client=client)
        all_chunks.extend(results)
    return all_chunks