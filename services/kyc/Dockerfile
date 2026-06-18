FROM python:3.12-slim

# Tesseract OCR binary for the document-fraud module.
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev

EXPOSE 8002
CMD ["uv", "run", "uvicorn", "bobai_kyc.main:app", "--host", "0.0.0.0", "--port", "8002"]
