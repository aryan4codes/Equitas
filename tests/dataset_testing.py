"""
Dataset testing framework for Equitas safety components.

Supports evaluation on standardized datasets with comprehensive metrics.
"""

import json
import csv
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import numpy as np
from dataclasses import dataclass
from datetime import datetime


@dataclass
class EvaluationResult:
    """Result of a single evaluation."""
    true_label: Any
    predicted_label: Any
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class MetricResult:
    """Aggregated metric result."""
    metric_name: str
    value: float
    details: Dict[str, Any]


class DatasetEvaluator:
    """Base class for dataset evaluation."""
    
    def __init__(self, dataset_path: str):
        """
        Initialize dataset evaluator.
        
        Args:
            dataset_path: Path to dataset file
        """
        self.dataset_path = Path(dataset_path)
        self.results: List[EvaluationResult] = []
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load dataset from file."""
        raise NotImplementedError
    
    async def evaluate(self, predictor) -> List[EvaluationResult]:
        """Evaluate predictor on dataset."""
        raise NotImplementedError
    
    def calculate_metrics(self) -> List[MetricResult]:
        """Calculate evaluation metrics."""
        raise NotImplementedError


class ToxicityDatasetEvaluator(DatasetEvaluator):
    """Evaluator for toxicity detection datasets."""
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load toxicity dataset."""
        data = []
        
        if self.dataset_path.suffix == '.csv':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data.append({
                        'text': row.get('comment_text', row.get('text', '')),
                        'labels': {
                            'toxic': int(row.get('toxic', 0)),
                            'severe_toxic': int(row.get('severe_toxic', 0)),
                            'obscene': int(row.get('obscene', 0)),
                            'threat': int(row.get('threat', 0)),
                            'insult': int(row.get('insult', 0)),
                            'identity_hate': int(row.get('identity_hate', 0)),
                        }
                    })
        elif self.dataset_path.suffix == '.jsonl':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data.append(json.loads(line))
        
        return data
    
    async def evaluate(self, predictor) -> List[EvaluationResult]:
        """Evaluate toxicity predictor."""
        dataset = self.load_dataset()
        results = []
        
        for item in dataset:
            text = item['text']
            true_labels = item['labels']
            
            # Run predictor
            prediction = await predictor(text)
            
            # Extract predicted labels
            predicted_labels = {
                cat: prediction.get('category_scores', {}).get(cat, 0) > 0.5
                for cat in ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
            }
            
            result = EvaluationResult(
                true_label=true_labels,
                predicted_label=predicted_labels,
                confidence=prediction.get('toxicity_score', 0.0),
                metadata={'text': text[:100]}  # First 100 chars
            )
            results.append(result)
        
        self.results = results
        return results
    
    def calculate_metrics(self) -> List[MetricResult]:
        """Calculate toxicity detection metrics."""
        if not self.results:
            return []
        
        metrics = []
        
        # For each category
        categories = ['toxic', 'severe_toxic', 'obscene', 'threat', 'insult', 'identity_hate']
        
        for category in categories:
            # Binary classification metrics
            tp = sum(1 for r in self.results 
                    if r.true_label.get(category, 0) == 1 and r.predicted_label.get(category, False))
            tn = sum(1 for r in self.results 
                    if r.true_label.get(category, 0) == 0 and not r.predicted_label.get(category, False))
            fp = sum(1 for r in self.results 
                    if r.true_label.get(category, 0) == 0 and r.predicted_label.get(category, False))
            fn = sum(1 for r in self.results 
                    if r.true_label.get(category, 0) == 1 and not r.predicted_label.get(category, False))
            
            # Calculate metrics
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
            accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
            
            metrics.append(MetricResult(
                metric_name=f"{category}_precision",
                value=precision,
                details={'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}
            ))
            metrics.append(MetricResult(
                metric_name=f"{category}_recall",
                value=recall,
                details={'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}
            ))
            metrics.append(MetricResult(
                metric_name=f"{category}_f1",
                value=f1,
                details={'precision': precision, 'recall': recall}
            ))
            metrics.append(MetricResult(
                metric_name=f"{category}_accuracy",
                value=accuracy,
                details={}
            ))
        
        # Overall toxicity score (max across categories)
        overall_accuracy = np.mean([m.value for m in metrics if 'accuracy' in m.metric_name])
        overall_f1 = np.mean([m.value for m in metrics if 'f1' in m.metric_name])
        
        metrics.append(MetricResult(
            metric_name="overall_accuracy",
            value=overall_accuracy,
            details={}
        ))
        metrics.append(MetricResult(
            metric_name="overall_f1",
            value=overall_f1,
            details={}
        ))
        
        return metrics


class JailbreakDatasetEvaluator(DatasetEvaluator):
    """Evaluator for jailbreak detection datasets."""
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load jailbreak dataset."""
        data = []
        
        if self.dataset_path.suffix == '.jsonl':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data.append(json.loads(line))
        elif self.dataset_path.suffix == '.json':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        return data
    
    async def evaluate(self, predictor) -> List[EvaluationResult]:
        """Evaluate jailbreak predictor."""
        dataset = self.load_dataset()
        results = []
        
        for item in dataset:
            text = item.get('text', item.get('prompt', ''))
            true_label = item.get('is_jailbreak', item.get('label', False))
            
            # Run predictor
            prediction = await predictor(text)
            
            predicted_label = prediction.get('jailbreak_flag', False)
            confidence = prediction.get('confidence', 0.0)
            
            result = EvaluationResult(
                true_label=true_label,
                predicted_label=predicted_label,
                confidence=confidence,
                metadata={'text': text[:100]}
            )
            results.append(result)
        
        self.results = results
        return results
    
    def calculate_metrics(self) -> List[MetricResult]:
        """Calculate jailbreak detection metrics."""
        if not self.results:
            return []
        
        tp = sum(1 for r in self.results if r.true_label and r.predicted_label)
        tn = sum(1 for r in self.results if not r.true_label and not r.predicted_label)
        fp = sum(1 for r in self.results if not r.true_label and r.predicted_label)
        fn = sum(1 for r in self.results if r.true_label and not r.predicted_label)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        
        return [
            MetricResult("precision", precision, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("recall", recall, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("f1", f1, {'precision': precision, 'recall': recall}),
            MetricResult("accuracy", accuracy, {}),
        ]


class HallucinationDatasetEvaluator(DatasetEvaluator):
    """Evaluator for hallucination detection datasets."""
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load hallucination dataset."""
        data = []
        
        if self.dataset_path.suffix == '.jsonl':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data.append(json.loads(line))
        
        return data
    
    async def evaluate(self, predictor) -> List[EvaluationResult]:
        """Evaluate hallucination predictor."""
        dataset = self.load_dataset()
        results = []
        
        for item in dataset:
            prompt = item.get('prompt', item.get('question', ''))
            response = item.get('response', item.get('answer', ''))
            true_label = item.get('is_hallucination', item.get('label', False))
            context = item.get('context', item.get('evidence', []))
            
            # Run predictor
            prediction = await predictor(prompt, response, context)
            
            predicted_label = prediction.get('flagged', False)
            confidence = prediction.get('hallucination_score', 0.0)
            
            result = EvaluationResult(
                true_label=true_label,
                predicted_label=predicted_label,
                confidence=confidence,
                metadata={'prompt': prompt[:100], 'response': response[:100]}
            )
            results.append(result)
        
        self.results = results
        return results
    
    def calculate_metrics(self) -> List[MetricResult]:
        """Calculate hallucination detection metrics."""
        if not self.results:
            return []
        
        tp = sum(1 for r in self.results if r.true_label and r.predicted_label)
        tn = sum(1 for r in self.results if not r.true_label and not r.predicted_label)
        fp = sum(1 for r in self.results if not r.true_label and r.predicted_label)
        fn = sum(1 for r in self.results if r.true_label and not r.predicted_label)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        
        # AUC-ROC approximation
        sorted_results = sorted(self.results, key=lambda x: x.confidence, reverse=True)
        # Simple AUC approximation
        auc = 0.0
        if len(sorted_results) > 1:
            # Simplified AUC calculation
            positives = sum(1 for r in sorted_results if r.true_label)
            negatives = len(sorted_results) - positives
            if positives > 0 and negatives > 0:
                tp_cum = 0
                auc = 0.0
                for i, r in enumerate(sorted_results):
                    if r.true_label:
                        tp_cum += 1
                    else:
                        auc += tp_cum / positives
                auc /= negatives
        
        return [
            MetricResult("precision", precision, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("recall", recall, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("f1", f1, {'precision': precision, 'recall': recall}),
            MetricResult("accuracy", accuracy, {}),
            MetricResult("auc_roc", auc, {}),
        ]


class BiasDatasetEvaluator(DatasetEvaluator):
    """Evaluator for bias detection datasets."""
    
    def load_dataset(self) -> List[Dict[str, Any]]:
        """Load bias dataset."""
        data = []
        
        if self.dataset_path.suffix == '.jsonl':
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data.append(json.loads(line))
        
        return data
    
    async def evaluate(self, predictor) -> List[EvaluationResult]:
        """Evaluate bias predictor."""
        dataset = self.load_dataset()
        results = []
        
        for item in dataset:
            prompt = item.get('prompt', '')
            response = item.get('response', '')
            true_label = item.get('has_bias', item.get('is_biased', False))
            variants = item.get('demographic_variants', None)
            
            # Run predictor
            prediction = await predictor(prompt, response, variants)
            
            predicted_label = prediction.get('bias_detected', False)
            confidence = prediction.get('bias_score', 0.0)
            
            result = EvaluationResult(
                true_label=true_label,
                predicted_label=predicted_label,
                confidence=confidence,
                metadata={'prompt': prompt[:100], 'response': response[:100]}
            )
            results.append(result)
        
        self.results = results
        return results
    
    def calculate_metrics(self) -> List[MetricResult]:
        """Calculate bias detection metrics."""
        if not self.results:
            return []
        
        tp = sum(1 for r in self.results if r.true_label and r.predicted_label)
        tn = sum(1 for r in self.results if not r.true_label and not r.predicted_label)
        fp = sum(1 for r in self.results if not r.true_label and r.predicted_label)
        fn = sum(1 for r in self.results if r.true_label and not r.predicted_label)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        
        return [
            MetricResult("precision", precision, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("recall", recall, {'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn}),
            MetricResult("f1", f1, {'precision': precision, 'recall': recall}),
            MetricResult("accuracy", accuracy, {}),
        ]


def save_evaluation_report(
    metrics: List[MetricResult],
    output_path: str,
    dataset_name: str,
    model_name: str
):
    """Save evaluation report to file."""
    report = {
        'dataset': dataset_name,
        'model': model_name,
        'timestamp': datetime.now().isoformat(),
        'metrics': [
            {
                'name': m.metric_name,
                'value': m.value,
                'details': m.details
            }
            for m in metrics
        ]
    }
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"Evaluation report saved to {output_path}")

