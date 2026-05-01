# SHAP & LIME Integration Guide for Equitas

## Overview

SHAP (SHapley Additive exPlanations) and LIME (Local Interpretable Model-agnostic Explanations) can significantly enhance Equitas's explainability capabilities, providing detailed feature importance and model interpretability for safety detections.

---

## Where SHAP/LIME Add Value

### 1. **Toxicity Detection Explanations** 🔴 **HIGH PRIORITY**

**Current State:**
- Simple pattern matching for toxic words
- Basic text highlighting
- No feature importance scores

**With SHAP/LIME:**
- **Token-level importance**: Which words/tokens contribute most to toxicity score
- **Category explanations**: Why specific categories (toxic, threat, insult) were triggered
- **Counterfactual analysis**: What would need to change to reduce toxicity score

**Integration Points:**
- `backend_api/services/explainability.py` → `_explain_toxicity()`
- `backend_api/api/v1/analysis.py` → `/explain` endpoint
- `backend_api/services/detoxify_toxicity.py` → Use model outputs for SHAP

**Example Output:**
```json
{
  "explanation": "Content flagged as toxic",
  "shap_values": {
    "tokens": [
      {"token": "hate", "shap_value": 0.45, "impact": "high"},
      {"token": "you", "shap_value": 0.12, "impact": "medium"},
      {"token": "are", "shap_value": -0.02, "impact": "low"}
    ],
    "categories": {
      "toxicity": 0.45,
      "insult": 0.38,
      "severe_toxicity": 0.12
    }
  },
  "highlighted_spans": [
    {"start": 0, "end": 4, "text": "hate", "shap_value": 0.45}
  ]
}
```

---

### 2. **Bias Detection Explanations** 🔴 **HIGH PRIORITY**

**Current State:**
- Pattern-based bias detection
- No explanation of which demographic variants cause bias

**With SHAP/LIME:**
- **Demographic variant analysis**: Which demographic swaps cause the biggest score changes
- **Feature importance**: Which parts of prompt/response contribute to bias
- **Fairness explanation**: Quantify how much each demographic attribute affects the score

**Integration Points:**
- `backend_api/services/explainability.py` → `_explain_bias()`
- `backend_api/services/enhanced_bias.py` → Use SHAP on demographic variants
- Frontend dashboard → Visualize demographic parity with SHAP values

**Example Output:**
```json
{
  "explanation": "Detected gender bias in response",
  "shap_values": {
    "demographic_impact": {
      "gender": {
        "male_variant": {"shap_value": 0.15, "direction": "positive"},
        "female_variant": {"shap_value": -0.22, "direction": "negative"},
        "bias_magnitude": 0.37
      }
    },
    "prompt_features": [
      {"feature": "pronoun usage", "shap_value": 0.28},
      {"feature": "professional context", "shap_value": 0.12}
    ]
  }
}
```

---

### 3. **Hallucination Detection Explanations** 🟡 **MEDIUM PRIORITY**

**Current State:**
- Component scores (semantic consistency, factuality)
- No detailed explanation of which parts are hallucinated

**With SHAP/LIME:**
- **Sentence-level importance**: Which sentences contribute most to hallucination score
- **Factuality breakdown**: Which claims are unsupported vs contradicted
- **Context relevance**: How well response aligns with provided context

**Integration Points:**
- `backend_api/services/explainability.py` → Add `_explain_hallucination()`
- `backend_api/services/hallucination.py` → Use LIME for sentence-level explanations
- Frontend analytics → Show hallucination heatmap

**Example Output:**
```json
{
  "explanation": "Response contains unsupported claims",
  "lime_explanation": {
    "sentences": [
      {
        "text": "The company was founded in 2020",
        "lime_score": 0.78,
        "explanation": "No evidence in context",
        "impact": "high"
      },
      {
        "text": "It is a leading AI company",
        "lime_score": 0.45,
        "explanation": "Vague claim",
        "impact": "medium"
      }
    ],
    "components": {
      "factuality": 0.78,
      "semantic_consistency": 0.45,
      "context_relevance": 0.32
    }
  }
}
```

---

### 4. **Jailbreak Detection Explanations** 🟡 **MEDIUM PRIORITY**

**Current State:**
- Pattern-based explanations
- Lists detected techniques

**With SHAP/LIME:**
- **Technique importance**: Which jailbreak techniques contribute most
- **Token-level analysis**: Which specific tokens indicate jailbreak
- **Adversarial pattern explanation**: How encoding tricks affect detection

**Integration Points:**
- `backend_api/services/explainability.py` → `_explain_jailbreak()`
- `backend_api/services/advanced_jailbreak.py` → Use SHAP on detection components

---

