# SHAP & LIME Implementation Summary

## ✅ Implementation Complete

I've implemented a comprehensive SHAP and LIME integration for Equitas to provide detailed explanations for toxicity, bias, and hallucination detection.

## What Was Implemented

### 1. **SHAP Toxicity Explainer** (`backend_api/services/shap_toxicity.py`)
- Token-level SHAP values showing which words contribute most to toxicity
- Category-level explanations (toxic, severe_toxicity, obscene, threat, insult, identity_attack)
- Feature importance ranking (top 10 most impactful tokens)
- Human-readable explanation summaries

### 2. **SHAP Bias Explainer** (`backend_api/services/shap_bias.py`)
- Demographic variant impact analysis (gender, race, age)
- Feature importance for prompt and response tokens
- Bias magnitude quantification
- Fairness violation explanations

### 3. **LIME Hallucination Explainer** (`backend_api/services/lime_hallucination.py`)
- Sentence-level explanations showing which sentences contribute to hallucination
- Claim-level analysis (supported vs unsupported claims)
- Context relevance scoring
- Impact quantification per sentence

### 4. **Enhanced Explainability Service** (`backend_api/services/explainability.py`)
- Integrated SHAP/LIME into existing explainability engine
- Automatic fallback to basic explanations if SHAP/LIME fails
- Support for all issue types: toxicity, bias, jailbreak, hallucination

### 5. **Updated API Schemas** (`backend_api/models/schemas.py`)
- Added `include_shap` and `include_lime` flags to `ExplainRequest`
- Added SHAP/LIME data models:
  - `SHAPTokenExplanation`
  - `SHAPCategoryExplanation`
  - `ToxicitySHAPData`
  - `BiasSHAPData`
  - `HallucinationLIMEData`
- Enhanced `ExplainResponse` with SHAP/LIME fields

### 6. **Enhanced API Endpoints** (`backend_api/api/v1/analysis.py`)
- Updated `/v1/analysis/explain` endpoint to support SHAP/LIME
- Added optional parameters for prompt, response, and context
- Returns detailed explanations with feature importance

## Dependencies Added

- `shap>=0.44.0` - SHAP values for feature importance
- `lime>=0.2.0` - LIME explanations for local interpretability

## How to Use

### Basic Usage (with SHAP/LIME)

```python
import httpx

response = httpx.post(
    "http://localhost:8000/v1/analysis/explain",
    headers={
        "Authorization": "Bearer your-api-key",
        "X-Tenant-ID": "your-tenant-id",
    },
    json={
        "text": "I hate you stupid idiot",
        "issues": ["toxicity"],
        "tenant_id": "your-tenant-id",
        "include_shap": True,  # Enable SHAP values
        "include_lime": False,
    }
)

result = response.json()
print(result["explanation"])
print(result["shap_values"]["toxicity"]["tokens"])  # Token-level importance
```

### Toxicity with SHAP

```python
{
    "text": "I hate you",
    "issues": ["toxicity"],
    "include_shap": True
}

# Returns:
{
    "explanation": "Key contributors to toxicity: hate, you. Primary categories: toxicity, insult.",
    "shap_values": {
        "toxicity": {
            "tokens": [
                {"token": "hate", "shap_value": 0.45, "impact": "high"},
                {"token": "you", "shap_value": 0.12, "impact": "medium"}
            ],
            "category_explanations": {
                "toxicity": {"score": 0.82, "contribution": "high"},
                "insult": {"score": 0.65, "contribution": "medium"}
            }
        }
    }
}
```

### Bias with SHAP

```python
{
    "text": "The response",
    "issues": ["bias"],
    "prompt": "Describe a doctor",
    "response": "The doctor is skilled and professional",
    "include_shap": True
}

# Returns SHAP values showing which demographic variants cause bias
```

### Hallucination with LIME

```python
{
    "text": "The response",
    "issues": ["hallucination"],
    "prompt": "What is the capital of France?",
    "response": "Paris is the capital. The city was founded in 2020.",
    "context": ["Paris is the capital of France", "Paris was founded in the 3rd century BC"],
    "include_lime": True
}

# Returns LIME explanations showing which sentences are hallucinated
```

## Features

### ✅ Token-Level Importance
- Shows which words/tokens contribute most to toxicity/bias scores
- Quantifies impact (high/medium/low)
- Shows positive/negative contributions

### ✅ Category-Level Explanations
- Explains why specific categories were triggered
- Provides confidence scores
- Human-readable descriptions

### ✅ Sentence-Level Analysis
- For hallucination detection
- Shows which sentences contribute to hallucination score
- Claims analysis (supported vs unsupported)

### ✅ Demographic Bias Analysis
- Quantifies bias across demographic variants
- Shows which variants are biased against/toward
- Calculates bias magnitude

### ✅ Automatic Fallback
- If SHAP/LIME fails, falls back to basic pattern matching
- Graceful degradation ensures explanations always available

## Next Steps

1. **Frontend Visualization** (TODO):
   - Create SHAP visualization component
   - Add interactive token highlighting
   - Show waterfall plots for feature importance

2. **Performance Optimization**:
   - Cache SHAP/LIME explanations
   - Optimize background data selection
   - Use faster explainers where possible

3. **Enhanced Features**:
   - Counterfactual explanations ("what if we change this word?")
   - Comparison explanations ("why is this more toxic than that?")
   - Batch explanation support

## Benefits

- 🔍 **Detailed Explanations**: Users understand exactly why content was flagged
- 📊 **Quantifiable**: SHAP/LIME provide numerical feature importance
- 🎯 **Debugging**: Helps identify false positives/negatives
- 📋 **Compliance**: Audit-ready explanations for regulatory requirements
- 🚀 **Competitive**: Matches Fiddler AI's explainability features

