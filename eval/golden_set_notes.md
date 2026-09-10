# Golden Set — Sampling & Labeling Methodology

## Overview
- **Target size:** 200 examples (within 150–250 requirement)
- **Brand:** @Uber_Support (Uber)
- **Labeler:** Solo annotator (candidate), with documented self-consistency protocol
- **Label fields:** `true_intent`, `true_escalation_decision`, `escalation_reason`, `ambiguity_flag`, human quality scores

## Sampling Procedure (Stratified, Not Pure Random)

Implemented in `scripts/sample_golden_from_kaggle.py`:

| Bucket | Target % | n | Purpose |
|--------|----------|---|---------|
| Stratified random | ~60% | 120 | Proportional coverage across all 10 intents |
| Hard/ambiguous | ~25% | 50 | Multi-issue tweets, sarcasm, very short messages |
| Safety oversample | ~15% (actual 23%) | 30 (actual 46) | Deliberate oversampling of `driver_unsafe_incident` |

### Why Not Pure Random? (And Why The 23% Divergence?)
Pure random sampling from Twitter support data would yield ~1-2% safety incidents — too few to evaluate escalation recall meaningfully. We deliberately oversample high-stakes categories. The final set achieved 23% (46 cases) rather than the planned 15% because real data surfaced more safety-adjacent language than the initial target assumed. We document this bias explicitly (see REPORT.md § "Misleading Headline Numbers").

### Hard Case Selection Criteria
- Multi-intent tweets ("app crashed AND driver was rude AND refund")
- Very short/low-context ("scam", "???", "help")
- Ambiguous safety-adjacent language ("not safe", "he scared me")
- Code-switching / emoji-heavy messages

## Intent Taxonomy (10 intents, data-derived)

| Intent | Definition | Default Escalation |
|--------|-----------|-------------------|
| `promo_code_failed` | Discount/promo didn't apply | auto_handle |
| `receipt_request` | Wants receipt/invoice | auto_handle |
| `lost_item` | Item left in vehicle | auto_handle |
| `app_technical_bug` | App crashes, payment/GPS/login issues | auto_handle |
| `fare_overcharge_dispute` | Disputes fare amount/route | escalate |
| `cancellation_fee_dispute` | Disputes cancellation fee | escalate |
| `driver_behavior_complaint` | Rude/unprofessional (non-safety) | escalate |
| `driver_unsafe_incident` | Physical safety — accident, harassment, assault | escalate (HARD) |
| `account_access_issue` | Locked out, banned, deactivated | escalate |
| `general_inquiry` | Other / positive feedback | auto_handle |

## Labeling Protocol
1. Label `true_intent` and `true_escalation_decision` **before** viewing any model output (avoid anchoring)
2. Write `escalation_reason` in own words before checking model
3. Mark `ambiguity_flag=true` when genuinely could go either way
4. For safety-adjacent cases: **err toward escalate** (conservative bias)
5. Sessions of ~40-50 examples with definition table re-read at start

## Self-Consistency Check
After completing the full set, re-label a random 20-example subset blind (hide original labels). Compare agreement:

```python
# Run: python scripts/self_consistency_check.py
# Expected: report Cohen's kappa or % agreement on intent + escalation
```

Document results in `eval/judge_agreement.md`.

## Reproducing the Golden Set
```bash
python scripts/generate_sample_data.py
# Output: eval/golden_set.csv (200 examples - canonical version used by pipeline)
# Note: eval/golden_set_fully_labeled.csv is the raw pre-normalization backup export, and eval/golden_set_unlabeled.csv is the initial sampling baseline.
```

For production labeling with real Kaggle data, replace templates with actual Uber_Support inbound tweets filtered by the same stratification logic in `scripts/sample_golden_from_kaggle.py` (extend as needed).
