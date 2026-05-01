# Equitas Platform Architecture

**Version:** 2.0.1  
**Last Updated:** March 2025  
**Status:** Production

---

## Overview

The Equitas platform is designed around two complementary execution paths that operate in parallel for every request: a **real-time inline path** that keeps user-facing latency under 50ms, and an **async analysis pipeline** that runs deeper, more compute-intensive safety checks without adding wait time. Together they provide layered, defence-in-depth protection across toxicity, jailbreak, bias, and hallucination categories.

The platform is split into four logical stages:

1. Real-Time Request Path
2. Async Analysis Pipeline
3. Storage & Observability
4. Response & Remediation

---

## Stage 1 — Real-Time Request Path

```
Client Application (Enterprise App)
          │
          ▼
     Edge SDK
  (Optional PII Redaction)
          │
          ▼
    Proxy Layer
  (FastAPI or gRPC)
          │
          ▼
  ┌── Inline Guards ──┐        ← decision node (fast path)
  │  Fast Path Check  │
  └───────┬───────────┘
          │
    ┌─────┼──────────────────┐
    ▼     ▼                  ▼
Sanitizer  Toxicity      Jailbreak
Regex &    Classifier    Signatures
Heuristics Distilled,CPU Database
    │     │                  │
    └─────┴──────────────────┘
          │
    ┌─────┴──────┐
    │            │
  PASS          EMIT
    │            │
    ▼            ▼
 AI Model    Emit Event
 OpenAI /    Compact
 Anthropic / Envelope
 HF Custom       │
                 ▼
           Event Bus
       Kafka or Redis Streams
```

### Components

#### Edge SDK
An optional client-side library that intercepts requests before they leave the enterprise network. Its primary function is **PII redaction** — stripping or masking sensitive identifiers (email addresses, phone numbers, SSNs, credit card numbers) using a regex + NER hybrid approach before the request reaches the Proxy Layer. This ensures no personal data ever flows through Equitas infrastructure unless the operator explicitly opts in.

#### Proxy Layer (FastAPI / gRPC)
The central ingress point. Responsible for:
- **Authentication** — verifying API keys and tenant IDs
- **Credit checks** — ensuring the tenant has sufficient balance before processing
- **Fan-out** — dispatching the request to the Inline Guards in parallel
- **Response assembly** — merging guard results and forwarding safe requests to the AI model

The Proxy Layer adds a deterministic overhead of **<8ms** and exposes both a RESTful HTTP interface and a gRPC interface for high-throughput scenarios.

#### Inline Guards (Fast Path)

Three guards execute in parallel on every request:

| Guard | Method | Latency |
|---|---|---|
| **Sanitizer** | Regex and heuristic pattern matching | <1ms |
| **Toxicity Classifier** | Distilled Detoxify model (RoBERTa, ~30M params) running on CPU | <40ms |
| **Jailbreak Signatures** | Lookup against a pre-computed signature database of known attack vectors | <2ms |

A request clears the fast path only if **all three guards pass**. If any guard triggers, a compact event envelope (containing the original request, metadata, and guard scores) is emitted onto the event bus, and the request is either blocked or forwarded with a warning depending on the tenant's `on_flag` policy (`strict`, `auto-correct`, or `warn-only`).

#### Inline Guard Decision Logic

```
if any(guard.triggered for guard in [sanitizer, toxicity, jailbreak]):
    emit_event(request, scores, metadata)
    if policy == "strict":
        raise SafetyViolationException
    elif policy == "auto-correct":
        forward_to_remediation_engine(request)
    else:  # warn-only
        forward_to_ai_model(request, attach_warning=True)
else:
    forward_to_ai_model(request)  # PASS path
```

#### AI Model (PASS path)
The target language model — OpenAI (GPT-3.5/4), Anthropic (Claude), or any Hugging Face custom endpoint. Equitas is model-agnostic; it wraps the model call transparently. The SDK measures `openai_latency_ms` and `equitas_overhead_ms` separately so operators can see the exact cost of safety checks.

#### Event Bus (EMIT path)
A Kafka topic or Redis Streams channel that receives event envelopes from flagged requests. Consumers in the async pipeline subscribe to this bus. The event bus is the decoupling point that ensures the user-facing response path is never blocked by deep analysis work.

---

## Stage 2 — Async Analysis Pipeline

