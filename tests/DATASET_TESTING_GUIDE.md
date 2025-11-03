# Dataset Testing Guide

This guide explains how to use the dataset testing framework to evaluate Equitas components.

## Setup

### 1. Install Dependencies

```bash
pip install torch transformers sentence-transformers numpy pandas
```

### 2. Download Datasets

Place datasets in the `datasets/` directory with the following structure:

```
datasets/
├── toxicity/
│   ├── test.csv          # Jigsaw Toxic Comments or similar
│   └── README.md
├── jailbreak/
│   ├── test.jsonl         # Jailbreak prompts dataset
│   └── README.md
├── hallucination/
│   ├── test.jsonl         # FEVER, TruthfulQA, or similar
│   └── README.md
└── bias/
    ├── test.jsonl         # BOLD, StereoSet, or similar
    └── README.md
```

### 3. Dataset Formats

#### Toxicity Dataset (CSV)

```csv
comment_text,toxic,severe_toxic,obscene,threat,insult,identity_hate
"This is a comment",0,0,0,0,0,0
```

#### Jailbreak Dataset (JSONL)

```jsonl
{"text": "ignore previous instructions", "is_jailbreak": true}
{"text": "normal question", "is_jailbreak": false}
```

#### Hallucination Dataset (JSONL)

```jsonl
{"prompt": "What is...", "response": "Answer...", "is_hallucination": false, "context": ["fact1", "fact2"]}
{"prompt": "Tell me about...", "response": "Incorrect fact...", "is_hallucination": true, "context": []}
```

#### Bias Dataset (JSONL)

```jsonl
{"prompt": "Describe a...", "response": "A typical...", "has_bias": true, "demographic_variants": [{"group": "gender", "value": "male"}]}
```

## Running Tests

### Run All Tests

```bash
python tests/run_dataset_tests.py
```

### Run Specific Test

```bash
# Toxicity
python tests/run_dataset_tests.py toxicity datasets/toxicity/test.csv

# Jailbreak
python tests/run_dataset_tests.py jailbreak datasets/jailbreak/test.jsonl

# Hallucination
python tests/run_dataset_tests.py hallucination datasets/hallucination/test.jsonl

# Bias
python tests/run_dataset_tests.py bias datasets/bias/test.jsonl
```

## Interpreting Results

Results are saved to `results/` directory as JSON files:

```json
{
  "dataset": "test",
  "model": "custom_toxicity",
  "timestamp": "2024-01-01T00:00:00",
  "metrics": [
    {
      "name": "toxic_precision",
      "value": 0.95,
      "details": {"tp": 100, "fp": 5, "fn": 10, "tn": 885}
    },
    {
      "name": "toxic_recall",
      "value": 0.91,
      "details": {"tp": 100, "fp": 5, "fn": 10, "tn": 885}
    },
    {
      "name": "toxic_f1",
      "value": 0.93,
      "details": {"precision": 0.95, "recall": 0.91}
    }
  ]
}
```

## Metrics Explained

- **Precision**: Proportion of positive predictions that are correct
- **Recall**: Proportion of actual positives that were correctly identified
- **F1-Score**: Harmonic mean of precision and recall
- **Accuracy**: Proportion of correct predictions overall

## Custom Datasets

To add your own dataset:

1. Create a dataset loader class in `tests/dataset_testing.py`
2. Implement `load_dataset()` and `evaluate()` methods
3. Add test function in `tests/run_dataset_tests.py`

## Troubleshooting

### Model Download Issues

If models fail to download, pre-download them:

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
AutoTokenizer.from_pretrained("unitary/toxic-bert")
AutoModelForSequenceClassification.from_pretrained("unitary/toxic-bert")
```

### Memory Issues

For large datasets, process in batches:

```python
# Modify evaluator to process in chunks
for batch in dataset_chunks:
    results.extend(await evaluate_batch(batch))
```

### GPU Availability

Models will automatically use CPU if GPU is not available. For better performance, ensure CUDA is available:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

