#!/usr/bin/env python3
"""
Validate a completed golden set CSV for consistency and completeness.

Run this AFTER the human has filled in labels in golden_set_unlabeled.csv
and saved it as golden_set.csv.

Usage:
  python scripts/validate_golden_set.py
  python scripts/validate_golden_set.py --input eval/golden_set.csv
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import INTENTS

REQUIRED_COLUMNS = [
    "tweet_id", "text", "true_intent", "true_escalation_decision",
    "escalation_reason", "ambiguity_flag",
]

VALID_ESCALATION = {"yes", "no", "escalate", "auto_handle"}
VALID_AMBIGUITY = {"yes", "", "true", "false", "nan"}


def validate(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Returns (errors, warnings)."""
    errors = []
    warnings = []

    # --- Column checks ---
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            errors.append(f"Missing required column: '{col}'")

    if errors:
        return errors, warnings  # can't continue without columns

    n = len(df)

    # --- Blank label checks ---
    blank_intent = df["true_intent"].isna() | (df["true_intent"].astype(str).str.strip() == "")
    if blank_intent.any():
        blank_ids = df[blank_intent]["tweet_id"].tolist()
        errors.append(
            f"{blank_intent.sum()} rows have BLANK true_intent: {blank_ids[:5]}..."
        )

    blank_esc = df["true_escalation_decision"].isna() | (
        df["true_escalation_decision"].astype(str).str.strip() == ""
    )
    if blank_esc.any():
        blank_ids = df[blank_esc]["tweet_id"].tolist()
        errors.append(
            f"{blank_esc.sum()} rows have BLANK true_escalation_decision: {blank_ids[:5]}..."
        )

    blank_reason = df["escalation_reason"].isna() | (
        df["escalation_reason"].astype(str).str.strip() == ""
    )
    if blank_reason.any():
        warnings.append(
            f"{blank_reason.sum()} rows have BLANK escalation_reason (strongly recommended to fill)"
        )

    # --- Intent validity ---
    filled = df[~blank_intent].copy()
    intents_used = set(filled["true_intent"].astype(str).str.strip().unique())
    unknown = intents_used - set(INTENTS)
    if unknown:
        errors.append(
            f"Unknown intents found (not in config.INTENTS): {unknown}. "
            f"If intentional, update src/config.py INTENTS list."
        )

    intent_counts = Counter(filled["true_intent"].astype(str).str.strip())
    missing_intents = set(INTENTS) - intents_used
    if missing_intents:
        warnings.append(
            f"These intents have 0 examples in the golden set: {missing_intents}. "
            f"Per-intent accuracy won't be computed for them."
        )

    # --- Escalation validity ---
    filled_esc = df[~blank_esc].copy()
    esc_values = set(filled_esc["true_escalation_decision"].astype(str).str.strip().str.lower().unique())
    invalid_esc = esc_values - VALID_ESCALATION
    if invalid_esc:
        errors.append(
            f"Invalid escalation values: {invalid_esc}. Must be exactly 'Yes' or 'No'."
        )

    # --- Safety-specific checks ---
    safety_rows = filled[filled["true_intent"].astype(str).str.strip() == "driver_unsafe_incident"]
    n_safety = len(safety_rows)
    if n_safety < 10:
        warnings.append(
            f"Only {n_safety} driver_unsafe_incident examples. "
            f"Need enough for meaningful escalation recall measurement (recommend 15-30+)."
        )
    
    safety_not_escalated = safety_rows[
        ~safety_rows["true_escalation_decision"].astype(str).str.strip().str.lower().isin(["yes", "escalate"])
    ]
    if len(safety_not_escalated) > 0:
        warnings.append(
            f"{len(safety_not_escalated)} driver_unsafe_incident rows labeled as auto_handle/No — "
            f"these should almost always be escalate per the labeling guide. Review: "
            f"{safety_not_escalated['tweet_id'].tolist()}"
        )

    # --- Ambiguity flag ---
    df["ambiguity_flag"] = df["ambiguity_flag"].fillna("")
    ambig = df["ambiguity_flag"].astype(str).str.strip().str.lower()
    ambig = ambig.apply(lambda x: "" if x == "nan" else x)
    
    invalid_ambig = set(ambig.unique()) - VALID_AMBIGUITY
    if invalid_ambig:
        errors.append(f"Invalid ambiguity values: {invalid_ambig}. Must be 'Yes' or blank.")

    ambig_count = (ambig == "yes").sum() + (ambig == "true").sum()
    if ambig_count == 0:
        warnings.append(
            "No rows flagged as ambiguous. Consider marking genuinely borderline cases."
        )
    elif ambig_count > n * 0.5:
        warnings.append(
            f"{ambig_count}/{n} rows flagged ambiguous — that's unusually high. "
            f"Ambiguity flag is for genuinely borderline cases."
        )

    # --- Duplicate tweet_ids ---
    dupes = df["tweet_id"].duplicated()
    if dupes.any():
        errors.append(f"{dupes.sum()} duplicate tweet_ids found.")

    return errors, warnings


