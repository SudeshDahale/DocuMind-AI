from typing import List, Dict
from core.logger import get_logger

log = get_logger("reranking")

_model = None


def _get_model():
    """Lazy-load the CrossEncoder. Returns None if unavailable."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import CrossEncoder
            from core.config import config
            _model = CrossEncoder(config.RERANKER_MODEL)
            log.info("reranker_loaded", extra={"model": config.RERANKER_MODEL})
        except Exception as e:
            log.error(
                "reranker_load_failed_will_skip_reranking",
                extra={"error": str(e)},
            )
            _model = None
    return _model


def rerank(query: str, chunks: List[Dict], top_n: int = None) -> List[Dict]:
    """
    Re-rank retrieved chunks using a CrossEncoder.
    Falls back to returning chunks as-is if the model is unavailable.
    """
    from core.config import config
    top_n = top_n or config.RERANK_TOP_N

    if not chunks:
        return []

    model = _get_model()

    # Fallback: no model available — return top_n as-is
    if model is None:
        log.warning(
            "reranking_skipped_returning_top_n",
            extra={"reason": "model_unavailable", "top_n": top_n},
        )
        return chunks[:top_n]

    try:
        pairs = [(query, chunk["text"]) for chunk in chunks]
        scores = model.predict(pairs)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in ranked[:top_n]]
    except Exception as e:
        log.error(
            "reranking_failed_returning_top_n",
            extra={"error": str(e), "top_n": top_n},
        )
        return chunks[:top_n]