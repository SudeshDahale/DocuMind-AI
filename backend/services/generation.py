from typing import List, Dict, Optional
from openai import OpenAI
import time
from core.logger import get_logger
from core.metrics import record
from core.config import config
from services.query_classifier import classify_query
from services.context import compress_context, build_context_string
from core.errors import with_retry


def _get_client() -> OpenAI:
    return OpenAI(api_key=config.OPENAI_API_KEY)


_SYSTEM_PROMPTS = {
    "factual": (
        "You are a precise document assistant. Answer the specific question using ONLY "
        "the provided document context. Cite sources inline using [1], [2], etc. "
        "Be direct and concise."
    ),
    "summary": (
        "You are a document assistant. Provide a clear, structured summary based ONLY "
        "on the provided document context. Cite sources inline using [1], [2], etc. "
        "Organise your answer with brief sections if helpful."
    ),
    "comparison": (
        "You are a document assistant. Compare and contrast the requested items using ONLY "
        "the provided document context. Cite sources inline using [1], [2], etc. "
        "Use a structured format — similarities first, then differences."
    ),
}


def answer_question(
    query: str,
    context_chunks: List[Dict],
    history: Optional[List[Dict]] = None,
    client: OpenAI = None,
    openai_api_key: str = None,
) -> Dict:
    # If a raw key is passed, build a client from it; otherwise fall back to default
    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)
    else:
        client = client or _get_client()

    # 1. Classify query
    query_type = classify_query(query, client=client)

    # 2. Compress context to token budget
    compressed_chunks, token_count = compress_context(context_chunks, query)

    # 3. Build context string
    context = build_context_string(compressed_chunks)

    # 4. Pick system prompt based on query type
    system_prompt = _SYSTEM_PROMPTS[query_type]

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        for turn in history[-(config.MAX_HISTORY_TURNS):]:
            messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append({
        "role": "user",
        "content": f"Document context:\n{context}\n\nQuestion: {query}",
    })

    @with_retry(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(Exception,), reraise=False, fallback=None)
    def _call_llm():
        return client.chat.completions.create(
            model=config.CHAT_MODEL,
            messages=messages,
        )

    t0 = time.perf_counter()
    response = _call_llm()
    latency_ms = round((time.perf_counter() - t0) * 1000, 1)

    if response is None:
        return {
            "answer": "I'm sorry, I was unable to generate an answer right now. Please try again in a moment.",
            "citations": [],
            "query_type": query_type,
            "context_tokens": token_count,
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "latency_ms": latency_ms},
        }

    answer = response.choices[0].message.content
    usage = response.usage

    # 5. Build deduplicated citations
    seen: set = set()
    citations: List[Dict] = []
    for chunk in compressed_chunks:
        key = (chunk["doc_id"], chunk["page"])
        if key not in seen:
            seen.add(key)
            citations.append({
                "page": chunk["page"],
                "fileName": chunk["fileName"],
                "snippet": chunk["text"][:200].strip(),
            })

    log = get_logger("generation")
    log.info(
        "llm_call",
        extra={
            "query_type": query_type,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "context_tokens": token_count,
            "model": config.CHAT_MODEL,
        },
    )

    record({
        "query_type": query_type,
        "latency_ms": latency_ms,
        "prompt_tokens": usage.prompt_tokens,
        "completion_tokens": usage.completion_tokens,
        "model": config.CHAT_MODEL,
    })

    return {
        "answer": answer,
        "citations": citations,
        "query_type": query_type,
        "context_tokens": token_count,
        "usage": {
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "latency_ms": latency_ms,
        },
    }