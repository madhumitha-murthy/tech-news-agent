# tests/test_summariser.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock
from agents.summariser import summarise_article, summarise_all


SAMPLE_ARTICLE = {
    "title": "OpenAI releases GPT-5",
    "summary": "OpenAI has released GPT-5, a new large language model with improved reasoning capabilities.",
}


def test_summarise_article_success():
    mock_response = MagicMock()
    mock_response.text = "GPT-5 is OpenAI's latest model. It improves on reasoning tasks. It was released in 2025."

    with patch("agents.summariser.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        result = summarise_article(SAMPLE_ARTICLE)

    assert isinstance(result, str)
    assert len(result) > 0


def test_summarise_article_fallback_on_error():
    with patch("agents.summariser.model") as mock_model:
        mock_model.generate_content.side_effect = Exception("API error")
        result = summarise_article(SAMPLE_ARTICLE)

    # Should fall back to original summary
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarise_all_adds_ai_summary():
    articles = [SAMPLE_ARTICLE.copy(), SAMPLE_ARTICLE.copy()]
    mock_response = MagicMock()
    mock_response.text = "This is a test summary."

    with patch("agents.summariser.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        result = summarise_all(articles)

    assert all("ai_summary" in a for a in result)


def test_summarise_all_returns_same_count():
    articles = [SAMPLE_ARTICLE.copy() for _ in range(5)]
    mock_response = MagicMock()
    mock_response.text = "Summary."

    with patch("agents.summariser.model") as mock_model:
        mock_model.generate_content.return_value = mock_response
        result = summarise_all(articles)

    assert len(result) == 5
