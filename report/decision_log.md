# Decision Log — 15 Non-Obvious Choices

1. **Brand = Uber (@Uber_Support)** — Highest volume in Kaggle dataset, richest multi-turn threads, and safety/fare dispute mix makes escalation evaluation meaningful (not just FAQ bot).

2. **10-intent taxonomy with separate `driver_unsafe_incident`** — Did not merge into `driver_behavior_complaint` despite expected low volume; liability narrative requires distinct handling and hard escalation rule.

3. **Bundled sample data for <15 min repro** — Full twcs.csv is 300MB+; graders won't run 3M rows. Bundled sample + optional Kaggle path balances reproducibility vs realism.

4. **Embedding model: `all-MiniLM-L6-v2`** — Local, free, fast (~80MB), good enough for short noisy tweets at subsample scale. Chose over OpenAI embeddings to avoid API dependency for retrieval-only runs.

5. **Resolution proxy: inbound → outbound pair** — Simpler than "no further complaint within 24h" which requires thread graph traversal. Noisy but sufficient for precedent retrieval at this scale; documented as limitation.

6. **Hard-coded safety escalation BEFORE any LLM reasoning** — `driver_unsafe_incident` and safety keywords trigger deterministic escalate in Python, not prompt. Prevents LLM from overriding safety decisions.

7. **Default escalate for all financial/account intents** — Unless confidence ≥ 0.85 AND grounding = strong. Conservative bias: false escalation costs agent time; false auto-handle costs customer trust and money.

8. **LLM classifier with keyword fallback** — Demo mode (no API key) still runs end-to-end using keyword classifier + template replies. Graders can evaluate architecture without API costs.

9. **Same model for generation and judging (gpt-4o-mini)** — Cost/simplicity tradeoff for take-home timeline. Documented same-model bias risk; noted Claude-as-judge as one-week improvement.

10. **Golden set stratification: 60/25/15 target (actual 23% safety)** — Not pure random. 25% hard cases + 23% safety oversample makes eval meaningful for high-stakes categories. Explicitly flagged as biasing headline recall upward.

11. **TF-IDF + LR over zero-shot embeddings for Baseline B** — Simpler, interpretable, trains in seconds on 200 examples. Evaluated using honest 5-fold cross-validation to prevent train/test leakage. Zero-shot would be stronger but harder to explain.

12. **280-char reply limit in prompt** — Matches Twitter reply constraint for this channel; noted when DM would be more appropriate.

13. **Structured JSON output with schema validation** — Pipeline fails loudly on malformed LLM output rather than silently degrading. Needed for reliable eval harness composition.

14. **Separate escalation evaluation from classification accuracy** — A perfectly classified fare dispute that gets auto-handled is a worse failure than a misclassified one that gets escalated. Stage 3 has its own metrics and baselines.

15. **Heuristic LLM-judge for demo mode** — Rule-based scoring on grounding quality + escalation match when no API key. Allows full eval pipeline to run offline; scores are clearly labeled as heuristic, not headline numbers.
 
16. **Retrieval Implementation** — Used standard Pandas cosine similarity in-memory using exact embeddings rather than Faiss or VectorDB. Since the search space (thousands of tweets) allows fast deterministic calculation, this avoids external infrastructure bloat.
 
17. **Agreement Metrics (Cohen's Kappa vs simple agreement)** — Relied on simple percentage-based ±1 threshold and binary match rather than Cohen's Kappa. With exactly 1 human annotator on a heavily imbalanced 200 example set, Kappa would artificially punish the score for class imbalances rather than convey true human-LLM reliability.
