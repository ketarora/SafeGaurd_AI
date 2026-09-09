#!/usr/bin/env python3
"""Run full evaluation harness: baselines + main pipeline + escalation metrics."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.classify import evaluate_classifier
from src.config import EVAL_DIR, OUTPUT_DIR
from src.escalate import EscalationDecider, evaluate_escalation_baseline
from src.pipeline import SupportAgentPipeline
from src.utils import save_json, setup_logging


def compute_escalation_metrics(outputs: list, golden: pd.DataFrame) -> dict:
    """Compare pipeline escalation decisions against golden labels."""
    tp = fp = tn = fn = 0
    safety_tp = safety_fn = 0
    safety_total = 0
    mismatches = []

    golden_map = {str(r["tweet_id"]): r for _, r in golden.iterrows()}

    for out in outputs:
        d = out.to_dict() if hasattr(out, "to_dict") else out
        tid = str(d["tweet_id"])
        if tid not in golden_map:
            continue
        true = golden_map[tid]["true_escalation_decision"]
        pred = d["escalation"]["decision"]
        intent = golden_map[tid]["true_intent"]

        if intent == "driver_unsafe_incident":
            safety_total += 1
            if pred == "escalate":
                safety_tp += 1
            else:
                safety_fn += 1
                mismatches.append({"tweet_id": tid, "text": d["text"][:80], "pred": pred})

        if true == "escalate":
            if pred == "escalate":
                tp += 1
            else:
                fn += 1
        else:
            if pred == "auto_handle":
                tn += 1
            else:
                fp += 1

    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall) if (precision + recall) else 0, 4),
        "driver_unsafe_incident_recall": round(safety_tp / safety_total if safety_total else 1.0, 4),
        "driver_unsafe_incident_total": safety_total,
        "driver_unsafe_incident_misses": mismatches,
        "false_auto_handles_on_escalate_cases": fn,
    }


def main() -> None:
    setup_logging()
    golden_path = EVAL_DIR / "golden_set.csv"
    if not golden_path.exists():
        print(f"Golden set not found: {golden_path}")
        sys.exit(1)

    golden = pd.read_csv(golden_path)
    examples = golden.to_dict("records")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("STAGE 1: Intent Classification — Baselines vs Main")
    print("=" * 60)

    results = {}
    for name in ["keyword", "tfidf", "llm"]:
        print(f"\nEvaluating {name} classifier...")
        r = evaluate_classifier(name, examples, tfidf_train=examples)
        results[name] = {k: v for k, v in r.items() if k != "predictions"}
        print(f"  Accuracy: {r['accuracy']:.1%} (n={r['n']})")
        if name == "llm":
            per = r["per_intent_accuracy"]
            rare = per.get("driver_unsafe_incident")
            if rare is not None:
                print(f"  driver_unsafe_incident accuracy: {rare:.1%}")

    print("\n" + "=" * 60)
    print("STAGE 3: Escalation — Baselines vs Main Pipeline")
    print("=" * 60)

    esc_baselines = {}
    for strategy in ["always_escalate", "never_escalate"]:
        esc_baselines[strategy] = evaluate_escalation_baseline(examples, strategy)
        print(f"\n  {strategy}: recall={esc_baselines[strategy]['recall']:.1%}, "
              f"precision={esc_baselines[strategy]['precision']:.1%}")

    print("\nRunning main pipeline on golden set...")
    pipeline = SupportAgentPipeline(classifier_name="llm")
    outputs = pipeline.process_batch(examples, log_path=OUTPUT_DIR / "eval_pipeline_log.jsonl")

    esc_metrics = compute_escalation_metrics(outputs, golden)
    print(f"\n  Main pipeline escalation recall: {esc_metrics['recall']:.1%}")
    print(f"  Main pipeline escalation precision: {esc_metrics['precision']:.1%}")
    print(f"  driver_unsafe_incident recall: {esc_metrics['driver_unsafe_incident_recall']:.1%} "
          f"({esc_metrics['driver_unsafe_incident_total']} cases)")

    if esc_metrics["driver_unsafe_incident_misses"]:
        print("  ⚠ CRITICAL: Safety incident auto-handled:")
        for m in esc_metrics["driver_unsafe_incident_misses"]:
            print(f"    - {m['text']}")

    # Save all metrics
    full_results = {
        "classification": results,
        "escalation_baselines": esc_baselines,
        "escalation_main": esc_metrics,
        "n_golden": len(golden),
    }
    save_json(OUTPUT_DIR / "eval_results.json", full_results)

    # Write markdown summary
    md_path = EVAL_DIR / "baselines_comparison.md"
    with md_path.open("w", encoding="utf-8") as f:
        f.write("# Baselines Comparison\n\n")
        f.write("## Stage 1 — Intent Classification\n\n")
        f.write("| Classifier | Accuracy | Notes |\n|---|---|---|\n")
        for name, r in results.items():
            f.write(f"| {name} | {r['accuracy']:.1%} | n={r['n']} |\n")

        f.write("\n### Per-Intent Accuracy (Main LLM Classifier)\n\n")
        f.write("| Intent | Accuracy |\n|---|---|\n")
        for intent, acc in sorted(results.get("llm", {}).get("per_intent_accuracy", {}).items()):
            if acc is not None:
                f.write(f"| {intent} | {acc:.1%} |\n")

        f.write("\n## Stage 3 — Escalation\n\n")
        f.write("| Strategy | Precision | Recall | F1 | Safety Recall |\n")
        f.write("|---|---|---|---|---|\n")
        for name, r in esc_baselines.items():
            f.write(f"| {name} | {r['precision']:.1%} | {r['recall']:.1%} | {r['f1']:.1%} | {r['driver_unsafe_recall']:.1%} |\n")
        f.write(f"| **main pipeline** | {esc_metrics['precision']:.1%} | {esc_metrics['recall']:.1%} | "
                f"{esc_metrics['f1']:.1%} | {esc_metrics['driver_unsafe_incident_recall']:.1%} |\n")

    print(f"\nResults saved to {OUTPUT_DIR / 'eval_results.json'}")
    print(f"Summary written to {md_path}")


if __name__ == "__main__":
    main()
