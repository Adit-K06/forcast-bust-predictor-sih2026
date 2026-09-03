# Multi-stage Dockerfile for AtmoTrust Backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r ./backend/requirements.txt

# Copy backend, ml_core, explainability, features
COPY backend ./backend
COPY ml_core ./ml_core
COPY explainability ./explainability
COPY features ./features

ENV PYTHONPATH="/app:/app/backend"
EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
