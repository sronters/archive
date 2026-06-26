FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY packages ./packages

RUN pip install --no-cache-dir ".[dev,parsers]"

ENV PYTHONPATH=/app/apps/worker:/app/packages/domain:/app/packages/application:/app/packages/infrastructure:/app/packages/shared

CMD ["celery", "-A", "medarchive_worker.celery_app:celery_app", "worker", "--loglevel=INFO"]
