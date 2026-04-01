# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source code
COPY . .

# Create metrics data dir
RUN mkdir -p metrics/data

# Non-root user for security
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default: run the scheduler (can override with CMD in docker-compose)
CMD ["python", "scheduler.py"]
