# Capture API Lambda image (issue #14): the FastAPI app unchanged, behind an HTTP API
# through Lambda Web Adapter. Default dependencies only (no ml group), so /recognize
# answers 503 here — recognition runs on the GPU box (#21).
# Build from the repo root:  docker build -f infra/api.Dockerfile -t avc-api .
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY backend/app ./app
# Shared Store as a top-level module; uvicorn adds /app to sys.path.
COPY ml/scripts/store.py ./store.py

# Lambda Web Adapter ships the Runtime Interface Client, so a non-AWS base image works.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:1.1.0 /lambda-adapter /opt/extensions/lambda-adapter

ENV PATH="/app/.venv/bin:$PATH" \
    AWS_LWA_READINESS_CHECK_PATH=/health

EXPOSE 8080
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]