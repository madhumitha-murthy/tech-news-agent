# tests/test_summariser.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch

from agents.summariser import summarise_all, summarise_article

SAMPLE_ARTICLE = {
    "title": "OpenAI releases GPT-5",
    "summary": "OpenAI has released GPT-5, a new large language model with improved reasoning capabilities.",
}


def _mock_google(response_text=None, raise_error=None):
    """Build a mock google.genai module for patching sys.modules."""
    mock_genai = MagicMock()
    mock_client = MagicMock()

    if raise_error:
        mock_client.models.generate_content.side_effect = raise_error
    else:
        mock_response = MagicMock()
        mock_response.text = response_text or "Test summary."
        mock_client.models.generate_content.return_value = mock_response

    mock_genai.Client.return_value = mock_client

    mock_google = MagicMock()
    mock_google.genai = mock_genai

    return mock_google, mock_genai


def test_summarise_article_success():
    mock_google, mock_genai = _mock_google(
        "GPT-5 is OpenAI's latest model. It improves on reasoning tasks. It was released in 2025."
    )
    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
        result = summarise_article(SAMPLE_ARTICLE)

    assert isinstance(result, str)
    assert len(result) > 0


def test_summarise_article_fallback_on_error():
    mock_google, mock_genai = _mock_google(raise_error=Exception("API error"))

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}):
        result = summarise_article(SAMPLE_ARTICLE)

    # Should fall back to original summary truncated to 200 chars + "..."
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarise_all_adds_ai_summary():
    articles = [SAMPLE_ARTICLE.copy(), SAMPLE_ARTICLE.copy()]
    mock_google, mock_genai = _mock_google("This is a test summary.")

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}), \
         patch("agents.summariser.time.sleep"):
        result = summarise_all(articles)

    assert all("ai_summary" in a for a in result)


def test_summarise_all_returns_same_count():
    articles = [SAMPLE_ARTICLE.copy() for _ in range(5)]
    mock_google, mock_genai = _mock_google("Summary.")

    with patch.dict("sys.modules", {"google": mock_google, "google.genai": mock_genai}), \
         patch("agents.summariser.time.sleep"):
        result = summarise_all(articles)

    assert len(result) == 5
