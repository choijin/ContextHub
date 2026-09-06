# syntax=docker/dockerfile:1

FROM python:3.12-slim AS runtime

ARG EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    HOME=/home/contexthub \
    HF_HOME=/home/contexthub/.cache/huggingface \
    CONTEXTHUB_EMBEDDING_MODEL=${EMBEDDING_MODEL}

RUN python -m pip install --no-cache-dir uv==0.11.7

RUN groupadd --gid 10001 contexthub \
    && useradd --uid 10001 --gid contexthub --create-home --shell /usr/sbin/nologin contexthub

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# Retrieval must not depend on downloading the embedding model during a cold start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('${EMBEDDING_MODEL}', device='cpu')"

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

COPY frontend ./frontend
COPY data/index ./data/index

RUN mkdir -p "$HF_HOME" \
    && chown -R contexthub:contexthub "$HOME"

USER contexthub

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["uvicorn", "contexthub.main:app", "--host", "0.0.0.0", "--port", "8000"]
