import pytest
from unittest.mock import MagicMock, patch


def _make_chunks(texts):
    return [
        {"text": t, "page": i + 1, "doc_id": "d1", "fileName": "f.pdf"}
        for i, t in enumerate(texts)
    ]


def test_rerank_orders_by_score():
    chunks = _make_chunks(["unrelated text", "the cat sat on the mat", "cat mat sat"])
    with patch("services.reranking._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.1, 0.9, 0.7]
        mock_get.return_value = mock_model

        from services.reranking import rerank
        result = rerank("where did the cat sit?", chunks, top_n=2)

    assert result[0]["text"] == "the cat sat on the mat"
    assert result[1]["text"] == "cat mat sat"


def test_rerank_empty_input():
    from services.reranking import rerank
    with patch("services.reranking._get_model"):
        result = rerank("query", [], top_n=3)
    assert result == []


def test_rerank_respects_top_n():
    chunks = _make_chunks(["a", "b", "c", "d", "e"])
    with patch("services.reranking._get_model") as mock_get:
        mock_model = MagicMock()
        mock_model.predict.return_value = [0.5, 0.4, 0.3, 0.2, 0.1]
        mock_get.return_value = mock_model

        from services.reranking import rerank
        result = rerank("query", chunks, top_n=2)

    assert len(result) == 2