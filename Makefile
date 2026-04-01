.PHONY: install run test lint format docker-build docker-run clean

## ── Setup ────────────────────────────────────────────────────────────────────
install:
	python -m venv venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt
	@echo "✅ venv ready. Run: source venv/bin/activate"

## ── Run ──────────────────────────────────────────────────────────────────────
run:
	python main.py

schedule:
	python scheduler.py

## ── Test & Lint ──────────────────────────────────────────────────────────────
test:
	pytest tests/ -v --tb=short

lint:
	ruff check .

format:
	ruff format .

## ── Docker ───────────────────────────────────────────────────────────────────
docker-build:
	docker build -t tech-news-agent:latest .

docker-run:
	docker run --env-file .env tech-news-agent:latest

docker-compose-up:
	docker-compose up --build

## ── Clean ────────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache htmlcov .coverage