### 5. **Dashboard Visualizations** 🟢 **HIGH VALUE**

**Current State:**
- Basic analytics dashboard
- No interactive explanations

**With SHAP/LIME:**
- **SHAP waterfall plots**: Visualize feature contributions
- **LIME explanation tables**: Show local explanations
- **Interactive heatmaps**: Highlight important tokens/features
- **Counterfactual what-if**: Show how changing inputs affects scores

**Integration Points:**
- `Equitas-frontend/src/components/Analytics.tsx` → Add SHAP visualization component
- `Equitas-frontend/src/components/Dashboard.tsx` → Add explanation viewer
- New component: `Equitas-frontend/src/components/ExplanationViewer.tsx`

---

## Implementation Plan

### Phase 1: Toxicity SHAP Integration 🔴

**Files to Modify:**

1. **`backend_api/services/shap_explainer.py`** (NEW)
   ```python
   import shap
   from detoxify import Detoxify
   
   class ToxicitySHAPExplainer:
       """SHAP explainer for toxicity detection."""
       
       def __init__(self, model: Detoxify):
           self.model = model
           self.explainer = shap.Explainer(self._model_predict, self._tokenizer)
       
       def explain(self, text: str) -> Dict[str, Any]:
           # Tokenize and get SHAP values
           # Return token-level importance
   ```

2. **`backend_api/services/explainability.py`**
   - Update `_explain_toxicity()` to use SHAP
   - Add SHAP values to response

3. **`backend_api/models/schemas.py`**
   - Add `shap_values` field to `ExplainResponse`
   - Create `SHAPExplanation` model

**API Changes:**
- `/v1/analysis/explain` → Add `include_shap=True` parameter
- `/v1/analysis/toxicity` → Optionally return SHAP values

---

### Phase 2: Bias SHAP Integration 🔴

**Files to Modify:**

1. **`backend_api/services/bias_shap_explainer.py`** (NEW)
   - SHAP on demographic variants
   - Feature importance for prompt/response

2. **`backend_api/services/explainability.py`**
   - Update `_explain_bias()` to use SHAP

---

### Phase 3: Hallucination LIME Integration 🟡

**Files to Modify:**

1. **`backend_api/services/hallucination_lime.py`** (NEW)
   - LIME for sentence-level explanations
   - Factuality breakdown

2. **`backend_api/services/explainability.py`**
   - Add `_explain_hallucination()` method

---

### Phase 4: Frontend Visualization 🟢

**New Components:**

1. **`Equitas-frontend/src/components/ExplanationViewer.tsx`**
   - SHAP waterfall charts
   - LIME explanation tables
   - Interactive token highlighting

2. **`Equitas-frontend/src/components/SHAPVisualization.tsx`**
   - Token-level importance bars
   - Category contribution pie charts

**Integration:**
- Update `Analytics.tsx` to show explanations
- Add explanation modal for incidents
- Dashboard explanation panel

---

## Dependencies to Add

```toml
# pyproject.toml
dependencies = [
    # ... existing dependencies
    "shap>=0.44.0",  # SHAP values
    "lime>=0.2.0",   # LIME explanations
]
```

---

## API Endpoint Enhancements

### Enhanced `/v1/analysis/explain` Endpoint

```python
@router.post("/explain", response_model=ExplainResponse)
async def explain_issues(
    request: ExplainRequest,
    include_shap: bool = Query(False, description="Include SHAP values"),
    include_lime: bool = Query(False, description="Include LIME explanations"),
    tenant_id: str = Depends(verify_api_key),
):
    """
    Generate explanation for flagged content.
    
    Now supports:
    - SHAP values for feature importance
    - LIME explanations for local interpretability
    - Token-level importance scores
    """
```

### New `/v1/analysis/explain-detailed` Endpoint

```python
@router.post("/explain-detailed")
async def explain_detailed(
    request: DetailedExplainRequest,
    tenant_id: str = Depends(verify_api_key),
):
    """
    Generate detailed explanation with SHAP/LIME.
    
    Returns:
    - SHAP values for all features
    - LIME explanations
    - Counterfactual suggestions
    - Interactive visualization data
    """
```

---

## Use Cases & Benefits

### 1. **Debugging False Positives**
- **Problem**: Content flagged incorrectly
- **Solution**: SHAP shows which tokens triggered false positive
- **Benefit**: Users can adjust thresholds or understand edge cases

### 2. **Compliance Audits**
- **Problem**: Need to explain why content was flagged
- **Solution**: SHAP provides quantifiable feature importance
- **Benefit**: Audit-ready explanations for compliance

### 3. **Model Improvement**
- **Problem**: Understanding model behavior
- **Solution**: SHAP/LIME reveal model decision patterns
- **Benefit**: Identify areas for model fine-tuning

