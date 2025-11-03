"""
Test scripts for dataset evaluation.

Run these to evaluate Equitas components on standardized datasets.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.dataset_testing import (
    ToxicityDatasetEvaluator,
    JailbreakDatasetEvaluator,
    HallucinationDatasetEvaluator,
    BiasDatasetEvaluator,
    save_evaluation_report
)

# Import detectors
from backend_api.services.custom_toxicity import get_toxicity_detector
from backend_api.services.advanced_jailbreak import get_jailbreak_detector
from backend_api.services.hallucination import get_hallucination_detector
from backend_api.services.enhanced_bias import get_bias_detector


async def test_toxicity(dataset_path: str, output_path: str = "results/toxicity_results.json"):
    """Test toxicity detection on dataset."""
    print(f"Testing toxicity detection on {dataset_path}")
    
    evaluator = ToxicityDatasetEvaluator(dataset_path)
    detector = get_toxicity_detector()
    
    # Wrapper function
    async def predictor(text: str):
        return await detector.analyze(text)
    
    results = await evaluator.evaluate(predictor)
    metrics = evaluator.calculate_metrics()
    
    # Print metrics
    print("\nToxicity Detection Metrics:")
    print("-" * 60)
    for metric in metrics:
        print(f"{metric.metric_name}: {metric.value:.4f}")
    
    # Save report
    save_evaluation_report(metrics, output_path, Path(dataset_path).stem, "custom_toxicity")
    
    return metrics


async def test_jailbreak(dataset_path: str, output_path: str = "results/jailbreak_results.json"):
    """Test jailbreak detection on dataset."""
    print(f"Testing jailbreak detection on {dataset_path}")
    
    evaluator = JailbreakDatasetEvaluator(dataset_path)
    detector = get_jailbreak_detector()
    
    # Wrapper function
    async def predictor(text: str):
        return await detector.detect(text)
    
    results = await evaluator.evaluate(predictor)
    metrics = evaluator.calculate_metrics()
    
    # Print metrics
    print("\nJailbreak Detection Metrics:")
    print("-" * 60)
    for metric in metrics:
        print(f"{metric.metric_name}: {metric.value:.4f}")
    
    # Save report
    save_evaluation_report(metrics, output_path, Path(dataset_path).stem, "advanced_jailbreak")
    
    return metrics


async def test_hallucination(dataset_path: str, output_path: str = "results/hallucination_results.json"):
    """Test hallucination detection on dataset."""
    print(f"Testing hallucination detection on {dataset_path}")
    
    evaluator = HallucinationDatasetEvaluator(dataset_path)
    detector = get_hallucination_detector()
    
    # Wrapper function
    async def predictor(prompt: str, response: str, context=None):
        return await detector.detect(prompt, response, context)
    
    results = await evaluator.evaluate(predictor)
    metrics = evaluator.calculate_metrics()
    
    # Print metrics
    print("\nHallucination Detection Metrics:")
    print("-" * 60)
    for metric in metrics:
        print(f"{metric.metric_name}: {metric.value:.4f}")
    
    # Save report
    save_evaluation_report(metrics, output_path, Path(dataset_path).stem, "hallucination")
    
    return metrics


async def test_bias(dataset_path: str, output_path: str = "results/bias_results.json"):
    """Test bias detection on dataset."""
    print(f"Testing bias detection on {dataset_path}")
    
    evaluator = BiasDatasetEvaluator(dataset_path)
    detector = get_bias_detector()
    
    # Wrapper function
    async def predictor(prompt: str, response: str, variants=None):
        return await detector.analyze_comprehensive(prompt, response, variants)
    
    results = await evaluator.evaluate(predictor)
    metrics = evaluator.calculate_metrics()
    
    # Print metrics
    print("\nBias Detection Metrics:")
    print("-" * 60)
    for metric in metrics:
        print(f"{metric.metric_name}: {metric.value:.4f}")
    
    # Save report
    save_evaluation_report(metrics, output_path, Path(dataset_path).stem, "enhanced_bias")
    
    return metrics


async def test_all():
    """Run all tests."""
    print("=" * 60)
    print("Equitas Dataset Evaluation Suite")
    print("=" * 60)
    
    # Dataset paths (adjust based on your dataset locations)
    datasets_dir = Path("datasets")
    
    # Toxicity
    if (datasets_dir / "toxicity" / "test.csv").exists():
        await test_toxicity(str(datasets_dir / "toxicity" / "test.csv"))
    
    # Jailbreak
    if (datasets_dir / "jailbreak" / "test.jsonl").exists():
        await test_jailbreak(str(datasets_dir / "jailbreak" / "test.jsonl"))
    
    # Hallucination
    if (datasets_dir / "hallucination" / "test.jsonl").exists():
        await test_hallucination(str(datasets_dir / "hallucination" / "test.jsonl"))
    
    # Bias
    if (datasets_dir / "bias" / "test.jsonl").exists():
        await test_bias(str(datasets_dir / "bias" / "test.jsonl"))
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        test_type = sys.argv[1]
        dataset_path = sys.argv[2] if len(sys.argv) > 2 else None
        
        if test_type == "toxicity" and dataset_path:
            asyncio.run(test_toxicity(dataset_path))
        elif test_type == "jailbreak" and dataset_path:
            asyncio.run(test_jailbreak(dataset_path))
        elif test_type == "hallucination" and dataset_path:
            asyncio.run(test_hallucination(dataset_path))
        elif test_type == "bias" and dataset_path:
            asyncio.run(test_bias(dataset_path))
        else:
            print(f"Usage: python {sys.argv[0]} <toxicity|jailbreak|hallucination|bias> <dataset_path>")
    else:
        # Run all tests
        asyncio.run(test_all())

