# Uber AI Support Agent

> **Hiver SDE Intern Take-Home** — Classify, draft grounded replies, and escalate @Uber_Support customer tweets with evidence it works (and evidence it doesn't).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](requirements.txt)

## What This Does

Given a customer support tweet directed at @Uber_Support, this pipeline:

1. **Classifies** intent (10 categories, including `driver_unsafe_incident`)
2. **Retrieves** similar historically-resolved threads as grounding precedents
3. **Drafts** a reply grounded in those precedents
4. **Decides** auto-handle vs escalate — with a stated reason and hard-coded safety guardrail

Then **proves it works** (and doesn't) via a 200-example golden set, baseline comparisons, LLM-as-judge, and honest failure analysis.

## Quick Start (< 15 Minutes)

```bash
# 1. Clone and setup
git clone <your-repo-url>
cd hiver-prd.md   # or your repo name
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# 2. (Optional) Enable LLM stages
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
# Edit .env → set OPENAI_API_KEY

# 3. Run everything
python scripts/run_all.py
```

**Without an API key:** Pipeline runs in demo mode (keyword classifier + template replies + heuristic judge). Full architecture is testable offline.

**With an API key:** LLM classification, grounded drafting, and LLM-as-judge activate automatically.

### Expected Output

```
outputs/eval_results.json       ← headline metrics
outputs/eval_pipeline_log.jsonl ← per-example trace
outputs/judge_scores.csv        ← LLM judge scores
eval/baselines_comparison.md    ← markdown summary
```

## Demo CLI

```bash
python demo/cli.py "I was overcharged $40 for a 2 mile trip @Uber_Support"
python demo/cli.py   # interactive mode
```

## Project Structure

```
├── src/
│   ├── classify.py      # Stage 1: intent + baselines (keyword, TF-IDF, LLM)
│   ├── retrieve.py      # Embedding-based precedent retrieval
│   ├── draft.py         # Stage 2: grounded reply drafting
│   ├── escalate.py      # Stage 3: escalation with safety hard rule
│   └── pipeline.py      # End-to-end orchestration
├── eval/
│   ├── golden_set.csv           # 200 hand-labeled examples
│   ├── golden_set_notes.md      # Sampling methodology
│   ├── llm_judge.py             # LLM-as-judge harness
│   ├── baselines_comparison.md  # Metrics vs baselines
│   ├── judge_agreement.md       # Judge vs human analysis
│   └── failure_analysis.md      # Top 5 failure modes
├── report/
│   ├── REPORT.md         # 6-page evaluation report
│   └── decision_log.md   # 15 non-obvious decisions
├── demo/cli.py           # Interactive demo
├── scripts/
│   ├── run_all.py        # One-command reproduction
│   ├── prepare_data.py   # Data preparation
│   ├── generate_sample_data.py # NOTE: Demo-only synthetic data fallback. NOT used for final results.
│   └── run_eval.py       # Evaluation harness
└── data/sample/          # Bundled sample data (fast repro)
```

## Using Real Kaggle Data (Optional)

```bash
# Download twcs.csv from Kaggle: thoughtvector/customer-support-on-twitter
# Place at data/raw/twcs.csv
python scripts/prepare_data.py --kaggle data/raw/twcs.csv
python scripts/run_eval.py
```

## Key Design Decisions

- **Safety guardrail is code, not prompt** — `driver_unsafe_incident` always escalates via Python `if` check
- **Conservative escalation** — financial/account disputes default to escalate unless confidence + grounding are both strong
- **Honest eval** — golden set deliberately includes hard cases and oversampled safety incidents; report explains why headline numbers overstate performance

See `report/decision_log.md` for all 15 decisions.

## Evaluation Highlights

| Metric | Main Pipeline | Trivial Baseline | Simple Baseline |
|--------|--------------|------------------|-----------------|
| Intent accuracy | 90.0% (LLM) | 90.0% (keyword) | 61.5% (TF-IDF) |
| Escalation recall | 98.4% | 100.0% (always escalate) | 0.0% (never escalate) |
| Safety recall | **100.0%** | 100.0% | 0.0% |

Read `report/REPORT.md` § "What Is Misleading About My Headline Number?" before quoting any of these.

## Citations & Borrowed Work

- Dataset: [Customer Support on Twitter](https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter) (Kaggle)
- Embeddings: [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- LLM: OpenAI GPT-4o-mini API
- Architecture inspired by RAG-based support systems (retrieval-augmented generation pattern)

## License

MIT — built for Hiver SDE Intern take-home evaluation.