```
         Event Bus
              │
              ▼
       Worker Pool
    (Autoscaled Analysis)
              │
    ┌─────────┼──────────┬──────────┐
    ▼         ▼          ▼          ▼
Structured  Audio     Image       Text
  Data      Feature   Feature    Feature
Normalizer Extraction Extraction Extraction
    │         │          │          │
    └─────────┴──────────┴──────────┘
                    │
                    ▼
         Unified Embedding Layer
                    │
    ┌───────┬───────┼───────────────┐
    ▼       ▼       ▼               ▼
  Drift  Toxicity  Bias      Hallucination
 Monitor  Module   Module       Module
MMD/KS/  Ensemble Counter-    Claim + RAG
 ADWIN   Checks   factual
                   Tests
```

### Worker Pool
An autoscaled fleet of workers (Kubernetes-managed, GPU-backed) that consume events from the event bus. Workers pick up events, extract modality-specific features, and dispatch the unified representation to the four analysis modules concurrently. Worker count scales with queue depth to maintain constant latency under variable load.

### Feature Extraction
Every incoming event is decomposed into modality-specific feature vectors before being merged:

| Modality | Method | Output |
|---|---|---|
| **Text** | Sentence Transformers (`all-MiniLM-L6-v2`) | 384-dim dense vector |
| **Structured Data** | Column normalisation, type coercion | Tabular feature map |
| **Audio** | Mel-frequency cepstral coefficients (MFCC) | Spectral feature vector |
| **Image** | CLIP-ViT-B/32 visual encoder | 512-dim visual embedding |

All modality vectors are projected into a **shared 512-dim embedding space** (Unified Embedding Layer) using a learned linear projection, enabling cross-modal comparisons and a single pass through downstream detectors.

### Analysis Modules

#### Drift Monitor — MMD / KS / ADWIN
Detects statistical distributional shift in the embedding space over time.

- **Maximum Mean Discrepancy (MMD)** — kernel-based two-sample test comparing the current request distribution against a reference window
- **Kolmogorov–Smirnov (KS) test** — non-parametric test on marginal feature distributions
- **ADWIN (Adaptive Windowing)** — streaming change-point detection for real-time concept drift

Drift alerts are surfaced as dashboard warnings and can trigger automatic model retraining pipelines.

#### Toxicity Module — Ensemble Checks
Runs multiple Detoxify model variants in parallel and aggregates scores:

| Model | Specialisation |
|---|---|
| `original` | General toxicity (Jigsaw dataset) |
| `unbiased` | Debiased toxicity (reduces demographic co-activation) |
| `multilingual` | 100+ language support |

**Scoring:**
```
toxicity_score = max(p_i) across 6 categories
categories = [toxic, severe_toxic, obscene, threat, insult, identity_hate]
flagged = toxicity_score > τ   (τ = 0.7, configurable)
```

**Performance:** F1 > 0.92 (macro), latency <50ms GPU / <200ms CPU.

#### Bias Module — Counterfactual Tests
Detects demographic bias using two complementary methods:

1. **Stereotype Association** — cosine similarity between the response embedding and a library of pre-computed stereotype phrase embeddings, segmented by demographic group (gender, race, age)
2. **Counterfactual Demographic Parity** — generates paired prompt variants with demographic terms swapped (e.g. "male engineer" ↔ "female engineer") and measures the delta in model scores; a delta above threshold flags potential bias

```
bias_score = max(
    stereotype_similarity,
    max_demographic_delta
)
flagged = bias_score > 0.5
```

**Performance:** F1 > 0.80.

#### Hallucination Module — Claim + RAG
A three-component ensemble:

1. **Semantic Consistency** — cosine similarity between prompt and response embeddings; low similarity (<0.5) indicates topic drift or fabrication
2. **Contradiction Detection** — NLI model (`cross-encoder/nli-deberta-v3-base`) checks for internal contradictions between response sentences
3. **RAG Factual Grounding** — extracts factual claims from the response and verifies each against a retrieved context; claims without grounding evidence are flagged as unsupported

```
hallucination_score = w1*consistency_score + w2*contradiction_score + w3*claim_support_score
flagged = hallucination_score > 0.5
```

**Performance:** AUC > 0.85.

---

## Stage 3 — Storage & Observability

```
Async Pipeline Results
         │
    ┌────┴──────────────┐
    ▼                   ▼
Privacy Layer      Time Series DB
DP & On-Prem      Metrics & WORM Logs
    │                   │
    ▼                   ▼
 Data Lake          Vector DB
Object Store    FAISS / Pinecone / Weaviate
```

### Privacy Layer — Differential Privacy & On-Prem
Before any data lands in the Data Lake, the Privacy Layer applies:
- **Differential privacy noise injection** (Laplace mechanism) to aggregated metrics, preventing reverse-engineering of individual requests from aggregate stats
- **On-prem mode** — operators can configure the entire pipeline to run inside their own infrastructure, with zero data leaving their network

