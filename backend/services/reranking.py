from typing import List, Dict
from core.logger import get_logger

log = get_logger("reranking")


def rerank(query: str, chunks: List[Dict], top_n: int = None) -> List[Dict]:
    """
    Returns top_n chunks as-is (reranking disabled to save memory on free tier).
    The hybrid FAISS + BM25 retrieval already produces well-ranked results.
    """
    from core.config import config
    top_n = top_n or config.RERANK_TOP_N
    if not chunks:
        return []
    return chunks[:top_n]