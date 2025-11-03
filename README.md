# Equitas: AI Safety & Observability Platform

**Enterprise-grade AI safety wrapper for LLM applications**

Equitas is a comprehensive AI safety platform that wraps around OpenAI (and other LLM) APIs to provide real-time toxicity detection, bias checking, hallucination detection, jailbreak prevention, and compliance monitoring. Built for enterprises who need to ensure their AI applications are safe, unbiased, and compliant.

## Key Features

- **Multi-Layer Safety Detection** - Toxicity, bias, hallucination, and jailbreak detection
- **Custom ML Models** - No vendor lock-in, uses open-source transformer models
- **Credit-Based System** - Flexible usage-based billing and credit management
- **Real-Time Analytics** - Comprehensive dashboard with metrics and incident tracking
- **Enterprise Ready** - Multi-tenant architecture with data isolation
- **Easy Integration** - Drop-in replacement for OpenAI API

## Quick Start

### Installation

```bash
pip install equitas
```

### Basic Usage

```python
from equitas_sdk import Equitas, SafetyConfig

# Initialize client
client = Equitas(
    openai_api_key="sk-your-openai-key",
    equitas_api_key="your-equitas-key",
    tenant_id="your-org-id",
    backend_api_url="http://localhost:8000",  # Optional
)

# Make safe API calls
response = await client.chat.completions.create_async(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello!"}],
    safety_config=SafetyConfig(
        on_flag="auto-correct",  # strict | auto-correct | warn-only
        enable_hallucination_check=True,
    )
)

# Access safety metadata
print(f"Toxicity Score: {response.safety_scores.toxicity_score}")
print(f"Hallucination Score: {response.safety_scores.hallucination_score}")
print(f"Bias Flags: {response.safety_scores.bias_flags}")
print(f"Jailbreak Detected: {response.safety_scores.jailbreak_flag}")
```

## Architecture

```
┌─────────────────┐
│  Your App       │
│  + Equitas SDK  │
└────────┬────────┘
         │
         └──────────────► Equitas Backend API
                          ├── Custom Toxicity Detection
                          ├── Bias Detection
                          ├── Jailbreak Prevention
                          ├── Hallucination Detection
                          └── Credit Management
                          
                          ↓
                      
                     Database (Logs, Metrics, Credits)
                     
                          ↓
                          
                     Dashboard & Analytics
```

## Safety Features

### 1. Custom Toxicity Detection
- **Model**: Uses `unitary/toxic-bert` (RoBERTa-based)
- **No OpenAI Dependency**: Fully independent, no vendor lock-in
- **Categories**: Detects toxic, severe toxic, obscene, threat, insult, identity hate
- **Cost**: 1 credit per analysis

### 2. Hallucination Detection
- **Multi-Component**: Semantic consistency, contradiction detection, factuality checking
- **Pattern Analysis**: Detects overconfident language and unsupported claims
- **Context Aware**: Can verify against knowledge base
- **Cost**: 3 credits per analysis

### 3. Advanced Jailbreak Detection
- **Pattern Matching**: Detects known jailbreak patterns
- **Semantic Analysis**: Catches paraphrased attempts
- **Behavioral Detection**: Identifies suspicious indicators
- **Adversarial Detection**: Catches encoding tricks
- **Cost**: 1.5 credits per analysis

### 4. Enhanced Bias Detection
- **Stereotype Association**: Detects stereotype reinforcement
- **Demographic Parity**: Tests fairness across demographics
- **Fairness Metrics**: Statistical parity and equalized odds
- **Intersectional Analysis**: Detects compounding bias
- **Cost**: 2 credits per analysis

### 5. Credit Management System
- **Balance Tracking**: Real-time credit balance monitoring
- **Transaction History**: Full audit trail
- **Usage-Based Billing**: Pay only for what you use
- **Flexible Plans**: Add credits as needed

## Project Structure

```
equitas/
├── equitas_sdk/          # Client SDK
│   ├── client.py         # Main SDK client
│   ├── models.py         # Data models
│   └── exceptions.py    # Custom exceptions
│
├── backend_api/          # Backend API
│   ├── main.py          # FastAPI application
│   ├── api/v1/          # API endpoints
│   │   ├── analysis.py  # Safety analysis endpoints
│   │   ├── credits.py   # Credit management
│   │   ├── metrics.py   # Analytics
│   │   └── incidents.py # Incident tracking
│   ├── services/        # ML services
│   │   ├── custom_toxicity.py
│   │   ├── hallucination.py
│   │   ├── advanced_jailbreak.py
│   │   └── enhanced_bias.py
│   └── models/          # Database models
│
└── examples/            # Usage examples
```

## Setup & Configuration

### 1. Install Dependencies

```bash
pip install equitas
```

### 2. Start Backend API

```bash
# Option 1: Direct run
python -m backend_api.main

# Option 2: Using uvicorn
uvicorn backend_api.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`

