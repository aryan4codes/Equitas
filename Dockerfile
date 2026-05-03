FROM python:3.11-slim

WORKDIR /app

# Default for Render 512MB: no torch models loaded at startup (see EQUITAS_SLIM)
ARG EQUITAS_SLIM=true
ENV EQUITAS_SLIM=${EQUITAS_SLIM}
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

COPY pyproject.toml ./
COPY README.md ./
COPY equitas_sdk ./equitas_sdk
COPY backend_api ./backend_api
COPY examples ./examples
COPY main.py ./

RUN uv pip install --system -e .

# Pre-download ML weights only for full (non-slim) images — avoids huge layers and build RAM when slim
RUN if [ "$EQUITAS_SLIM" != "true" ]; then \
      python -c "from detoxify import Detoxify; Detoxify('original')" && \
      python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"; \
    else \
      echo "Skipping model warm-up (EQUITAS_SLIM=true)"; \
    fi

RUN mkdir -p /app/data
EXPOSE 10000
ENV PYTHONUNBUFFERED=1

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-10000}/health" || exit 1'

CMD ["sh", "-c", "uvicorn backend_api.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
