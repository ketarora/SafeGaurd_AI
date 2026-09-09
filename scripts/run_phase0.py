#!/usr/bin/env python3
"""
Phase 0 Orchestration — Real Data Pipeline.

Run this to execute all steps that can be automated.
Steps that require human action are printed as instructions.

Usage:
  python scripts/run_phase0.py
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
py = sys.executable


def run(cmd: list[str], desc: str, can_fail: bool = False) -> int:
    print(f"\n{'=' * 60}")
    print(f"  {desc}")
    print(f"{'=' * 60}")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.time() - t0
    status = "✓" if result.returncode == 0 else "✗"
    print(f"  {status} Completed in {elapsed:.1f}s (exit={result.returncode})")
    if result.returncode != 0 and not can_fail:
        print(f"  FAILED — stopping here. Fix the issue and rerun.")
        sys.exit(result.returncode)
    return result.returncode


def check_file(path: Path, desc: str) -> bool:
    exists = path.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {desc}: {path}")
    return exists


def main() -> None:
    print("=" * 60)
    print("  PHASE 0 — REAL DATA PIPELINE")
    print("=" * 60)

    # Step 1: Check for raw Kaggle data
    twcs = ROOT / "data" / "raw" / "twcs.csv"
    print("\n[Step 1] Checking for Kaggle data...")
    if not check_file(twcs, "twcs.csv"):
        print(f"\n  ⚠ BLOCKED: Download twcs.csv from Kaggle:")
        print(f"    https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter")
        print(f"    Place at: {twcs}")
        print(f"    Then rerun this script.")
        sys.exit(1)

    # Step 2: Prepare processed data from Kaggle
    processed = ROOT / "data" / "processed" / "uber_threads.csv"
    print("\n[Step 2] Preparing processed data from Kaggle...")
    if not processed.exists():
        run([py, "scripts/prepare_data.py", "--kaggle", str(twcs)],
            "Extract Uber_Support threads from Kaggle data")
    else:
        print(f"  ✓ Already processed: {processed}")

    # Step 3: Explore data (validate taxonomy)
    print("\n[Step 3] Exploring data for taxonomy validation...")
    run([py, "scripts/explore_data.py"], "Data exploration & taxonomy validation")

    # Step 4: Generate blank-labels golden set
    unlabeled = ROOT / "eval" / "golden_set_unlabeled.csv"
    labeled = ROOT / "eval" / "golden_set.csv"

    if not labeled.exists():
        print("\n[Step 4] Generating blank-labels golden set...")
        run([py, "scripts/sample_golden_from_kaggle.py",
             "--n", "200", "--output", str(unlabeled)],
            "Sample 200 real tweets for golden set labeling")

        print(f"\n{'=' * 60}")
        print(f"  ⚠ HUMAN ACTION REQUIRED")
        print(f"{'=' * 60}")
        print(f"  1. Open: {unlabeled}")
        print(f"  2. Fill in labels for each row:")
        print(f"     - true_intent (from taxonomy)")
        print(f"     - true_escalation_decision (auto_handle | escalate)")
        print(f"     - escalation_reason (one sentence)")
        print(f"     - ambiguity_flag (TRUE/FALSE)")
        print(f"  3. Save as: {labeled}")
        print(f"  4. Rerun this script to continue.")
        sys.exit(0)

    # Step 5: Validate golden set labels
    print("\n[Step 5] Validating golden set labels...")
    rc = run([py, "scripts/validate_golden_set.py", "--input", str(labeled)],
             "Validate golden set consistency", can_fail=True)
    if rc != 0:
        print(f"\n  ⚠ Fix validation errors in {labeled} and rerun.")
        sys.exit(1)

    # Step 6: Run full evaluation pipeline
    print("\n[Step 6] Running full evaluation pipeline...")
    run([py, "scripts/run_eval.py"], "Evaluation: baselines + main pipeline + escalation")

    # Step 7: Run LLM judge
    log = ROOT / "outputs" / "eval_pipeline_log.jsonl"
    if log.exists():
        print("\n[Step 7] Running LLM-as-judge...")
        run([py, "eval/llm_judge.py"], "LLM-as-judge scoring")
    else:
        print("\n[Step 7] Skipping LLM judge (no pipeline log found)")

    # Step 8: Self-consistency check
    print("\n[Step 8] Running self-consistency check...")
    run([py, "scripts/self_consistency_check.py"],
        "Self-consistency (proxy) check", can_fail=True)

    print(f"\n{'=' * 60}")
    print(f"  PHASE 0 COMPLETE")
    print(f"{'=' * 60}")
    print(f"\n  Real results in: outputs/eval_results.json")
    print(f"  Judge scores:    outputs/judge_scores.csv")
    print(f"\n  TODO (manual):")
    print(f"  1. Review outputs/eval_results.json — update README.md numbers")
    print(f"  2. Review outputs/judge_scores.csv — update judge_agreement.md")
    print(f"  3. Review outputs/eval_pipeline_log.jsonl — update failure_analysis.md")
    print(f"  4. Update REPORT.md with real numbers")
    print(f"  5. Update decision_log.md with taxonomy/data decisions")


if __name__ == "__main__":
    main()
