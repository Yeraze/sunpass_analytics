FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN uv pip install --system --no-cache .

RUN playwright install chromium && playwright install-deps chromium

RUN mkdir -p /app/data

EXPOSE 8080

CMD ["uvicorn", "sunpass.main:app", "--host", "0.0.0.0", "--port", "8080"]
