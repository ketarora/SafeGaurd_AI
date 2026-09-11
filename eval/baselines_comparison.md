# Baselines Comparison

## Stage 1 — Intent Classification

| Classifier | Accuracy | Notes |
|---|---|---|
| keyword | 90.0% | n=200 |
| tfidf | 61.5% | n=200 |
| llm | 90.0% | n=200 |

### Per-Intent Accuracy (Main LLM Classifier)

| Intent | Accuracy |
|---|---|
| account_access_issue | 70.6% |
| app_technical_bug | 84.6% |
| cancellation_fee_dispute | 100.0% |
| driver_behavior_complaint | 81.2% |
| driver_unsafe_incident | 97.3% |
| fare_overcharge_dispute | 100.0% |
| general_inquiry | 90.7% |
| lost_item | 86.7% |
| promo_code_failed | 100.0% |
| receipt_request | 83.3% |

## Stage 3 — Escalation

| Strategy | Precision | Recall | F1 | Safety Recall |
|---|---|---|---|---|
| always_escalate | 31.5% | 100.0% | 47.9% | 100.0% |
| never_escalate | 0.0% | 0.0% | 0.0% | 0.0% |
| **main pipeline** | 32.5% | 98.4% | 48.8% | 100.0% |
