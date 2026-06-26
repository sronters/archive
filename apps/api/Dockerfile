FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY apps ./apps
COPY packages ./packages
COPY migrations ./migrations
COPY alembic.ini ./

RUN pip install --no-cache-dir ".[dev]"

ENV PYTHONPATH=/app/apps/api:/app/packages/domain:/app/packages/application:/app/packages/infrastructure:/app/packages/shared

CMD ["uvicorn", "medarchive_api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
