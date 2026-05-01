# Testing SHAP/LIME/Detoxify

## Quick Test

Run the quick test script:

```bash
python test_shap_lime.py
```

Or use the main entry point:

```bash
python main.py test
```

## Comprehensive Test

For detailed testing with all scenarios:

```bash
python tests/test_shap_lime_detoxify.py
```

## What Gets Tested

### 1. **Detoxify Library**
- Toxicity detection on various texts
- Category scores (toxic, severe_toxicity, obscene, threat, insult, identity_attack)
- Flagged status

### 2. **SHAP Toxicity Explanations**
- Token-level feature importance
- Base value calculation
- Category-level explanations
- Summary generation

### 3. **SHAP Bias Explanations**
- Demographic variant impact analysis
- Feature importance for prompt/response
- Bias magnitude quantification

### 4. **LIME Hallucination Explanations**
- Sentence-level analysis
- Claim support scoring
- Context relevance

### 5. **Integrated Explainability Engine**
- Combined SHAP/LIME support
- Multiple issue types
- Fallback handling

### 6. **API Endpoint Simulation**
- `/v1/analysis/toxicity` endpoint
- `/v1/analysis/explain` endpoint with SHAP/LIME

## Expected Output

```
🚀 Starting Equitas SHAP/LIME/Detoxify Tests...

============================================================
TEST 1: Detoxify Library
============================================================

📝 Testing text: 'I hate you stupid idiot!'
✅ Detoxify working!
   Toxicity Score: 0.823
   Flagged: True
   Categories: ['toxicity', 'insult']

============================================================
TEST 2: SHAP Toxicity Explanations
============================================================

📝 Testing text: 'I hate you'
✅ SHAP working!
   Base Value: 0.045
   Summary: Key contributors to toxicity: hate, you. Primary categories: toxicity, insult.

   Top 3 Tokens:
   1. 'hate': SHAP=0.423
   2. 'you': SHAP=0.156
   3. 'I': SHAP=0.012

...
```

## Troubleshooting

### If Detoxify fails:
- Make sure `detoxify>=0.5.0` is installed
- Check internet connection (first run downloads models)

### If SHAP fails:
- Make sure `shap>=0.44.0` is installed
- Check that models are loaded correctly

### If LIME fails:
- Make sure `lime>=0.2.0` is installed
- Check hallucination detector is initialized

### If API tests fail:
- Make sure backend is running: `python main.py backend`
- Check API key configuration

## Manual Testing

You can also test individual components:

```python
# Test Detoxify
from backend_api.services.detoxify_toxicity import get_detoxify_detector
detector = get_detoxify_detector()
result = await detector.analyze("test text")
print(result)

# Test SHAP
from backend_api.services.shap_toxicity import get_toxicity_shap_explainer
shap_explainer = get_toxicity_shap_explainer(detector)
result = shap_explainer.explain("test text")
print(result)

# Test LIME
from backend_api.services.lime_hallucination import get_hallucination_lime_explainer
from backend_api.services.hallucination import get_hallucination_detector
detector = get_hallucination_detector()
lime_explainer = get_hallucination_lime_explainer(detector)
result = lime_explainer.explain(prompt, response, context)
print(result)
```





