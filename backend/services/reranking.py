from typing import List, Dict
from sentence_transformers import CrossEncoder
from core.config import config

_model: CrossEncoder = None


def _get_model() -> CrossEncoder:
    """Lazy-load the CrossEncoder (downloads once, cached in memory)."""
    global _model
    if _model is None:
        _model = CrossEncoder(config.RERANKER_MODEL)
    return _model


def rerank(query: str, chunks: List[Dict], top_n: int = None) -> List[Dict]:
    """
    Re-rank retrieved chunks using a CrossEncoder.

    Args:
        query: user question
        chunks: candidate chunks from hybrid retrieval
        top_n: how many to keep after reranking (defaults to config)

    Returns:
        top_n chunks sorted by relevance score descending
    """
    top_n = top_n or config.RERANK_TOP_N
    if not chunks:
        return []

    model = _get_model()
    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores = model.predict(pairs)

    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_n]]