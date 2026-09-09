#!/usr/bin/env python3
"""Self-consistency check for golden set labeling (solo annotator protocol)."""

from __future__ import annotations

import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.classify import KeywordClassifier


def simulate_blind_relabel(examples: list[dict], n: int = 20) -> dict:
    """
    Simulate self-consistency by re-classifying with keyword classifier
    as a proxy for annotator drift measurement on a held-out check.

    For real submission: manually re-label 20 examples blind and compare.
    """
    random.seed(123)
    sample = random.sample(examples, min(n, len(examples)))

    intent_match = 0
    esc_match = 0

    for ex in sample:
        # In real protocol: human re-labels blind
        # Here we use keyword classifier as drift proxy
        kw = KeywordClassifier().classify(ex["text"])
        if kw.intent == ex["true_intent"]:
            intent_match += 1

        from src.config import DEFAULT_ESCALATION
        from src.escalate import EscalationDecider
        decider = EscalationDecider()
        result = decider.decide(
            text=ex["text"],
            intent=ex["true_intent"],
            intent_confidence=0.8,
            draft_reply="",
            grounding_quality="weak",
        )
        if result.decision == ex["true_escalation_decision"]:
            esc_match += 1

    n = len(sample)
    return {
        "n_sample": n,
        "intent_agreement_pct": round(intent_match / n * 100, 1),
        "escalation_agreement_pct": round(esc_match / n * 100, 1),
        "note": "Replace with actual blind human re-labeling for submission",
    }


if __name__ == "__main__":
    golden = pd.read_csv(ROOT / "eval" / "golden_set.csv")
    result = simulate_blind_relabel(golden.to_dict("records"))
    print("Self-consistency check (proxy):")
    for k, v in result.items():
        print(f"  {k}: {v}")
