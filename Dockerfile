FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy project files
COPY pyproject.toml ./
COPY equitas_sdk ./equitas_sdk
COPY guardian ./guardian
COPY examples ./examples
COPY main.py ./

# Install dependencies
RUN uv pip install --system -e .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Environment variables
ENV DATABASE_URL=sqlite+aiosqlite:///./data/equitas.db
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "guardian.main:app", "--host", "0.0.0.0", "--port", "8000"]
