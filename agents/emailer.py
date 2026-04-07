# emailer.py — Format and send the daily digest via Gmail SMTP

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from config import EMAIL_SUBJECT

load_dotenv()


def build_html(articles):
    """Build a clean HTML email digest."""
    date_str = datetime.now().strftime("%A, %d %B %Y")

    rows = ""
    for i, article in enumerate(articles, 1):
        rows += f"""
        <div style="margin-bottom:28px; border-left:4px solid #4F46E5; padding-left:14px;">
            <p style="margin:0 0 4px 0; font-size:13px; color:#6B7280;">
                {article.get('source','Unknown')} &nbsp;|&nbsp; #{i}
            </p>
            <a href="{article.get('link','#')}"
               style="font-size:16px; font-weight:600; color:#111827; text-decoration:none;">
                {article.get('title','')}
            </a>
            <p style="margin:8px 0 6px 0; font-size:14px; color:#374151; line-height:1.6;">
                {article.get('ai_summary', article.get('summary','')[:200])}
            </p>
            <a href="{article.get('link','#')}"
               style="font-size:13px; color:#4F46E5; text-decoration:none;">
                Read full article →
            </a>
        </div>
        """

    html = f"""
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                 max-width:680px; margin:0 auto; padding:24px; background:#F9FAFB;">

        <div style="background:#4F46E5; border-radius:12px; padding:24px; margin-bottom:28px;">
            <h1 style="color:white; margin:0; font-size:22px;">🤖 Daily Tech & AI Digest</h1>
            <p style="color:#C7D2FE; margin:6px 0 0 0; font-size:14px;">{date_str}</p>
        </div>

        <div style="background:white; border-radius:12px; padding:24px; box-shadow:0 1px 3px rgba(0,0,0,0.1);">
            <p style="color:#6B7280; font-size:14px; margin-top:0;">
                Here are your top <strong>{len(articles)}</strong> stories in
                Agentic AI, LLMs, NLP & Singapore Tech today.
            </p>

            {rows}
        </div>

        <p style="text-align:center; color:#9CA3AF; font-size:12px; margin-top:20px;">
            Tech News Agent • Auto-generated daily digest
        </p>
    </body>
    </html>
    """
    return html


def send_email(articles):
    """Send the digest email via Gmail SMTP."""
    gmail = os.getenv("GMAIL_ADDRESS")
    password = os.getenv("GMAIL_APP_PASSWORD")
    recipient = os.getenv("RECIPIENT_EMAIL", gmail)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"{EMAIL_SUBJECT} — {datetime.now().strftime('%d %b %Y')}"
    msg["From"] = gmail
    msg["To"] = recipient

    html_content = build_html(articles)
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail, password)
            server.sendmail(gmail, recipient, msg.as_string())
        print(f"[emailer] Digest sent to {recipient}")
    except Exception as e:
        print(f"[emailer] Failed to send email: {e}")
        raise
