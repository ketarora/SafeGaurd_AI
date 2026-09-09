#!/usr/bin/env python3
"""
One-command reproduction script — headline results in under 15 minutes.

Steps:
  1. Generate sample data (if missing)
  2. Prepare processed data
  3. Run evaluation harness
  4. Run LLM judge (heuristic if no API key)
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list[str], desc: str) -> None:
    print(f"\n{'='*60}\n{desc}\n{'='*60}")
    t0 = time.time()
    result = subprocess.run(cmd, cwd=ROOT)
    elapsed = time.time() - t0
    print(f"Completed in {elapsed:.1f}s (exit={result.returncode})")
    if result.returncode != 0:
        sys.exit(result.returncode)


def main() -> None:
    py = sys.executable
    t_start = time.time()

    if not (ROOT / "data" / "sample" / "precedents.json").exists():
        run([py, "scripts/generate_sample_data.py"], "Step 0: Generate sample data + golden set")

    run([py, "scripts/prepare_data.py"], "Step 1: Prepare processed data")
    run([py, "scripts/run_eval.py"], "Step 2: Run evaluation harness")

    log = ROOT / "outputs" / "eval_pipeline_log.jsonl"
    if log.exists():
        run([py, "eval/llm_judge.py"], "Step 3: Run LLM-as-judge")

    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"ALL DONE in {total/60:.1f} minutes")
    print(f"Results: outputs/eval_results.json")
    print(f"Report:  report/REPORT.md")
    print(f"Demo:    python demo/cli.py \"I was overcharged for my ride\"")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
