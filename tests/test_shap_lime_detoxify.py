#!/usr/bin/env python3
"""
Comprehensive test script for Equitas SHAP/LIME/Detoxify functionality.
Tests all explainability features and displays results.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend_api.services.detoxify_toxicity import get_detoxify_detector
from backend_api.services.shap_toxicity import get_toxicity_shap_explainer
from backend_api.services.shap_bias import get_bias_shap_explainer
from backend_api.services.lime_hallucination import get_hallucination_lime_explainer
from backend_api.services.hallucination import get_hallucination_detector
from backend_api.services.explainability import ExplainabilityEngine
import json


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(title: str, data: dict, indent: int = 2):
    """Pretty print a result dictionary."""
    print(f"\n{title}:")
    print(json.dumps(data, indent=indent, default=str))


async def test_detoxify():
    """Test Detoxify toxicity detection."""
    print_section("TEST 1: Detoxify Toxicity Detection")
    
    try:
        detector = get_detoxify_detector(model_name="original")
        
        test_texts = [
            "This is a normal sentence.",
            "I hate you stupid idiot!",
            "Thank you for your help.",
            "You are such a terrible person.",
        ]
        
        for text in test_texts:
            print(f"\n📝 Text: '{text}'")
            result = await detector.analyze(text)
            
            print(f"   Toxicity Score: {result['toxicity_score']:.3f}")
            print(f"   Flagged: {result['flagged']}")
            print(f"   Categories: {result.get('categories', [])}")
            print(f"   Category Scores: {json.dumps(result.get('category_scores', {}), indent=6)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_shap_toxicity():
    """Test SHAP toxicity explanations."""
    print_section("TEST 2: SHAP Toxicity Explanations")
    
    try:
        detector = get_detoxify_detector(model_name="original")
        shap_explainer = get_toxicity_shap_explainer(detector)
        
        if not shap_explainer:
            print("❌ SHAP explainer not initialized")
            return
        
        test_texts = [
            "I hate you stupid idiot",
            "You are terrible",
            "This is fine",
        ]
        
        for text in test_texts:
            print(f"\n📝 Text: '{text}'")
            result = shap_explainer.explain(text)
            
            print(f"\n   Base Value: {result['base_value']:.3f}")
            print(f"   Total SHAP Value: {result['total_shap_value']:.3f}")
            print(f"\n   Summary: {result['explanation_summary']}")
            
            print(f"\n   Top 5 Most Important Tokens:")
            for i, token_info in enumerate(result['feature_importance'][:5], 1):
                print(f"   {i}. '{token_info['token']}': SHAP={token_info['shap_value']:.3f}, Impact={token_info['impact']}")
            
            print(f"\n   Category Explanations:")
            for category, info in result['category_explanations'].items():
                print(f"   - {category}: Score={info['score']:.3f}, {info['explanation']}")
                
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_shap_bias():
    """Test SHAP bias explanations."""
    print_section("TEST 3: SHAP Bias Explanations")
    
    try:
        bias_shap_explainer = get_bias_shap_explainer()
        
        # Test demographic bias
        prompt = "Describe a doctor"
        response = "The doctor is skilled and professional"
        
        # Simulate demographic variants
        demographic_variants = {
            "gender": ["male", "female", "non-binary"],
        }
        
        variant_scores = {
            "male": 0.1,
            "female": 0.5,
            "non-binary": 0.15,
        }
        
        print(f"\n📝 Prompt: '{prompt}'")
        print(f"📝 Response: '{response}'")
        
        result = bias_shap_explainer.explain_demographic_bias(
            prompt, response, demographic_variants, variant_scores
        )
        
        print_result("Demographic Bias Analysis", result)
        
        # Test feature importance
        print("\n" + "-" * 80)
        print("Feature Importance Analysis:")
        feature_result = bias_shap_explainer.explain_feature_importance(
            prompt, response, 0.3
        )
        
        print(f"\n   Prompt Features:")
        for feat in feature_result['prompt_features'][:5]:
            print(f"   - '{feat['token']}': Importance={feat['importance']:.3f}, Impact={feat['impact']}")
        
        print(f"\n   Response Features:")
        for feat in feature_result['response_features'][:5]:
            print(f"   - '{feat['token']}': Importance={feat['importance']:.3f}, Impact={feat['impact']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_lime_hallucination():
    """Test LIME hallucination explanations."""
    print_section("TEST 4: LIME Hallucination Explanations")
    
    try:
        hallucination_detector = get_hallucination_detector()
        lime_explainer = get_hallucination_lime_explainer(hallucination_detector)
        
        prompt = "What is the capital of France?"
        response = "Paris is the capital of France. The city was founded in 2020 and has a population of 10 million people."
        context = [
            "Paris is the capital of France",
            "Paris was founded in the 3rd century BC",
            "Paris has a population of approximately 2.1 million people"
        ]
        
        print(f"\n📝 Prompt: '{prompt}'")
        print(f"📝 Response: '{response}'")
        print(f"📝 Context: {context}")
        
        result = lime_explainer.explain(prompt, response, context)
        
        print(f"\n   Overall Explanation: {result['overall_explanation']}")
        print(f"   Summary: {result['summary']}")
        
        print(f"\n   Sentence-Level Analysis:")
        for i, sentence_info in enumerate(result['sentences'], 1):
            print(f"\n   Sentence {i}: '{sentence_info['sentence'][:60]}...'")
            print(f"      Hallucination Score: {sentence_info['hallucination_score']:.3f}")
            print(f"      Impact: {sentence_info['impact']:.3f} ({sentence_info['impact_level']})")
            print(f"      Explanation: {sentence_info['explanation']}")
        
        print(f"\n   Claim Analysis:")
        for i, claim_info in enumerate(result['claims'], 1):
            print(f"\n   Claim {i}: '{claim_info['claim'][:60]}...'")
            print(f"      Status: {claim_info['status']}")
            print(f"      Support Score: {claim_info['support_score']:.3f}")
            print(f"      Explanation: {claim_info['explanation']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_explainability_engine():
    """Test the integrated explainability engine."""
    print_section("TEST 5: Integrated Explainability Engine")
    
    try:
        engine = ExplainabilityEngine()
        
        test_cases = [
            {
                "text": "I hate you stupid idiot",
                "issues": ["toxicity"],
                "name": "Toxicity Only"
            },
            {
                "text": "The response",
                "issues": ["bias"],
                "prompt": "Describe a doctor",
                "response": "The female doctor is skilled",
                "name": "Bias with Prompt/Response"
            },
            {
                "text": "The response",
                "issues": ["hallucination"],
                "prompt": "What is the capital of France?",
                "response": "Paris is the capital. It was founded in 2020.",
                "context": ["Paris is the capital of France", "Paris was founded in 3rd century BC"],
                "name": "Hallucination"
            },
        ]
        
        for test_case in test_cases:
            print(f"\n📋 Test Case: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Issues: {test_case['issues']}")
            
            result = await engine.explain(
                text=test_case['text'],
                issues=test_case['issues'],
                prompt=test_case.get('prompt'),
                response=test_case.get('response'),
                include_shap=True,
                include_lime=True,
                context=test_case.get('context'),
            )
            
            print(f"\n   Explanation: {result['explanation']}")
            print(f"   Highlighted Spans: {len(result.get('highlighted_spans', []))} spans")
            
            if result.get('shap_values'):
                print(f"\n   SHAP Values Available:")
                for issue_type in result['shap_values'].keys():
                    print(f"      - {issue_type}")
            
            if result.get('lime_explanations'):
                print(f"\n   LIME Explanations Available:")
                for issue_type in result['lime_explanations'].keys():
                    print(f"      - {issue_type}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_api_endpoint_simulation():
    """Simulate API endpoint calls."""
    print_section("TEST 6: API Endpoint Simulation")
    
    try:
        import httpx
        
        base_url = "http://localhost:8000"
        
        # Test toxicity endpoint
        print("\n1. Testing /v1/analysis/toxicity")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/v1/analysis/toxicity",
                    json={
                        "text": "I hate you",
                        "tenant_id": "test-tenant"
                    },
                    headers={
                        "Authorization": "Bearer test-key",
                        "X-Tenant-ID": "test-tenant"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    print("   ✅ Success!")
                    print(f"   Result: {json.dumps(response.json(), indent=6)}")
                else:
                    print(f"   ⚠️  Status: {response.status_code}")
                    print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ⚠️  Could not connect to API: {e}")
            print("   (Make sure backend is running on http://localhost:8000)")
        
        # Test explain endpoint
        print("\n2. Testing /v1/analysis/explain")
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/v1/analysis/explain",
                    json={
                        "text": "I hate you stupid idiot",
                        "issues": ["toxicity"],
                        "tenant_id": "test-tenant",
                        "include_shap": True,
                        "include_lime": False
                    },
                    headers={
                        "Authorization": "Bearer test-key",
                        "X-Tenant-ID": "test-tenant"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    print("   ✅ Success!")
                    result = response.json()
                    print(f"   Explanation: {result.get('explanation')}")
                    if result.get('shap_values'):
                        print(f"   SHAP Values: ✅ Available")
                        print(f"   Keys: {list(result['shap_values'].keys())}")
                else:
                    print(f"   ⚠️  Status: {response.status_code}")
                    print(f"   Response: {response.text}")
        except Exception as e:
            print(f"   ⚠️  Could not connect to API: {e}")
            print("   (Make sure backend is running on http://localhost:8000)")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests."""
    print("\n" + "🧪 " * 20)
    print("   EQUITAS SHAP/LIME/DETOXIFY TEST SUITE")
    print("🧪 " * 20)
    
    # Run all tests
    await test_detoxify()
    await test_shap_toxicity()
    await test_shap_bias()
    await test_lime_hallucination()
    await test_explainability_engine()
    await test_api_endpoint_simulation()
    
    print_section("TEST SUITE COMPLETE")
    print("\n✅ All tests completed!")
    print("\nNote: API endpoint tests require the backend to be running.")
    print("      Start backend with: python main.py backend")
    print()


if __name__ == "__main__":
    asyncio.run(main())





