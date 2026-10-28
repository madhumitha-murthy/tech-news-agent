# 🤖 Tech News Agent

![CI](https://github.com/madhumitha-murthy/tech-news-agent/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/madhumitha-murthy/tech-news-agent/actions/workflows/cd.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An end-to-end AI system with two parts: a **daily news pipeline** that fetches, filters, summarises, and emails a digest of AI & tech news, and a **ReAct research agent** (LangGraph + Gemini) that answers questions over collected articles with tool calling, grounding checks, and hallucination refusal.

---

## Features

- **Multi-source fetching** — ArXiv, HackerNews, TechCrunch, VentureBeat, Anthropic/OpenAI/DeepMind blogs
- **Smart filtering** — keyword-based relevance scoring across Agentic AI, LLMs, NLP, Singapore tech
- **AI summarisation** — Gemini 3.8 Flash (free tier) generates 2–3 line summaries per article
- **Beautiful HTML email** — styled digest delivered via Gmail SMTP at 11:55 PM SGT daily
- **Agentic research assistant** — LangGraph ReAct agent with Gemini function calling, 4 tools, grounding check
- **RAG query interface** — ask questions over stored articles using semantic search + Gemini
- **Vector store** — ChromaDB + Sentence Transformers for local semantic search
- **Grounding & hallucination guard** — embedding-based check refuses answers not supported by sources
- **Agent evaluation suite** — 20 test questions measuring grounded answer rate, refusal accuracy, tool selection
- **Pipeline metrics** — tracks fetch counts, filter rates, summary success, delivery status
- **Fully containerised** — Docker + Kubernetes CronJob ready
- **CI/CD** — GitHub Actions for lint, test, Docker build & push to GHCR

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Tech News Agent                    │
│                                                     │
│  ┌──────────┐   ┌──────────┐   ┌────────────────┐  │
│  │ Fetcher  │──▶│  Filter  │──▶│  Summariser    │  │
│  │          │   │          │   │  (Gemini 3.8)  │  │
│  │ ArXiv    │   │ Keyword  │   └───────┬────────┘  │
│  │ RSS Feeds│   │ Scoring  │           │           │
│  │ HN/TC/VB │   │ Top N    │   ┌───────▼────────┐  │
│  └──────────┘   └──────────┘   │    Storer      │  │
│                                │  (ChromaDB)    │  │
│                                └───────┬────────┘  │
│  ┌──────────────────────────┐          │           │
│  │  RAG Query Interface     │   ┌───────▼────────┐  │
│  │  query.py                │   │    Emailer     │  │
│  │  Retriever + Gemini      │   │  (Gmail SMTP)  │  │
│  └──────────────────────────┘   └────────────────┘  │
│                                                     │
│  Scheduler: APScheduler / K8s CronJob (11:55 PM SGT)│
└─────────────────────────────────────────────────────┘
```

### Research Agent (ReAct Loop)

```
User question
     │
     ▼
┌─────────────────────────────────────────────┐
│  AGENT NODE (Gemini 3.8 Flash)              │
│  Sees: question + history + 4 tool schemas  │
│  Decides: call a tool OR give final answer  │
└──────────┬──────────────────┬───────────────┘
           │                  │
      tool calls         final answer
           │                  │
           ▼                  ▼
    ┌─────────────┐   ┌────────────────────┐
    │ TOOLS NODE  │   │ GROUNDING NODE     │
    │ Validates & │   │ Splits answer into │
    │ executes    │   │ sentences, checks  │
    │ (budget: 6) │   │ cosine sim vs      │
    └──────┬──────┘   │ sources (>= 60%)   │
           │          └─────────┬──────────┘
           ▼                    │
      back to             supported?
      AGENT NODE         yes/       \no
                        return     refuse
                        answer     answer
```

**Tools available to the agent:**

| Tool | What it does | When the agent uses it |
|---|---|---|
| `search_articles` | Semantic search over ChromaDB | News questions |
| `search_arxiv` | Live ArXiv paper search | Research questions |
| `summarise` | Gemini summarises long text | Verbose results |
| `compare_articles` | Fetch articles by title for comparison | Comparison questions |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| AI / LLM | Google Gemini 3.8 Flash (free tier) |
| Agent Framework | LangGraph (state graph, ReAct loop) |
| News Sources | feedparser, arxiv |
| Vector Store | ChromaDB (local, persistent) |
| Embeddings | Sentence Transformers (all-MiniLM-L6-v2) |
| Email Delivery | Gmail SMTP (smtplib) |
| Scheduling | APScheduler / Kubernetes CronJob |
| Containerisation | Docker (multi-stage build) |
| Orchestration | Kubernetes |
| CI/CD | GitHub Actions |
| Testing | pytest + mocks |
| Linting | ruff |

---

## Quick Start

### 1. Clone & set up virtual environment
```bash
git clone https://github.com/madhumitha-murthy/tech-news-agent.git
cd tech-news-agent
make install
source venv/bin/activate
```

### 2. Configure API keys
```bash
cp .env.example .env
# Edit .env with your keys (see API Keys section below)
```

### 3. Run once (test)
```bash
python main.py
```

### 4. Run on schedule (11:55 PM SGT daily)
```bash
python scheduler.py
```

### 5. Ask the research agent a question
```bash
python -m research_agent.run "What's new in AI agents this week?"
```
```
============================================================
  [search_articles] {'query': 'AI agents', 'top_k': 5} -> 5 results (ok)
============================================================
Based on recent news and research:

* Google launched a new developer platform allowing businesses to bring
  their services directly into Gemini and Search as agents alter how
  users discover and interact with web services.
* The paper "GEPA-Curator" introduces methods for curated learning and
  reflective prompt optimization to help LLM agents sustain multi-turn
  interactions in complex environments.
============================================================

Sources:
  - GEPA-Curator: Curated Learning for Self Improving Agents (ArXiv)
  - As AI agents reshape the web, Google opens Gemini... (TechCrunch AI)

Grounding: {'grounded': True, 'supported_fraction': 0.8}
```

### 6. Run the agent evaluation suite
```bash
python -m eval.run_eval
# Results saved to results/metrics.json and results/eval_details.csv
```

### 7. Legacy RAG query interface
```bash
python query.py
```

---

## API Keys Setup

| Key | Where to get | Cost |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) | Free |
| `GMAIL_ADDRESS` | Your Gmail address | Free |
| `GMAIL_APP_PASSWORD` | Google Account → Security → 2FA → App Passwords | Free |
| `RECIPIENT_EMAIL` | Email to receive the digest | Free |

---

## Docker

```bash
# Build
make docker-build

# Run with scheduler
make docker-run

# Or with docker-compose
make docker-compose-up

# Run pipeline once
docker-compose --profile run-once up tech-news-agent-run-once
```

---

## Kubernetes Deployment

```bash
# 1. Encode your secrets
echo -n "your_api_key" | base64

# 2. Edit k8s/secret.yaml with encoded values

# 3. Apply manifests
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/cronjob.yaml

# 4. Verify
kubectl get cronjobs
kubectl create job --from=cronjob/tech-news-agent test-run
```

---

## Metrics & Evaluation

Every pipeline run saves a JSON metrics log to `metrics/data/`.

```bash
# View evaluation across all runs
python -m metrics.evaluator
```

Sample output:
```
==================================================
PIPELINE EVALUATION REPORT
==================================================
  Total runs        : 7
  Success rate      : 100.0%
  Avg articles/run  : 14.3
  Avg duration      : 42.1s
  Avg summary rate  : 96.8%
==================================================
```

---

## Testing

```bash
make test          # run all tests
make lint          # lint with ruff
make format        # auto-format
```

---

## Project Structure

```
tech-news-agent/
├── pipeline/                  # Daily news pipeline (not agentic)
│   ├── fetcher.py             # fetch from ArXiv & RSS feeds
│   ├── filter.py              # keyword scoring & ranking
│   ├── summariser.py          # Gemini summarisation
│   ├── storer.py              # embed & store in ChromaDB
│   ├── retriever.py           # semantic search over stored articles
│   └── emailer.py             # HTML email via Gmail SMTP
├── research_agent/            # Agentic research assistant
│   ├── tools.py               # 4 tools + JSON schemas + validation
│   ├── llm.py                 # Gemini function calling wrapper
│   ├── graph.py               # LangGraph state graph (ReAct loop)
│   ├── grounding.py           # hallucination guard (embedding similarity)
│   └── run.py                 # CLI entry point
├── eval/                      # Agent evaluation
│   ├── questions.json         # 20 test questions (16 answerable + 4 OOS)
│   └── run_eval.py            # run eval, compute metrics
├── metrics/
│   ├── tracker.py             # per-run pipeline metrics
│   ├── evaluator.py           # historical evaluation report
│   ├── relevance_drift.py     # retrieval drift detection
│   └── data/                  # saved JSON run logs
├── tests/
│   ├── test_filter.py
│   ├── test_summariser.py
│   ├── test_emailer.py
│   ├── test_metrics.py
│   └── test_research_agent.py # 9 agent tests (FakeModel, no API)
├── k8s/
│   ├── cronjob.yaml
│   ├── configmap.yaml
│   └── secret.yaml
├── config.py                  # all settings
├── main.py                    # pipeline orchestrator
├── scheduler.py               # APScheduler daily runner
├── query.py                   # legacy RAG query CLI
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Roadmap

- [x] Agentic research assistant with LangGraph
- [x] Grounding check (hallucination guard)
- [x] Agent evaluation suite (20 questions, 4 metrics)
- [ ] Multi-agent upgrade (planner + parallel researchers + critic)
- [ ] Reddit source integration
- [ ] Web dashboard for metrics visualisation
- [ ] Personalisation based on reading history

---

## Author

**Madhumitha Murthy** — MSc EEE, NTU Singapore
ML/AI Engineer | NLP | Agentic AI

[![GitHub](https://img.shields.io/badge/GitHub-madhumitha--murthy-black?logo=github)](https://github.com/madhumitha-murthy)
