# FairSight: AI Safety & Observability Platform

A hybrid SDK and backend platform that enhances OpenAI API usage with real-time safety, bias, and compliance checks.

## 🎯 Overview

FairSight provides:
- **Client SDK**: Drop-in replacement for OpenAI API with safety enhancements
- **Guardian Backend**: Microservices for toxicity, bias, and jailbreak detection
- **Real-time Dashboard**: Observability UI for metrics and incidents
- **Multi-tenant**: Enterprise-grade data isolation and RBAC

## 🏗️ Architecture

```
┌─────────────────┐
│  Your App       │
│  + FairSight SDK│
└────────┬────────┘
         │
         ├──────────────► OpenAI API
         │
         └──────────────► Guardian Backend
                          ├── Toxicity Detector
                          ├── Bias Checker
                          ├── Jailbreak Detector
                          ├── Explainability Engine
                          └── Remediation Service
                          
                          ↓
                          
                     Database (Logs, Incidents, Metrics)
                     
                          ↓
                          
                     Dashboard UI
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
uv init --python 3.11
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Configure Environment

Create `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///./fairsight.db

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### 3. Start Guardian Backend

```bash
cd backend
python -m guardian.main
```

Backend will be available at `http://localhost:8000`

### 4. Use FairSight SDK

```python
from fairsight_sdk import FairSight, SafetyConfig

# Initialize client
fairsight = FairSight(
    openai_api_key="sk-...",
    fairsight_api_key="fs-dev-key-123",
    tenant_id="your-org",
)

# Make safe API calls
response = fairsight.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    safety_config=SafetyConfig(on_flag="auto-correct")
)

# Access safety metadata
print(f"Toxicity: {response.safety_scores.toxicity_score}")
print(f"Categories: {response.safety_scores.toxicity_categories}")
```

## 📦 Project Structure

```
backend/
├── fairsight_sdk/          # Client SDK
│   ├── client.py           # Main SDK client
│   ├── models.py           # Data models
│   └── exceptions.py       # Custom exceptions
│
├── guardian/               # Backend API
│   ├── main.py            # FastAPI app
│   ├── core/              # Core utilities
│   │   ├── config.py      # Configuration
│   │   ├── database.py    # Database setup
│   │   └── auth.py        # Authentication
│   ├── models/            # Database models
│   │   ├── database.py    # SQLAlchemy models
│   │   └── schemas.py     # Pydantic schemas
│   ├── services/          # Analysis services
│   │   ├── toxicity.py    # Toxicity detection
│   │   ├── bias.py        # Bias checking
│   │   ├── jailbreak.py   # Jailbreak detection
│   │   ├── explainability.py  # Explanations
│   │   └── remediation.py     # Content remediation
│   └── api/v1/            # API endpoints
│       ├── analysis.py    # Analysis endpoints
│       ├── logging.py     # Logging endpoint
│       ├── metrics.py     # Metrics endpoint
│       └── incidents.py   # Incidents endpoint
│
└── examples/              # Usage examples
    ├── basic_usage.py     # SDK examples
    └── test_guardian_api.py  # API testing
```

## 🔒 Safety Features

### Toxicity Detection
- Uses OpenAI Moderation API
- Detects hate, harassment, violence, self-harm, sexual content
- Returns toxicity score (0-1) and flagged categories

### Bias Detection
- Demographic bias checking
- Paired prompt testing
- Stereotype detection

### Jailbreak Detection
- Pattern-based prompt injection detection
- Instruction override attempts
- Code injection prevention

### Explainability
- Highlights problematic text spans
- Natural language explanations
- Detailed violation categorization

### Automatic Remediation
- LLM-based text rewriting
- Removes toxic language while preserving intent
- Neutralizes biased content

## 📊 API Endpoints

### Analysis Endpoints

#### POST `/v1/analysis/toxicity`
Analyze text for toxicity.

```json
{
  "text": "Text to analyze",
  "tenant_id": "org123"
}
```

#### POST `/v1/analysis/bias`
Check for demographic bias.

```json
{
  "prompt": "Original prompt",
  "response": "LLM response",
  "tenant_id": "org123"
}
```

#### POST `/v1/analysis/jailbreak`
Detect jailbreak attempts.

```json
{
  "text": "Text to check",
  "tenant_id": "org123"
}
```

#### POST `/v1/analysis/explain`
Get explanation for flagged content.

```json
{
  "text": "Flagged text",
  "issues": ["toxicity", "bias"],
  "tenant_id": "org123"
}
```

#### POST `/v1/analysis/remediate`
Remediate unsafe content.

```json
{
  "text": "Unsafe text",
  "issue": "toxicity",
  "tenant_id": "org123"
}
```

### Logging & Metrics

#### POST `/v1/log`
Log API call with safety analysis.

#### GET `/v1/metrics`
Get aggregated metrics (usage, safety scores, incidents).

#### GET `/v1/incidents`
Query flagged incidents with filters.

## 🔑 Authentication

All endpoints require:
- **Authorization Header**: `Bearer <api-key>`
- **X-Tenant-ID Header**: `<tenant-id>`

Default API keys (for development):
- `fs-dev-key-123` → `tenant_demo`
- `fs-prod-key-456` → `tenant_prod`

## 📈 Metrics & Observability

FairSight logs comprehensive metrics per API call:

- **Safety Scores**: Toxicity, bias, jailbreak flags
- **Performance**: Latency, overhead, token counts
- **Usage**: Safety Inference Units (SIUs) consumed
- **Incidents**: Flagged content with severity levels

All data is isolated per tenant with encryption at rest.

## 🎛️ Configuration

### Safety Config (SDK)

```python
SafetyConfig(
    on_flag="auto-correct",  # strict | auto-correct | warn-only
    toxicity_threshold=0.7,
    enable_bias_check=True,
    enable_jailbreak_check=True,
    enable_remediation=True,
)
```

### Tenant Config (Backend)

Stored in database per tenant:
- Safety thresholds
- Feature flags (enable/disable checks)
- Privacy settings (anonymization, retention)
- Credit limits (Safety Units)

## 🧪 Testing

Run example scripts:

```bash
# Test SDK
python examples/basic_usage.py

# Test API directly
python examples/test_guardian_api.py
```

## 📝 Development

### Running locally

```bash
# Start backend
uvicorn guardian.main:app --reload --port 8000

# In another terminal, test SDK
python examples/basic_usage.py
```

### Database migrations

```bash
# Auto-generate migration
alembic revision --autogenerate -m "Description"

# Apply migration
alembic upgrade head
```

## 🚢 Deployment

### Docker

```bash
# Build
docker build -t fairsight-guardian .

# Run
docker run -p 8000:8000 --env-file .env fairsight-guardian
```

### Kubernetes

```bash
kubectl apply -f k8s/deployment.yaml
```

## 📜 License

MIT License - see LICENSE file

## 🤝 Contributing

Contributions welcome! Please see CONTRIBUTING.md

## 📚 Documentation

For detailed documentation, see:
- [PRD.md](PRD.md) - Product Requirements Document
- [API Documentation](http://localhost:8000/docs) - Swagger UI (when running)

## 🆘 Support

For issues or questions:
- GitHub Issues: [github.com/yourorg/fairsight/issues]
- Email: support@fairsight.ai

---

Built with ❤️ for AI Safety
