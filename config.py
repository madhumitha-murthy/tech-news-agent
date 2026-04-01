# config.py — All settings for the Tech News Agent

# ── Topics to filter by ──────────────────────────────────────────────────────
TOPICS = [
    "agentic AI", "AI agents", "LLM", "large language model",
    "NLP", "natural language processing", "ChatGPT", "GPT", "Gemini",
    "Claude", "Anthropic", "OpenAI", "DeepMind",
    "Singapore tech", "Singapore AI", "Singapore job", "SG tech",
    "machine learning", "deep learning", "transformer", "RAG",
    "retrieval augmented", "fine-tuning", "LoRA",
]

# ── Number of top articles to include ────────────────────────────────────────
TOP_N = 15  # between 10–20

# ── RSS Feed Sources ──────────────────────────────────────────────────────────
RSS_FEEDS = {
    "HackerNews":       "https://hnrss.org/frontpage",
    "TechCrunch AI":    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "VentureBeat AI":   "https://venturebeat.com/category/ai/feed/",
    "Anthropic Blog":   "https://www.anthropic.com/rss.xml",
    "OpenAI Blog":      "https://openai.com/blog/rss.xml",
    "DeepMind Blog":    "https://deepmind.google/blog/rss.xml",
    "MIT Tech Review":  "https://www.technologyreview.com/feed/",
    "SG Tech News":     "https://www.techinasia.com/feed",
}

# ── ArXiv categories to fetch ─────────────────────────────────────────────────
ARXIV_CATEGORIES = ["cs.AI", "cs.CL", "cs.LG"]
ARXIV_MAX_RESULTS = 20

# ── Reddit subreddits ─────────────────────────────────────────────────────────
REDDIT_SUBREDDITS = ["MachineLearning", "artificial", "singularity", "LocalLLaMA"]
REDDIT_POST_LIMIT = 10

# ── Schedule ──────────────────────────────────────────────────────────────────
SCHEDULE_HOUR = 23
SCHEDULE_MINUTE = 55

# ── Email ─────────────────────────────────────────────────────────────────────
EMAIL_SUBJECT = "🤖 Daily Tech & AI Digest"
