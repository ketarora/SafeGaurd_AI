# Failure Analysis — Top 5 Failure Modes

Each mode includes a real example from the golden set evaluation, hypothesis for cause, and severity.

---

## 1. Multi-Intent Tweet → Single Intent Misclassification

**Example:**
> "There r 2 cases. yesterday driver cancelled his trip as he refused to pick me up from my Location. But u have debited my account of Rs 43.2nd one, today driver behaved unprofessionally..." (tweet_id: 587498)
> - True intent: `driver_behavior_complaint` OR `cancellation_fee_dispute`
> - Predicted: `general_inquiry` (keyword clash causes ambiguity fallback)
> - Impact: Wrong precedent retrieved → weak grounding → unnecessary escalation OR wrong reply template

**Hypothesis:** Single-label classification forces a choice on multi-issue tweets. Keyword baseline especially vulnerable to salient emotional words ("rude") over primary ask ("refund").

**Severity:** Medium — escalation often saves us (conservative routing), but reply quality suffers.

**Fix:** Multi-label classification or priority rules (financial > behavioral > technical when multiple detected).

---

## 2. Short/Ambiguous Messages → `general_inquiry` Default

**Example:**
> "is it some scam or what,my last ride issue of over charging is pending and yet again,I am being charged 4times more thn the rate booked on..." (tweet_id: 584146)
> - True intent: `promo_code_failed` (in dataset) or `fare_overcharge_dispute`
> - Predicted: `general_inquiry` (confidence 0.35)
> - Escalation: Correctly escalated due to low confidence, but reply is useless generic template

**Hypothesis:** Very short messages lack features for any classifier. LLM defaults to general_inquiry; keyword finds no match.

**Severity:** Medium — escalation catches it, but customer gets non-actionable reply before human takeover.

**Fix:** Short-message handling: always escalate + ask clarifying question rather than draft a substantive reply.

---

## 3. Safety-Adjacent Language Missed by Classifier (Non-Keyword Path)

**Example:**
> "TW: car accident. Green car, Oregon plates 973 HCJ with an @115873 sticker in the window barely missed hitting me in the crosswalk at W Burnside and NW Park..." (tweet_id: 515368)
> - True intent: `driver_unsafe_incident`
> - Predicted: `driver_behavior_complaint` (LLM, confidence 0.55)
> - Escalation: **Saved by safety keyword flag** ("not safe" → `unsafe` substring match)

**Hypothesis:** Without the hard-coded safety keyword layer, this would be misclassified AND potentially auto-handled. The deterministic guardrail is doing real work.

**Severity:** Critical if guardrail fails; Low with guardrail (this case shows guardrail working).

**Fix:** Expand safety keyword list; never auto-handle below 0.7 confidence when ANY negative sentiment present.

---

## 4. Weak Retrieval → Overconfident Template Reply

**Example:**
> "Upfront price was $18, final charge was $34. Why?"
> - Intent: Correctly classified as `fare_overcharge_dispute`
> - Best precedent similarity: 0.48 (below weak threshold)
> - Grounding: "none" — but demo template still drafts a reply
> - Escalation: Correctly escalated (default for fare disputes)

**Hypothesis:** Stage 2 drafts a reply even when grounding is absent; Stage 3 catches it for high-stakes intents, but for low-stakes intents with weak grounding, we might auto-handle with a generic reply.

**Severity:** Low-Medium — escalation saves high-stakes cases; low-stakes generic replies are mediocre but not harmful.

**Fix:** Skip substantive drafting when similarity < 0.55; output "escalating to specialist" instead.

---

## 5. LLM Judge Inflates Tone Scores for Boilerplate Replies

**Example:**
> Customer: "Charged twice for the same trip!!!"
> Draft: "Thank you for reaching out! We understand your frustration."
> Judge TONE: 4 | Human TONE: 2
> Headline metric: "Average tone score 4.1/5" — misleading

**Hypothesis:** LLM judge rewards politeness markers without evaluating whether the reply actually addresses the issue. Same-model bias amplifies this.

**Severity:** High for **evaluation integrity** (not customer safety). This is the primary "misleading headline number" for reply quality.

**Fix:** Use different model family for judging; add automated boilerplate detector that penalizes scores; weight CORRECTNESS and ACTIONABILITY higher than TONE in composite metric.

---

## Summary Table

| # | Failure Mode | Safety Impact | Eval Impact | Mitigation Status |
|---|-------------|---------------|-------------|-------------------|
| 1 | Multi-intent misclassification | Low (escalation saves) | Medium | Partial |
| 2 | Short message ambiguity | Low | Medium | Partial |
| 3 | Safety-adjacent miss | **Critical** without guardrail | Low | **Guardrail works** |
| 4 | Weak retrieval + generic reply | Medium | Low | Partial |
| 5 | Judge score inflation | None | **High** | Documented, not fixed |
