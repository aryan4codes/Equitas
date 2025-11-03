# Equitas Changelog

## Version 2.0.1 (2025-01-XX)

### Fixes
- Fixed PyPI upload conflict by bumping version
- Updated project structure (renamed guardian to backend_api)
- Removed all emojis from codebase per professional standards

## Version 2.0.0 (2025-01-XX)

### Major Changes

### New Features

1. **Custom Toxicity Detection**
   - Replaced OpenAI Moderation API with custom transformer models
   - Uses `unitary/toxic-bert` (RoBERTa-based)
   - Supports multiple toxicity categories
   - No external API dependencies

2. **Hallucination Detection**
   - Multi-component ensemble approach
   - Semantic consistency checking
   - Contradiction detection
   - Factuality verification
   - Pattern-based detection
   - Confidence calibration

3. **Advanced Jailbreak Detection**
   - Pattern matching
   - Semantic similarity analysis
   - Behavioral indicators
   - Context-aware detection
   - Adversarial technique detection

4. **Enhanced Bias Detection**
   - Stereotype association detection
   - Demographic parity testing
   - Fairness metrics calculation
   - Intersectional bias detection

5. **Dataset Testing Framework**
   - Comprehensive evaluation suite
   - Support for multiple dataset formats
   - Automated metric calculation
   - Evaluation report generation

### Breaking Changes

- **Toxicity Detection**: Now uses custom models instead of OpenAI API
  - Response format unchanged, but detection method changed
  - Models may need to be downloaded on first run

- **SDK Models**: Added `hallucination_score` and `hallucination_flagged` to `SafetyScores`
  - Update client code to handle new fields

### Migration Guide

1. **Update Dependencies**
   ```bash
   pip install -U equitas
   ```

2. **Download Models** (automatic on first run)
   ```python
   # Models will be downloaded automatically
   # unitary/toxic-bert (~500MB)
   # all-MiniLM-L6-v2 (~80MB)
   # cross-encoder/nli-deberta-v3-base (~440MB)
   ```

3. **Update SDK Usage**
   ```python
   # New hallucination detection is enabled by default
   response = await equitas.chat.completions.create_async(
       model="gpt-4",
       messages=[{"role": "user", "content": "..."}],
       safety_config=SafetyConfig(
           enable_hallucination_check=True  # New option
       )
   )
   
   # Access hallucination scores
   print(response.safety_scores.hallucination_score)
   print(response.safety_scores.hallucination_flagged)
   ```

### Performance

- **Latency**: Increased by ~200-300ms due to ML model inference
- **Throughput**: Supports batch processing for better efficiency
- **GPU**: Automatically uses GPU if available for faster inference

### Documentation

- See `TECHNICAL_ROADMAP.md` for detailed technical documentation
- See `tests/DATASET_TESTING_GUIDE.md` for dataset testing instructions

### Known Issues

- First model download may take several minutes
- Large models require 8GB+ RAM (16GB recommended)
- GPU recommended for production use

### Contributors

- Aryan Rajpurkar (@aryan4codes)

### License

MIT License

