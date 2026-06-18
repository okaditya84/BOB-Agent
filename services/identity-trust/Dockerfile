FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

# Install deps first (better layer caching), then the project.
COPY pyproject.toml uv.lock* ./
RUN uv sync --no-dev --no-install-project
COPY . .
RUN uv sync --no-dev

EXPOSE 8001
CMD ["uv", "run", "uvicorn", "bobai_identity.main:app", "--host", "0.0.0.0", "--port", "8001"]