def print_summary(df: pd.DataFrame) -> None:
    """Print golden set summary statistics."""
    n = len(df)
    print(f"\n{'=' * 50}")
    print(f"GOLDEN SET SUMMARY — {n} examples")
    print(f"{'=' * 50}")

    # Intent distribution
    print("\nIntent distribution:")
    intent_counts = df["true_intent"].astype(str).str.strip().value_counts()
    for intent, count in intent_counts.items():
        pct = count / n * 100
        bar = "█" * int(pct)
        print(f"  {intent:<30} {count:>3} ({pct:5.1f}%) {bar}")

    # Escalation split
    esc_counts = df["true_escalation_decision"].astype(str).str.strip().str.lower().value_counts()
    print(f"\nEscalation split:")
    for dec, count in esc_counts.items():
        print(f"  {dec}: {count} ({count/n*100:.1f}%)")

    # Ambiguity
    ambig = df["ambiguity_flag"].astype(str).str.strip().str.lower()
    print(f"\nAmbiguity flags: {((ambig == 'yes') | (ambig == 'true')).sum()}/{n}")

    # Sampling tiers (from notes column)
    if "notes" in df.columns:
        notes = df["notes"].astype(str)
        print(f"\nSampling tiers:")
        for tier in ["safety_adjacent", "hard_case", "stratified_random", "fill"]:
            count = notes.str.contains(tier, case=False).sum()
            if count > 0:
                print(f"  {tier}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate golden set labels")
    parser.add_argument(
        "--input", type=str,
        default=str(ROOT / "eval" / "golden_set.csv"),
    )
    args = parser.parse_args()

    path = Path(args.input)
    if not path.exists():
        print(f"File not found: {path}")
        print(f"Have you completed labeling? Expected at: eval/golden_set.csv")
        sys.exit(1)

    df = pd.read_csv(path, dtype=str)
    errors, warnings = validate(df)

    if errors:
        print(f"\n❌ ERRORS ({len(errors)}) — must fix before proceeding:")
        for e in errors:
            print(f"  • {e}")

    if warnings:
        print(f"\n⚠ WARNINGS ({len(warnings)}) — review and address if possible:")
        for w in warnings:
            print(f"  • {w}")

    if not errors:
        # Map labels to eval harness format and save
        mapping_esc = {"yes": "escalate", "no": "auto_handle"}
        esc_series = df["true_escalation_decision"].astype(str).str.strip().str.lower()
        df["true_escalation_decision"] = esc_series.map(mapping_esc).fillna(df["true_escalation_decision"])
        
        mapping_ambig = {"yes": "true", "nan": ""}
        ambig_series = df["ambiguity_flag"].astype(str).str.strip().str.lower()
        df["ambiguity_flag"] = ambig_series.map(mapping_ambig).fillna(df["ambiguity_flag"])
        
        df.to_csv(path, index=False)

        print_summary(df)
        if not warnings:
            print(f"\n✅ Golden set looks good. Mapped Yes/No -> escalate/auto_handle and saved to {path}. Ready for pipeline evaluation.")
        else:
            print(f"\n⚠ Golden set has warnings but no blocking errors. Mapped and saved to {path}.")
    else:
        print(f"\n❌ Fix errors before running evaluation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
