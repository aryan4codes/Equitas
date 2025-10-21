# FairSight Development Guide

## Prerequisites

- Python 3.11+
- OpenAI API Key
- uv package manager

## Setup

### 1. Initialize Project

```bash
# Initialize uv
bash init-uv.sh

# Or manually
uv init --python 3.11
uv venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
# Install all dependencies
uv pip install -e .

# Or install specific groups
uv pip install -e ".[dev]"
```

### 3. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit with your values
nano .env
```

Required settings:
- `OPENAI_API_KEY`: Your OpenAI API key for toxicity detection

### 4. Initialize Database

The database will be created automatically on first run. It uses SQLite by default.

For production, use PostgreSQL:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/fairsight
```

## Running the Application

### Start Guardian Backend

```bash
# Using the start script
bash start-guardian.sh

# Or manually
uvicorn guardian.main:app --reload --port 8000
```

API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

### Test the SDK

```bash
# Run basic examples
python examples/basic_usage.py

# Test API directly
python examples/test_guardian_api.py
```

## Development Workflow

### Code Style

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy guardian fairsight_sdk
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=guardian --cov=fairsight_sdk
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Architecture

### SDK Architecture

```
FairSight Client
├── Wraps OpenAI API
├── Async HTTP client for Guardian
├── Safety checks (pre/post)
└── Automatic remediation
```

### Backend Architecture

```
Guardian API (FastAPI)
├── Authentication Layer
├── API Endpoints (v1)
│   ├── Analysis (toxicity, bias, jailbreak)
│   ├── Logging
│   ├── Metrics
│   └── Incidents
├── Services
│   ├── Toxicity Detector (OpenAI Moderation)
│   ├── Bias Detector (Pattern + Paired Testing)
│   ├── Jailbreak Detector (Pattern Matching)
│   ├── Explainability Engine
│   └── Remediation Engine (LLM-based)
└── Database
    ├── API Logs
    ├── Incidents
    ├── Metrics
    └── Tenant Configs
```

## API Usage

### Using the SDK

```python
from fairsight_sdk import FairSight, SafetyConfig

client = FairSight(
    openai_api_key="sk-...",
    fairsight_api_key="fs-dev-key-123",
    tenant_id="your-org",
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello"}],
    safety_config=SafetyConfig(
        on_flag="auto-correct",  # strict, auto-correct, warn-only
        toxicity_threshold=0.7,
        enable_bias_check=True,
    )
)
```

### Direct API Calls

```bash
# Analyze toxicity
curl -X POST http://localhost:8000/v1/analysis/toxicity \
  -H "Authorization: Bearer fs-dev-key-123" \
  -H "X-Tenant-ID: tenant_demo" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test text", "tenant_id": "tenant_demo"}'

# Get metrics
curl http://localhost:8000/v1/metrics \
  -H "Authorization: Bearer fs-dev-key-123" \
  -H "X-Tenant-ID: tenant_demo"
```

## Configuration

### Safety Thresholds

Customize per tenant in database or via SDK:

```python
SafetyConfig(
    toxicity_threshold=0.7,    # 0.0 - 1.0
    bias_threshold=0.3,         # 0.0 - 1.0
    on_flag="auto-correct",     # Action on violation
)
```

### Feature Flags

Enable/disable checks per tenant:

```python
SafetyConfig(
    enable_toxicity_check=True,
    enable_bias_check=True,
    enable_jailbreak_check=True,
    enable_remediation=True,
)
```

## Monitoring

### Logs

```bash
# Application logs
tail -f guardian.log

# Access logs
tail -f access.log
```

### Metrics

Available at `/v1/metrics`:
- Total API calls
- Flagged calls
- Average toxicity/bias scores
- Latency metrics
- Safety units consumed

### Incidents

Query at `/v1/incidents`:
- Filter by type, severity, status
- Date range queries
- Pagination support

## Production Deployment

### Docker

```bash
# Build
docker build -t fairsight-guardian .

# Run
docker run -d \
  -p 8000:8000 \
  -e OPENAI_API_KEY=sk-... \
  -e DATABASE_URL=postgresql://... \
  fairsight-guardian
```

### Environment Variables

Required:
- `OPENAI_API_KEY`
- `DATABASE_URL` (for production)
- `SECRET_KEY` (strong random key)

Optional:
- `DEFAULT_TOXICITY_THRESHOLD`
- `DEFAULT_BIAS_THRESHOLD`
- Feature flags

### Scaling

- Use multiple Guardian instances behind load balancer
- Scale database (PostgreSQL with read replicas)
- Use Redis for caching
- Enable async logging

## Troubleshooting

### Common Issues

**Import errors:**
```bash
# Reinstall in editable mode
uv pip install -e .
```

**Database errors:**
```bash
# Reset database
rm fairsight.db
# Restart app (will recreate)
```

**OpenAI API errors:**
- Check API key in .env
- Verify API quota
- Check network connectivity

## Contributing

1. Create feature branch
2. Make changes
3. Run tests and linting
4. Submit PR

## Resources

- [PRD](PRD.md) - Product Requirements
- [API Docs](http://localhost:8000/docs) - Swagger UI
- [OpenAI Moderation](https://platform.openai.com/docs/guides/moderation)
