# tests/test_emailer.py

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import MagicMock, patch

from agents.emailer import build_html, send_email

SAMPLE_ARTICLES = [
    {
        "source": "TechCrunch AI",
        "title": "AI agents are taking over",
        "link": "https://techcrunch.com/example",
        "ai_summary": "AI agents are becoming more capable. Companies are racing to deploy them. The market is growing fast.",
    },
    {
        "source": "ArXiv",
        "title": "LoRA fine-tuning on LLMs",
        "link": "https://arxiv.org/abs/example",
        "ai_summary": "LoRA reduces memory for fine-tuning. It achieves near full fine-tune performance. It is widely adopted.",
    },
]


def test_build_html_contains_titles():
    html = build_html(SAMPLE_ARTICLES)
    assert "AI agents are taking over" in html
    assert "LoRA fine-tuning on LLMs" in html


def test_build_html_contains_links():
    html = build_html(SAMPLE_ARTICLES)
    assert "https://techcrunch.com/example" in html
    assert "https://arxiv.org/abs/example" in html


def test_build_html_contains_summaries():
    html = build_html(SAMPLE_ARTICLES)
    assert "Companies are racing to deploy them" in html


def test_send_email_success():
    with patch("agents.emailer.smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server

        with patch.dict(os.environ, {
            "GMAIL_ADDRESS": "test@gmail.com",
            "GMAIL_APP_PASSWORD": "testpass",
            "RECIPIENT_EMAIL": "recipient@gmail.com",
        }):
            send_email(SAMPLE_ARTICLES)

        mock_server.login.assert_called_once()
        mock_server.sendmail.assert_called_once()


def test_send_email_raises_on_failure():
    import pytest
    with patch("agents.emailer.smtplib.SMTP_SSL") as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP connection failed")

        with patch.dict(os.environ, {
            "GMAIL_ADDRESS": "test@gmail.com",
            "GMAIL_APP_PASSWORD": "testpass",
            "RECIPIENT_EMAIL": "recipient@gmail.com",
        }):
            with pytest.raises(Exception):
                send_email(SAMPLE_ARTICLES)