### 4. **User Education**
- **Problem**: Users don't understand safety flags
- **Solution**: Visual explanations show why content was flagged
- **Benefit**: Better user understanding and trust

### 5. **Bias Mitigation**
- **Problem**: Need to understand bias sources
- **Solution**: SHAP shows which demographic variants cause bias
- **Benefit**: Targeted bias mitigation strategies

---

## Performance Considerations

### SHAP Performance
- **Complexity**: O(n * m) where n = samples, m = features
- **Optimization**: 
  - Use `shap.TreeExplainer` for tree-based models (faster)
  - Use `shap.LinearExplainer` for linear models
  - Use `shap.KernelExplainer` as fallback (slower but general)
  - Cache SHAP values for repeated queries

### LIME Performance
- **Complexity**: O(k * m) where k = samples, m = features
- **Optimization**:
  - Use smaller feature sets for faster computation
  - Cache explanations for common queries
  - Use sentence-level LIME (faster than token-level)

### Caching Strategy
```python
# Cache SHAP/LIME explanations
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_shap_explanation(text_hash: str, model_name: str):
    # Compute and cache SHAP values
    pass
```

---

## Example Implementation

### SHAP Integration for Toxicity

```python
# backend_api/services/shap_explainer.py
import shap
import numpy as np
from typing import Dict, Any, List
from detoxify import Detoxify

class ToxicitySHAPExplainer:
    """SHAP explainer for toxicity detection."""
    
    def __init__(self, model: Detoxify):
        self.model = model
        # Use KernelExplainer for general models
        self.explainer = shap.KernelExplainer(
            self._model_predict,
            shap.sample(np.array([""]), 10)  # Background data
        )
    
    def _model_predict(self, texts: np.ndarray) -> np.ndarray:
        """Wrapper for model prediction."""
        results = []
        for text in texts:
            pred = self.model.predict(text)
            # Return max toxicity score
            results.append(max(pred.values()))
        return np.array(results)
    
    def explain(self, text: str) -> Dict[str, Any]:
        """Generate SHAP explanation for text."""
        # Tokenize text
        tokens = text.split()
        
        # Get SHAP values
        shap_values = self.explainer.shap_values([text])
        
        # Format results
        token_shap = [
            {
                "token": token,
                "shap_value": float(shap_val),
                "impact": "high" if abs(shap_val) > 0.3 else "medium" if abs(shap_val) > 0.1 else "low"
            }
            for token, shap_val in zip(tokens, shap_values[0])
        ]
        
        return {
            "tokens": token_shap,
            "base_value": float(self.explainer.expected_value),
            "feature_importance": sorted(token_shap, key=lambda x: abs(x["shap_value"]), reverse=True)
        }
```

---

## Frontend Visualization Example

```typescript
// Equitas-frontend/src/components/SHAPVisualization.tsx
interface SHAPToken {
  token: string;
  shap_value: number;
  impact: "high" | "medium" | "low";
}

export function SHAPVisualization({ tokens }: { tokens: SHAPToken[] }) {
  return (
    <div className="shap-visualization">
      {tokens.map((token, idx) => (
        <span
          key={idx}
          className={`token shap-${token.impact}`}
          style={{
            backgroundColor: token.shap_value > 0 
              ? `rgba(255, 0, 0, ${Math.abs(token.shap_value)})`
              : `rgba(0, 255, 0, ${Math.abs(token.shap_value)})`
          }}
        >
          {token.token}
        </span>
      ))}
    </div>
  );
}
```

---

## Priority Ranking

1. **🔴 HIGH**: Toxicity SHAP (most impactful, easiest to implement)
2. **🔴 HIGH**: Bias SHAP (important for fairness explanations)
3. **🟡 MEDIUM**: Hallucination LIME (useful but less critical)
4. **🟡 MEDIUM**: Jailbreak SHAP (nice to have)
5. **🟢 LOW**: Frontend visualizations (after backend is ready)

---

## Summary

**Where SHAP/LIME Add Value:**
1. ✅ `/v1/analysis/explain` endpoint - Enhanced explanations
2. ✅ Toxicity detection - Token-level importance
3. ✅ Bias detection - Demographic variant analysis
4. ✅ Hallucination detection - Sentence-level explanations
5. ✅ Dashboard - Visual explanations for users

**Key Benefits:**
- 🔍 **Better Explanations**: Quantifiable feature importance
- 🎯 **Debugging**: Understand model decisions
- 📊 **Compliance**: Audit-ready explanations
- 🎨 **Visualization**: Interactive explanation UI
- 🚀 **Competitive Advantage**: Match Fiddler AI's explainability

