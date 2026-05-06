from typing import List, Dict, Optional
from openai import OpenAI

from core.config import config
from services.query_classifier import classify_query
from services.context import compress_context, build_context_string


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
) -> Dict:
    """
    Generate an answer with:
      - query classification (factual / summary / comparison)
      - context compression (token budget enforcement)
      - inline citations
      - conversation history

    Args:
        query: user question
        context_chunks: reranked chunks (best first)
        history: prior turns [{"role", "content"}, ...]
        client: optional OpenAI client for DI

    Returns:
        {
          "answer": str,
          "citations": [...],
          "query_type": str,
          "context_tokens": int
        }
    """
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

    response = client.chat.completions.create(
        model=config.CHAT_MODEL,
        messages=messages,
    )
    answer = response.choices[0].message.content

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

    return {
        "answer": answer,
        "citations": citations,
        "query_type": query_type,
        "context_tokens": token_count,
    }