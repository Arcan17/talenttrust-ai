# TalentTrust AI backend
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install deps first for layer caching
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install ".[dev]"

COPY . .

EXPOSE 8000

# entrypoint runs migrations then starts the API (overridable by compose)
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
