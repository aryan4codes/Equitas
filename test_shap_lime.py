#!/usr/bin/env python3
"""
Quick test script for Detoxify, SHAP, and LIME.
Run this to verify everything works.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🚀 Starting Equitas SHAP/LIME/Detoxify Tests...\n")

# Test 1: Detoxify
print("=" * 60)
print("TEST 1: Detoxify Library")
print("=" * 60)
try:
    from backend_api.services.detoxify_toxicity import get_detoxify_detector
    
    detector = get_detoxify_detector(model_name="original")
    
    test_text = "I hate you stupid idiot!"
    print(f"\n📝 Testing text: '{test_text}'")
    
    result = asyncio.run(detector.analyze(test_text))
    
    print(f"✅ Detoxify working!")
    print(f"   Toxicity Score: {result['toxicity_score']:.3f}")
    print(f"   Flagged: {result['flagged']}")
    print(f"   Categories: {result.get('categories', [])}")
except Exception as e:
    print(f"❌ Detoxify test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 2: SHAP Toxicity
print("\n" + "=" * 60)
print("TEST 2: SHAP Toxicity Explanations")
print("=" * 60)
try:
    from backend_api.services.detoxify_toxicity import get_detoxify_detector
    from backend_api.services.shap_toxicity import get_toxicity_shap_explainer
    
    detector = get_detoxify_detector(model_name="original")
    shap_explainer = get_toxicity_shap_explainer(detector)
    
    if shap_explainer:
        test_text = "I hate you"
        print(f"\n📝 Testing text: '{test_text}'")
        
        result = shap_explainer.explain(test_text)
        
        print(f"✅ SHAP working!")
        print(f"   Base Value: {result['base_value']:.3f}")
        print(f"   Summary: {result['explanation_summary']}")
        
        if result.get('feature_importance'):
            print(f"\n   Top 3 Tokens:")
            for i, token in enumerate(result['feature_importance'][:3], 1):
                print(f"   {i}. '{token['token']}': SHAP={token['shap_value']:.3f}")
    else:
        print("❌ SHAP explainer not initialized")
except Exception as e:
    print(f"❌ SHAP test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 3: SHAP Bias
print("\n" + "=" * 60)
print("TEST 3: SHAP Bias Explanations")
print("=" * 60)
try:
    from backend_api.services.shap_bias import get_bias_shap_explainer
    
    bias_explainer = get_bias_shap_explainer()
    
    prompt = "Describe a doctor"
    response = "The doctor is skilled"
    
    print(f"\n📝 Prompt: '{prompt}'")
    print(f"📝 Response: '{response}'")
    
    result = bias_explainer.explain_feature_importance(prompt, response, 0.3)
    
    print(f"✅ SHAP Bias working!")
    print(f"   Summary: {result['summary']}")
    
    if result.get('prompt_features'):
        print(f"\n   Top Prompt Features:")
        for feat in result['prompt_features'][:3]:
            print(f"   - '{feat['token']}': {feat['importance']:.3f}")
except Exception as e:
    print(f"❌ SHAP Bias test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 4: LIME Hallucination
print("\n" + "=" * 60)
print("TEST 4: LIME Hallucination Explanations")
print("=" * 60)
try:
    from backend_api.services.hallucination import get_hallucination_detector
    from backend_api.services.lime_hallucination import get_hallucination_lime_explainer
    
    detector = get_hallucination_detector()
    lime_explainer = get_hallucination_lime_explainer(detector)
    
    prompt = "What is the capital of France?"
    response = "Paris is the capital. It was founded in 2020."
    context = ["Paris is the capital of France", "Paris was founded in 3rd century BC"]
    
    print(f"\n📝 Prompt: '{prompt}'")
    print(f"📝 Response: '{response}'")
    
    result = lime_explainer.explain(prompt, response, context)
    
    print(f"✅ LIME working!")
    print(f"   Overall: {result['overall_explanation']}")
    print(f"   Summary: {result['summary']}")
    
    if result.get('sentences'):
        print(f"\n   Sentence Analysis:")
        for sent in result['sentences'][:2]:
            print(f"   - '{sent['sentence'][:50]}...': Impact={sent['impact']:.3f}")
except Exception as e:
    print(f"❌ LIME test failed: {e}")
    import traceback
    traceback.print_exc()

# Test 5: Integrated Explainability Engine
print("\n" + "=" * 60)
print("TEST 5: Integrated Explainability Engine")
print("=" * 60)
try:
    from backend_api.services.explainability import ExplainabilityEngine
    
    engine = ExplainabilityEngine()
    
    result = asyncio.run(engine.explain(
        text="I hate you stupid idiot",
        issues=["toxicity"],
        include_shap=True,
        include_lime=False
    ))
    
    print(f"✅ Explainability Engine working!")
    print(f"   Explanation: {result['explanation']}")
    print(f"   Highlighted Spans: {len(result.get('highlighted_spans', []))}")
    print(f"   SHAP Values: {'✅' if result.get('shap_values') else '❌'}")
except Exception as e:
    print(f"❌ Explainability Engine test failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("✨ ALL TESTS COMPLETE!")
print("=" * 60)
print("\nIf all tests passed, your SHAP/LIME/Detoxify integration is working! 🎉\n")





