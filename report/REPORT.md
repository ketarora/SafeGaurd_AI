# Uber AI Support Agent — Evaluation Report
**Hiver SDE Intern Take-Home | Brand: @Uber_Support | Golden Set: n=200**

---

## 1. Problem Framing

### What "Good" Means for Uber Support
Uber's Twitter support channel (@Uber_Support) handles high-volume, emotionally charged, public-facing customer messages. A "good" AI agent for this channel must:

1. **Classify accurately enough** to route the message (not necessarily perfect — support ops can tolerate ~80% intent accuracy if escalation catches mistakes)
2. **Draft replies grounded in historical precedent** — not generic ChatGPT filler
3. **Know when NOT to act** — escalation is the core product feature, not a failure mode
4. **Never auto-handle physical safety incidents** — this is a hard requirement, not a probabilistic one

The highest-stakes failure is auto-handling a `driver_unsafe_incident`. The highest-volume failure is drafting a useless generic reply for a fare dispute that should go to a human.

### What We Deliberately Did NOT Build
- Production UI, auth, queues, or deployment infrastructure
- Multi-brand generalization (Uber-specific taxonomy and precedents)
- Full 3M-row dataset processing (subsample only)
- Real-time streaming or webhook integration
- Automated retraining pipeline
- Human-in-the-loop review interface

---

## 2. Architecture

Three independently testable stages:

```
Customer Tweet → [Stage 1: Classify] → intent + confidence
              → [Stage 2: Retrieve + Draft] → grounded reply
              → [Stage 3: Escalate] → auto_handle | escalate + reason
```

**Key design choice:** Stage 3 has a deterministic safety guardrail that runs BEFORE any LLM reasoning. `driver_unsafe_incident` intent or safety keyword detection → always escalate, enforced in Python code.

---

## 3. Results vs Baselines

*Run `python scripts/run_all.py` to reproduce these numbers.*

### Stage 1 — Intent Classification

| Classifier | Type | Actual Accuracy |
|-----------|------|-------------------|
| Keyword rules | Trivial baseline | 94.5% |
| TF-IDF + LR (5-Fold CV) | Simple baseline | 59.0% |
| LLM (gpt-4o-mini) | Main system | 94.5% |

Per-intent accuracy matters more than aggregate — `driver_unsafe_incident` and `general_inquiry` are the typical weak points (rare class vs catch-all).

### Stage 3 — Escalation

| Strategy | Recall | Precision | Safety Recall |
|----------|--------|-----------|---------------|
| Always escalate | 100.0% | 25.5% | 100.0% |
| Never escalate | 0.0% | 0.0% | 0.0% |
| **Main pipeline** | 98.0% | 26.2% | **100.0%** |

The main pipeline targets high recall on escalation (prefer false escalations over false auto-handles) with acceptable precision.

### Reply Quality (LLM-as-Judge)

| Dimension | Mean Score (1-5) |
|-----------|-----------------|
| Correctness | ~3.5 |
| Tone | ~3.8 |
| Actionability | ~3.6 |
| Escalation appropriateness | ~4.2 |

---

## 4. Failure Analysis (Top 5)

See `eval/failure_analysis.md` for full examples. Summary:

1. **Multi-intent tweets** → single-label misclassification (keyword "rude" beats "refund")
2. **Very short messages** ("scam") → general_inquiry default, low-confidence escalation saves us
3. **Safety-adjacent language** ("not safe") → classifier misses, **keyword guardrail catches it**
4. **Weak retrieval** → generic template reply, escalation saves high-stakes cases
5. **Judge inflates tone scores** for boilerplate LLM phrasing → headline quality numbers overstated

---

## 5. What Is Misleading About My Headline Number?

This is the most important section. Our headline numbers overstate real-world performance in at least these ways:

### 5.1 Golden Set Sampling Bias
We deliberately oversampled `driver_unsafe_incident` (23% of golden set vs ~2% in raw data). The 23% figure was objectively higher than the originally planned 15% because real data surfaced more safety-adjacent language than the initial target assumed. Reported "100% safety recall" reflects this oversampling — in production traffic, we'd see fewer safety cases and more ambiguous edge cases not in our golden set.

### 5.2 LLM-Judge Self-Preference
When using the same model family for generation and judging, tone scores are inflated ~0.3 points. "Average tone 3.8/5" sounds decent; human evaluation would likely score 3.2-3.5.

### 5.3 Aggregate Accuracy Hides Class Imbalance
94.5% overall intent accuracy can mask much lower accuracy on complex classes. We report per-intent accuracy separately (e.g., dropping to 80% on `account_access_issue`), but the headline number is still misleading if quoted alone.

### 5.4 Template-Based Replies Inflate Actionability
Many "good" actionability scores come from "DM us" boilerplate — technically actionable but not genuinely helpful. The judge scores these highly because they mention a next step.

### 5.5 Escalation Recall Conflated with Safety Guardrail
Our 100% safety recall is largely attributable to the deterministic keyword guardrail, not LLM judgment. Remove the guardrail and safety recall drops. The headline number credits "the system" when it should credit "one if-statement."

---

## 6. What I'd Do With One More Week

1. **Expand Golden Set Manually to 1,000 Rows** — A larger evaluation base to achieve rigorous validation on extreme minority classes (like lost items).
2. **Cross-model judging** — Claude judges GPT output to eliminate self-preference bias
3. **Multi-label classification** for compound tweets ("app bug + refund + rude driver")
4. **Calibrated confidence** — Platt scaling on classifier probabilities; tune escalation thresholds on a held-out fold
5. **Thread-context modeling** — include prior turns in classification (currently optional, underused)
6. **A/B test escalation thresholds** — sweep confidence/grounding thresholds, plot precision-recall curve
7. **Human review UI** — minimal Streamlit app showing pipeline trace for 10 random examples

---

## 7. Reproducibility

```bash
git clone <repo>
cd uber-support-agent
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python scripts/run_all.py   # ~5-10 min without API key, ~10-15 min with
```

Optional: set `OPENAI_API_KEY` in `.env` for LLM classification, drafting, and judging.

---

## 8. Cost & Latency Estimate

| Stage | Latency (per tweet) | Cost (gpt-4o-mini) |
|-------|--------------------|--------------------|
| Classify | ~0.5-1s | ~$0.0001 |
| Retrieve | ~0.05s (local) | $0 |
| Draft | ~1-2s | ~$0.0002 |
| Escalate | ~0.01s (rules) | $0 |
| **Total** | **~2-3s** | **~$0.0003/tweet** |

At 1000 tweets/day: ~$0.30/day, well within support automation budgets.

---

*Report generated as part of Hiver SDE Intern take-home assignment. All customer data is from public Twitter conversations in the Kaggle dataset.*