### Data Lake — Object Store
Long-term cold storage (S3-compatible) for raw event envelopes, model outputs, and audit trails. Retention policies are configurable per tenant. Used for compliance auditing, model retraining, and ad-hoc analysis.

### Time Series DB — Metrics & WORM Logs
A time-series database (Prometheus + VictoriaMetrics or InfluxDB) storing:
- Per-request latency, toxicity, bias, jailbreak, and hallucination scores
- Aggregate metrics (`total_calls`, `flagged_calls`, `avg_latency_ms`, `safety_units_used`)
- WORM (Write-Once Read-Many) log entries for compliance — immutable audit trail

### Vector DB — FAISS / Pinecone / Weaviate
Stores dense embeddings of all processed requests and responses, enabling:
- **Semantic search** across historical incidents
- **Nearest-neighbour retrieval** for the RAG Hallucination Module
- **Clustering** of bias and toxicity incidents for trend analysis

---

## Stage 4 — Response & Remediation

```
Dashboard & Alerts
        │
        ▼
Remediation Engine
  Rules & LLM Fixes
        │
        ▼
    Alerting
Slack / Jira / Webhooks
        │
        ▼
Human in the Loop
 Review & Retrain
```

### Dashboard & Alerts
A real-time web interface (the Equitas Analytics Dashboard) that aggregates all pipeline outputs:
- **Overview tab** — total calls, flagged rate, avg latency, safety units consumed; toxicity and bias score distributions
- **Logs tab** — per-request log with toxicity/bias/jailbreak scores, latency breakdown, and SHAP/LIME explanations
- **Incidents tab** — flagged events sorted by severity (critical / high / medium / low) with full prompt, response, and remediation context

### Remediation Engine
When a request is flagged and the tenant policy is `auto-correct`, the Remediation Engine rewrites the unsafe content. Two remediation strategies are available:

1. **Rule-based** — template substitution, content stripping, placeholder replacement (deterministic, <5ms)
2. **LLM-based** — a lightweight corrective model rewrites the flagged content to preserve intent while removing the unsafe element (non-deterministic, ~200–500ms)

The engine records the original response alongside the remediated response in the incident log, enabling operators to audit every rewrite.

### Alerting — Slack / Jira / Webhooks
Configurable alerting integrations that fire on:
- Incident severity threshold breach (e.g. any `critical` incident)
- Anomalous flagged-call rate (e.g. >5% in a 5-minute window)
- Drift Monitor alert
- Credit balance approaching zero

### Human in the Loop — Review & Retrain
Incidents that exceed a confidence threshold or are manually escalated enter a human review queue. Reviewers can:
- **Confirm or dismiss** the incident classification
- **Override** the remediation output
- **Export** confirmed incidents as labelled training examples for model fine-tuning

Confirmed incident labels feed directly back into the evaluation framework and can trigger scheduled retraining runs, closing the feedback loop.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Python 3.11, AsyncIO |
| ML Models | PyTorch, Hugging Face Transformers, Detoxify, Sentence-Transformers |
| Embeddings | `all-MiniLM-L6-v2` (384-dim), CLIP-ViT-B/32 |
| NLI | `cross-encoder/nli-deberta-v3-base` |
| Database | MongoDB (primary), PostgreSQL (optional) |
| Event Bus | Apache Kafka or Redis Streams |
| Vector DB | FAISS (embedded), Pinecone or Weaviate (managed) |
| SDK | Python (async + sync), drop-in OpenAI wrapper |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Auth | Clerk (frontend), JWT API keys (backend) |
| Infrastructure | Docker, Kubernetes, NVIDIA GPU nodes |

---

## Resource Requirements

| Component | Minimum | Recommended |
|---|---|---|
| GPU | — | NVIDIA GPU, 8GB+ VRAM |
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| Storage | 10 GB | 50 GB (models + datasets) |

---

## References

- Devlin et al. (2019). BERT: Pre-training of Deep Bidirectional Transformers. *NAACL-HLT*.
- Liu et al. (2019). RoBERTa: A Robustly Optimized BERT Pretraining Approach. *arXiv:1907.11692*.
- Reimers & Gurevych (2019). Sentence-BERT. *EMNLP*.
- He et al. (2021). DeBERTa. *ICLR*.
- Perez et al. (2022). Red Teaming Language Models to Reduce Harms. *arXiv:2209.07858*.
- Zou et al. (2023). Universal and Transferable Adversarial Attacks on Aligned Language Models. *arXiv:2307.15043*.
- Maynez et al. (2020). On Faithfulness and Factuality in Abstractive Summarization. *ACL*.
- Borkan et al. (2019). Nuanced Metrics for Measuring Unintended Bias. *WWW*.
- Nadeem et al. (2021). StereoSet. *ACL*.
