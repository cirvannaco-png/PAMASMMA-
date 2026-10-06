# PAMASMMA v4 — Backend Dockerfile
# Multi-stage build. Non-root user.

FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ── Deps stage ───────────────────────────────────────────────────────────────
FROM base AS deps
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Production stage ──────────────────────────────────────────────────────────
FROM deps AS production
COPY . .

# Non-root user
RUN addgroup --system pamasmma && adduser --system --ingroup pamasmma pamasmma
USER pamasmma

EXPOSE 8000

# Render and compatible platforms provide PORT; default to 8000 for local execution
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --loop uvloop"]
