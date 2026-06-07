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
