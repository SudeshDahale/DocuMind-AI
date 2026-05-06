import pytest
from services.context import compress_context, build_context_string


def _make_chunks(n=5, text_len=200):
    return [
        {"text": f"chunk {i} " + ("x" * text_len), "page": i + 1, "doc_id": "d1", "fileName": "f.pdf"}
        for i in range(n)
    ]


def test_compress_fits_within_budget():
    chunks = _make_chunks(n=10, text_len=400)
    kept, tokens = compress_context(chunks, "short query", max_tokens=500)
    assert tokens <= 500
    assert len(kept) <= 10


def test_compress_keeps_best_first():
    chunks = _make_chunks(n=5, text_len=100)
    kept, _ = compress_context(chunks, "q", max_tokens=2000)
    assert kept[0]["page"] == chunks[0]["page"]


def test_compress_empty_input():
    kept, tokens = compress_context([], "query")
    assert kept == []
    assert tokens == 0


def test_build_context_string_format():
    chunks = [
        {"text": "hello world", "page": 1, "doc_id": "d1", "fileName": "doc.pdf"},
        {"text": "second chunk", "page": 2, "doc_id": "d1", "fileName": "doc.pdf"},
    ]
    ctx = build_context_string(chunks)
    assert "[1]" in ctx
    assert "[2]" in ctx
    assert "hello world" in ctx
    assert "Page 1" in ctx


def test_compress_trims_oversized_single_chunk():
    chunks = [{"text": "w " * 5000, "page": 1, "doc_id": "d1", "fileName": "f.pdf"}]
    kept, tokens = compress_context(chunks, "q", max_tokens=300)
    assert len(kept) == 1
    assert tokens <= 300