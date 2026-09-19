FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Dependencies change less often than code; keep them in their own layer.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY api ./api
COPY clients ./clients
COPY graph ./graph
COPY tools ./tools

RUN useradd --system --no-create-home app
USER app

EXPOSE 8000
CMD ["uvicorn", "api.service:app", "--host", "0.0.0.0", "--port", "8000"]
