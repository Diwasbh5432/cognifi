# CogniFi

**Real-time cognitive bias detection and behavioral intervention for Indonesian retail investors.**

[![arXiv](https://img.shields.io/badge/arXiv-preprint-b31b1b.svg)](https://arxiv.org/abs/XXXX.XXXXX)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Dataset](https://img.shields.io/badge/dataset-HuggingFace-orange.svg)](https://huggingface.co/datasets/redsandr/cognifi-investor-bias)

CogniFi detects FOMO, loss aversion, and confirmation bias from investor-generated text and delivers friction-based behavioral interventions before trade execution. Rule-based and fully interpretable in every output is traceable to specific rules and keyword matches.

> **Paper:** *The Behavioral Layer Gap: Domain-Specific Interpretability Challenges Scale in Low-Resource Safety-Critical Classification, Evidence from Cognitive Bias Detection in Indonesian Retail Investor Text*

---

## Quick start

```bash
git clone https://github.com/redsandr/cognifi.git
cd cognifi
pip install -r requirements.txt
export GEMINI_API_KEY="your-key-here"
streamlit run app.py
```

---

## Results

| System | Accuracy | FOMO F1 | LA F1 | CB F1 | NONE F1 |
|--------|----------|---------|-------|-------|---------|
| Majority class baseline | 29.3% | 0.0% | 0.0% | 0.0% | 45.4% |
| Gemini 3 Flash zero-shot (medium reasoning) | 76.4% | 76.5% | 78.0% | 79.2% | 72.9% |
| **CogniFi (this work)** | **94.7%** | **94.0%** | **95.8%** | **96.2%** | **93.6%** |

**+18.3pp over Gemini 3 Flash** on a stratified held-out set of 150 cases.

**Code-switching finding:** Gemini accuracy drops from 80.0% on monolingual Indonesian to 64.1% on code-switching samples (−15.9pp). CogniFi maintains 91.6% on the same samples. The gap is distributional, not architectural, terms like `masih sempet ga` and `serok bareng` are absent from any general-purpose training corpus.

---

## How it works

CogniFi runs a six-layer rule-based pipeline:

```
Input text
    │
    ├── Layer 1: Early exit (analytical/educational text → NONE)
    ├── Layer 2: Price context (Yahoo Finance real-time data)
    ├── Layer 3: Keyword scoring (1,307 terms, 13 categories)
    ├── Layer 4: Contextual adjustments (57 rules)
    ├── Layer 5: Confidence thresholding
    └── Layer 6: Signal construction
         │
         ▼
    Bias label + confidence + counter-evidence + friction prompt
```

The rule-based design is intentional. In behavioral intervention contexts, unexplainable outputs are dismissed precisely when intervention is most needed.

---

## Dataset

1,193 labeled samples of authentic Indonesian retail investor posts, collected from five platforms.

| Platform | Training | % |
|----------|----------|---|
| Stockbit | 882 | 84.6% |
| X.com | 85 | 8.1% |
| Reddit | 32 | 3.1% |
| WhatsApp | 23 | 2.2% |
| Threads | 21 | 2.0% |

**Language distribution:**

| Category | n | % |
|----------|---|---|
| Monolingual Indonesian | 844 | 70.7% |
| Intra-sentential code-switching | 307 | 25.7% |
| Monolingual English | 42 | 3.5% |

Language detection uses hybrid FastText LID + domain lexicon overlap.

Inter-annotator agreement: **Cohen's Kappa = 0.7815** (substantial agreement, Landis & Koch 1977), across two domain-qualified annotators (n=100 samples).

---

## Repository structure

```
cognifi/
├── bias_detector.py      # 6-layer detection pipeline
├── keywords.py           # 1,307-term domain lexicon
├── counter_evidence.py   # Historical backtesting engine
├── intervention.py       # Friction and Pre-Mortem prompts
├── ticker_extractor.py   # Ticker detection
├── price_fetcher.py      # Yahoo Finance data layer
├── fundamental_data.py   # IDX fundamentals (10 tickers)
├── llm.py                # Gemini API wrapper
├── news_context.py       # News sentiment layer
├── rag.py                # ChromaDB RAG engine
├── app.py                # Streamlit web app
├── config.py             # Configuration
├── evaluate_final.py     # Held-out evaluation
├── gemini_baseline.py    # Gemini baseline script
├── test_bias_accuracy.py # Training accuracy script
└── data/
    ├── training_v2.json        # 1,043 training cases with provenance
    └── held_out_TEST_ONLY.json # 150 held-out cases (labels withheld)
```

---

## Reproduce results

```bash
# Training set accuracy
python test_bias_accuracy.py

# Gemini 3 Flash baseline (requires API key)
python gemini_baseline.py
```

The held-out answer key is not included to prevent data leakage. Evaluation results are documented in the paper.

---

## Counter-evidence engine

For 10 covered IDX tickers, the engine surfaces historical precedents relevant to the detected bias. Outputs are base rates, not predictions.

| Ticker | FOMO Episodes | Correction Prob. | LA Episodes | Recovery Rate | Avg Days |
|--------|:---:|:---:|:---:|:---:|:---:|
| BBCA.JK | — | — | 75 | 100% | 2 |
| BBRI.JK | 4 | 50% | 76 | 100% | 4 |
| TLKM.JK | — | — | 97 | 100% | 3 |
| ASII.JK | — | — | 95 | 100% | 8 |
| BMRI.JK | — | — | 78 | 100% | 3 |
| UNVR.JK | 10 | 50% | 111 | 95% | 7 |
| GOTO.JK | 10 | 20% | 44 | 95% | 7 |
| BREN.JK | 17 | 18% | 20 | 90% | 5 |
| EMTK.JK | 18 | 22% | 113 | 100% | 1 |
| SIDO.JK | 6 | 50% | 93 | 95% | 10 |

`—` = no episodes meeting the >20% 5-day FOMO threshold. System returns an explicit `insufficient_data` response rather than generating output from inadequate samples.

---


## License

MIT. See [LICENSE](LICENSE).

Dataset released for research use. All samples are authentic user-generated content from Indonesian retail investor communities (Stockbit, X.com, Reddit, Threads).