### 3. Configure Environment

Create `.env` file:

```bash
# OpenAI (for LLM calls)
OPENAI_API_KEY=sk-your-key-here

# Database
DATABASE_URL=sqlite+aiosqlite:///.equitas.db

# Security
SECRET_KEY=your-secret-key-change-in-production
```

### 4. Add Credits to Tenant

```python
import httpx

# Add credits via API
response = httpx.post(
    "http://localhost:8000/v1/credits/add",
    headers={
        "Authorization": "Bearer your-api-key",
        "X-Tenant-ID": "your-tenant-id",
    },
    json={
        "amount": 1000.0,
        "description": "Initial credits",
    }
)
```

## API Endpoints

### Safety Analysis

#### POST `/v1/analysis/toxicity`
Analyze text for toxicity using custom ML models.

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

#### POST `/v1/analysis/hallucination`
Detect hallucinations in responses.

```json
{
  "prompt": "Original prompt",
  "response": "LLM response",
  "tenant_id": "org123",
  "context": ["fact1", "fact2"]  // Optional
}
```

### Credit Management

#### GET `/v1/credits/balance`
Get current credit balance.

#### POST `/v1/credits/add`
Add credits to account.

```json
{
  "amount": 1000.0,
  "description": "Monthly subscription",
  "reference_type": "subscription"
}
```

#### GET `/v1/credits/transactions`
Get transaction history with pagination.

#### POST `/v1/credits/calculate-cost`
Calculate cost before executing operations.

```json
{
  "operation_types": ["toxicity", "bias", "jailbreak"]
}
```

### Analytics & Metrics

#### GET `/v1/metrics`
Get aggregated metrics (usage, safety scores, incidents).

#### GET `/v1/incidents`
Query flagged incidents with filters.

## Credit System

### Credit Costs

| Operation | Cost (Credits) |
|-----------|----------------|
| Toxicity Detection | 1.0 |
| Bias Detection | 2.0 |
| Jailbreak Detection | 1.5 |
| Hallucination Detection | 3.0 |
| Remediation | 2.0 |
| Full Analysis | 7.5 |

### Handling Insufficient Credits

```python
from equitas_sdk.exceptions import InsufficientCreditsException

try:
    response = await client.chat.completions.create_async(...)
except InsufficientCreditsException as e:
    print(f"Insufficient credits!")
    print(f"Required: {e.required}")
    print(f"Available: {e.available}")
    # Handle error - prompt user to add credits
```

## Testing

### Run Dataset Tests

```bash
# Test all components
python tests/run_dataset_tests.py

# Test specific component
python tests/run_dataset_tests.py toxicity datasets/toxicity/test.csv
```

See [tests/DATASET_TESTING_GUIDE.md](tests/DATASET_TESTING_GUIDE.md) for details.

## Safety Configuration

```python
SafetyConfig(
    on_flag="auto-correct",  # strict | auto-correct | warn-only
    toxicity_threshold=0.7,
    enable_bias_check=True,
    enable_jailbreak_check=True,
    enable_hallucination_check=True,
    enable_remediation=True,
)
```

### Action Modes

- **strict**: Raises exception on safety violation
- **auto-correct**: Automatically remediates unsafe content
- **warn-only**: Returns warnings but allows content

## Deployment

### Docker

```bash
docker build -t equitas .
docker run -p 8000:8000 --env-file .env equitas
```

### Production Considerations

- Use PostgreSQL instead of SQLite
- Configure proper CORS origins
- Set up Redis for caching
- Enable rate limiting
- Use GPU for faster ML inference
- Set up monitoring and alerting

## Documentation

- [Technical Roadmap](TECHNICAL_ROADMAP.md) - Detailed technical documentation
- [Credit System](backend_api/services/CREDIT_SYSTEM.md) - Credit management guide
- [Dataset Testing](tests/DATASET_TESTING_GUIDE.md) - Testing framework guide
- [API Docs](http://localhost:8000/docs) - Interactive Swagger UI (when running)

## What Makes Equitas Stand Out

1. **No Vendor Lock-In** - Custom ML models, no dependency on external APIs
2. **Comprehensive** - Covers toxicity, bias, hallucination, jailbreak, and more
3. **Enterprise Ready** - Multi-tenant, credit system, audit trails
4. **Explainable** - Detailed explanations for every safety flag
5. **Production Ready** - Low latency, scalable, battle-tested
6. **Easy Integration** - Drop-in replacement for OpenAI API

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see LICENSE file

## Support

- **GitHub Issues**: [github.com/aryan4codes/Equitas/issues](https://github.com/aryan4codes/Equitas/issues)
- **Email**: av.rajpurkar@gmail.com
- **Documentation**: [github.com/aryan4codes/Equitas#readme](https://github.com/aryan4codes/Equitas#readme)

---

**Built for AI Safety**

Start protecting your AI applications today with Equitas.
