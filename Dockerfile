FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# uv’s install script places binaries in ~/.local/bin (not ~/.cargo/bin)
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml ./
COPY README.md ./
COPY equitas_sdk ./equitas_sdk
COPY backend_api ./backend_api
COPY examples ./examples
COPY main.py ./

RUN uv pip install --system -e .

# Pre-download heavy ML weights at build time (faster cold start on Render)
RUN python -c "from detoxify import Detoxify; Detoxify('original')"
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

RUN mkdir -p /app/data
EXPOSE 8000
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8000}/health" || exit 1'

# Render and other PaaS set PORT at runtime
CMD ["sh", "-c", "uvicorn backend_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
