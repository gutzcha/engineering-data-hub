# ===
# File Summary
# Path: backend\Dockerfile
# Type: shell
# Purpose: Container build specification for backend or frontend image publication.
# Primary responsibilities:
# - Domain behavior is summarized for fast onboarding and avoids full-file reread.
# - Core symbols: file-level implementation
# Inputs:
# - Downstream and upstream interactions in the same domain.
# Outputs:
# - API payloads, records, side effects, or UI views depending on file role.
# Dependencies:
# - Shared runtime services and adjacent domain modules.
# Known risks:
# - Validate behavior after migrations, dependency upgrades, or contract changes.
# ===
# 

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        gcc \
        postgresql-client \
        tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY . .

RUN if [ -f pyproject.toml ]; then pip install .; fi

EXPOSE 8000

CMD ["gunicorn", "plastic_hub.wsgi:application", "--bind", "0.0.0.0:8000"]

