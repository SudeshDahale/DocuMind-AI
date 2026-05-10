from typing import Literal
from openai import OpenAI
from core.config import config
from core.logger import get_logger
from core.errors import with_retry

log = get_logger("query_classifier")

QueryType = Literal["summary", "factual", "comparison"]

_VALID = {"summary", "factual", "comparison"}
_FALLBACK: QueryType = "factual"

_PROMPT = (
    "Classify this question into exactly one word: summary, factual, or comparison.\n"
    "Rules:\n"
    "  summary    = asks for overview, summary, or general description\n"
    "  factual    = asks for a specific fact, value, date, or definition\n"
    "  comparison = asks to compare, contrast, or differentiate things\n\n"
    "Question: {query}\n"
    "Answer (one word only):"
)


@with_retry(max_attempts=2, delay=0.5, backoff=2.0, exceptions=(Exception,), reraise=False, fallback=_FALLBACK)
def classify_query(query: str, client: OpenAI = None) -> QueryType:
    """
    Classify the user query into: summary | factual | comparison.
    Retries once on failure, then falls back to 'factual'.
    """
    client = client or OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=[{"role": "user", "content": _PROMPT.format(query=query)}],
        max_tokens=5,
        temperature=0,
    )
    label = response.choices[0].message.content.strip().lower()
    if label in _VALID:
        return label  # type: ignore

    log.warning(
        "query_classifier_unexpected_label",
        extra={"label": label, "fallback": _FALLBACK},
    )
    return _FALLBACK