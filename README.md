# 🤖 Tech News Agent

![CI](https://github.com/YOUR_GITHUB_USERNAME/tech-news-agent/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/YOUR_GITHUB_USERNAME/tech-news-agent/actions/workflows/cd.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![License](https://img.shields.io/badge/license-MIT-green)

An end-to-end **agentic AI pipeline** that fetches, filters, summarises, and delivers a daily digest of AI & tech news to your inbox — fully automated, scheduled, and containerised.

---

## Features

- **Multi-source fetching** — ArXiv, HackerNews, TechCrunch, VentureBeat, Anthropic/OpenAI/DeepMind blogs, Reddit
- **Smart filtering** — keyword-based relevance scoring across Agentic AI, LLMs, NLP, Singapore tech
- **AI summarisation** — Gemini 1.5 Flash (free tier) generates 2–3 line summaries per article
- **Beautiful HTML email** — styled digest delivered via Gmail SMTP at 11:55 PM daily
- **Pipeline metrics** — tracks fetch counts, filter rates, summary success, delivery status
- **Evaluation report** — historical analysis across all runs
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
│  │          │   │          │   │  (Gemini API)  │  │
│  │ ArXiv    │   │ Keyword  │   └───────┬────────┘  │
│  │ RSS Feeds│   │ Scoring  │           │           │
│  │ Reddit   │   │ Top N    │   ┌───────▼────────┐  │
│  └──────────┘   └──────────┘   │    Emailer     │  │
│                                │  (Gmail SMTP)  │  │
│  ┌──────────────────────────┐  └───────┬────────┘  │
│  │  Metrics Tracker         │          │           │
│  │  + Evaluator             │◀─────────┘           │
│  └──────────────────────────┘                      │
│                                                     │
│  Scheduler: APScheduler / K8s CronJob (11:55 PM SGT)│
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| AI Summarisation | Google Gemini 1.5 Flash (free) |
| News Sources | feedparser, arxiv, praw (Reddit) |
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
git clone https://github.com/YOUR_GITHUB_USERNAME/tech-news-agent.git
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

### 4. Run on schedule (11:55 PM daily)
```bash
python scheduler.py
```

---

## API Keys Setup

| Key | Where to get | Cost |
|---|---|---|
| `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) | Free |
| `GMAIL_APP_PASSWORD` | Google Account → Security → 2FA → App Passwords | Free |
| `REDDIT_CLIENT_ID/SECRET` | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) | Free |

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
├── agents/
│   ├── fetcher.py          # fetch from ArXiv, RSS, Reddit
│   ├── filter.py           # keyword scoring & ranking
│   ├── summariser.py       # Gemini API summarisation
│   └── emailer.py          # HTML email via Gmail SMTP
├── metrics/
│   ├── tracker.py          # per-run metrics collection
│   ├── evaluator.py        # historical evaluation report
│   └── data/               # saved JSON run logs
├── tests/
│   ├── test_filter.py
│   ├── test_summariser.py
│   ├── test_emailer.py
│   └── test_metrics.py
├── k8s/
│   ├── cronjob.yaml        # k8s CronJob (11:55 PM SGT)
│   ├── configmap.yaml
│   └── secret.yaml
├── .github/workflows/
│   ├── ci.yml              # lint + test on every PR
│   └── cd.yml              # build + push Docker on merge
├── config.py               # all settings
├── main.py                 # pipeline orchestrator
├── scheduler.py            # APScheduler daily runner
├── Dockerfile              # multi-stage production build
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

---

## Roadmap

- [ ] Telegram bot delivery option
- [ ] Web dashboard for metrics visualisation
- [ ] Personalisation based on reading history
- [ ] Integration with job hunting agent

---

## Author

**Madhumitha Murthy** — MSc EEE, NTU Singapore
ML/AI Engineer | NLP | Agentic AI
