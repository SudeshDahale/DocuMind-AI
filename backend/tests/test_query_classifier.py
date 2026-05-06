import pytest
from unittest.mock import MagicMock


def _mock_client(label: str):
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=label))]
    )
    return client


def test_classify_factual():
    from services.query_classifier import classify_query
    result = classify_query("What is the boiling point of water?", client=_mock_client("factual"))
    assert result == "factual"


def test_classify_summary():
    from services.query_classifier import classify_query
    result = classify_query("Summarise this document", client=_mock_client("summary"))
    assert result == "summary"


def test_classify_comparison():
    from services.query_classifier import classify_query
    result = classify_query("Compare method A and method B", client=_mock_client("comparison"))
    assert result == "comparison"


def test_classify_fallback_on_unknown():
    from services.query_classifier import classify_query
    result = classify_query("huh?", client=_mock_client("gibberish"))
    assert result == "factual"


def test_classify_fallback_on_exception():
    from services.query_classifier import classify_query
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("API down")
    result = classify_query("anything", client=client)
    assert result == "factual"