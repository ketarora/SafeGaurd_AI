# Baselines Comparison

## Stage 1 — Intent Classification

| Classifier | Accuracy | Notes |
|---|---|---|
| keyword | 94.5% | n=200 |
| tfidf | 59.0% | n=200 |
| llm | 94.5% | n=200 |

### Per-Intent Accuracy (Main LLM Classifier)

| Intent | Accuracy |
|---|---|
| account_access_issue | 80.0% |
| app_technical_bug | 100.0% |
| cancellation_fee_dispute | 100.0% |
| driver_behavior_complaint | 92.9% |
| driver_unsafe_incident | 97.8% |
| fare_overcharge_dispute | 100.0% |
| general_inquiry | 92.5% |
| lost_item | 100.0% |
| promo_code_failed | 100.0% |
| receipt_request | 83.3% |

## Stage 3 — Escalation

| Strategy | Precision | Recall | F1 | Safety Recall |
|---|---|---|---|---|
| always_escalate | 25.5% | 100.0% | 40.6% | 100.0% |
| never_escalate | 0.0% | 0.0% | 0.0% | 0.0% |
| **main pipeline** | 26.2% | 98.0% | 41.3% | 100.0% |
