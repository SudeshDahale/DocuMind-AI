import time
import numpy as np
from typing import List
from openai import OpenAI
from core.config import config
from core.logger import get_logger
from core.errors import with_retry

log = get_logger("embedding")


def _get_client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)


@with_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,), reraise=True)
def get_embedding(text: str, client: OpenAI = None) -> List[float]:
    """Embed a single string with automatic retry."""
    client = client or _get_client()
    response = client.embeddings.create(
        model=config.EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def get_embeddings_batch(
    texts: List[str],
    client: OpenAI = None,
    batch_size: int = 100,
    max_retries: int = 3,
    retry_delay: float = 1.0,
) -> List[List[float]]:
    """
    Embed a list of texts using batched API calls with retry logic.
    Falls back to zero vectors for any batch that permanently fails
    so the rest of the document can still be indexed.
    """
    client = client or _get_client()
    dim = None  # resolved on first success
    all_embeddings: List[List[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start: start + batch_size]
        last_error = None
        wait = retry_delay

        for attempt in range(max_retries):
            try:
                response = client.embeddings.create(
                    model=config.EMBEDDING_MODEL,
                    input=batch,
                )
                batch_embeddings = [
                    item.embedding
                    for item in sorted(response.data, key=lambda x: x.index)
                ]
                if dim is None:
                    dim = len(batch_embeddings[0])
                all_embeddings.extend(batch_embeddings)
                break
            except Exception as e:
                last_error = e
                log.warning(
                    "embedding_batch_failed",
                    extra={
                        "batch_start": start,
                        "attempt": attempt + 1,
                        "error": str(e),
                        "retry_in": wait,
                    },
                )
                if attempt < max_retries - 1:
                    time.sleep(wait)
                    wait *= 2.0
        else:
            # Fallback: zero vectors so indexing can continue
            fallback_dim = dim or 1536
            log.error(
                "embedding_batch_exhausted_retries_using_zero_vectors",
                extra={
                    "batch_start": start,
                    "batch_size": len(batch),
                    "fallback_dim": fallback_dim,
                    "error": str(last_error),
                },
            )
            all_embeddings.extend([[0.0] * fallback_dim] * len(batch))

    return all_embeddings