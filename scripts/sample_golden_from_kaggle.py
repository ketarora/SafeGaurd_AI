#!/usr/bin/env python3
"""
Sample real Uber_Support tweets for golden set labeling.

Outputs a BLANK-LABELS CSV for the human to label by hand.
Does NOT auto-assign intents or escalation decisions — that's the point.

Usage:
  python scripts/sample_golden_from_kaggle.py
  python scripts/sample_golden_from_kaggle.py --n 200 --output eval/golden_set_unlabeled.csv

Sampling strategy (from golden_set_notes.md):
  ~60% stratified random across rough intent buckets
  ~25% deliberately hard/ambiguous (short, multi-issue, angry)
  ~15% safety-adjacent (keyword-flagged, for oversampling)
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import (
    KEYWORD_RULES,
    PROCESSED_DIR,
    SAFETY_KEYWORDS,
    UBER_SUPPORT_HANDLE,
)

random.seed(42)


def load_uber_inbound(processed_dir: Path) -> pd.DataFrame:
    """Load inbound customer tweets from processed Uber threads."""
    threads_path = processed_dir / "uber_threads.csv"
    if not threads_path.exists():
        raise FileNotFoundError(
            f"No processed data at {threads_path}. "
            "Run: python scripts/prepare_data.py --kaggle data/raw/twcs.csv"
        )
    df = pd.read_csv(threads_path, dtype=str)
    df["inbound"] = df["inbound"].map({"True": True, "False": False, "true": True, "false": False})
    
    # Only inbound tweets (customers, not brand replies)
    inbound = df[df["inbound"] == True].copy()
    inbound = inbound.dropna(subset=["text"])
    inbound = inbound[inbound["text"].str.strip().str.len() > 0]
    
    print(f"Total inbound tweets: {len(inbound)}")
    return inbound


def build_thread_context(tweet_id: str, df: pd.DataFrame, max_turns: int = 3) -> str:
    """Reconstruct prior turns in the conversation thread."""
    context_parts = []
    current_id = tweet_id
    
    for _ in range(max_turns):
        row = df[df["tweet_id"] == current_id]
        if row.empty:
            break
        parent_id = row.iloc[0].get("in_response_to_tweet_id")
        if pd.isna(parent_id) or not parent_id:
            break
        
        parent = df[df["tweet_id"] == parent_id]
        if parent.empty:
            break
        
        parent_text = str(parent.iloc[0]["text"])
        parent_author = str(parent.iloc[0]["author_id"])
        is_brand = parent_author == UBER_SUPPORT_HANDLE
        prefix = "[Uber_Support]" if is_brand else "[Customer]"
        context_parts.insert(0, f"{prefix}: {parent_text}")
        current_id = parent_id
    
    return "\n".join(context_parts) if context_parts else ""


def rough_intent_bucket(text: str) -> str:
    """
    Rough heuristic bucketing for stratified sampling ONLY.
    This is NOT the label — it's just to ensure sampling diversity.
    The human assigns the real label.
    """
    lower = text.lower()
    
    # Check safety first (highest priority)
    if any(kw in lower for kw in SAFETY_KEYWORDS):
        return "safety_adjacent"
    
    # Check each intent's keywords
    for intent, keywords in KEYWORD_RULES.items():
        if intent == "driver_unsafe_incident":
            continue  # already checked via SAFETY_KEYWORDS
        if any(kw in lower for kw in keywords):
            return intent
    
    return "unmatched"


def is_hard_case(text: str) -> bool:
    """Heuristic for hard/ambiguous cases worth human attention."""
    lower = text.lower()
    
    # Very short (low context)
    if len(text.strip()) < 30:
        return True
    
    # Multi-issue signals (multiple keyword buckets match)
    buckets_hit = 0
    for intent, keywords in KEYWORD_RULES.items():
        if any(kw in lower for kw in keywords):
            buckets_hit += 1
    if buckets_hit >= 2:
        return True
    
    # Strong negative sentiment (escalation boundary cases)
    angry_markers = [
        "!!!", "wtf", "fuck", "scam", "fraud", "worst", "never again",
        "lawyer", "sue", "ridiculous", "unacceptable",
    ]
    if sum(1 for m in angry_markers if m in lower) >= 2:
        return True
    
    # Sarcasm/irony signals
    if "thanks a lot" in lower or "great job" in lower or "love how" in lower:
        return True
    
    # Questions without clear intent
    if text.strip().endswith("?") and len(text.strip()) < 60:
        return True
    
    return False


def sample_golden_set(
    inbound: pd.DataFrame,
    full_df: pd.DataFrame,
    n_target: int = 200,
) -> list[dict]:
    """
    Stratified sampling for golden set.
    Returns rows with BLANK label fields for human annotation.
    """
    # Step 1: Assign rough buckets for sampling diversity
    inbound = inbound.copy()
    inbound["_rough_bucket"] = inbound["text"].apply(rough_intent_bucket)
    inbound["_is_hard"] = inbound["text"].apply(is_hard_case)
    inbound["_is_safety"] = inbound["_rough_bucket"] == "safety_adjacent"
    
    bucket_counts = inbound["_rough_bucket"].value_counts()
    print(f"\nRough bucket distribution (for sampling, NOT labels):")
    for bucket, count in bucket_counts.items():
        print(f"  {bucket}: {count}")
    
    n_hard = int(n_target * 0.25)
    n_safety = int(n_target * 0.15)
    n_stratified = n_target - n_hard - n_safety
    
    selected_ids = set()
    examples = []
    
    # --- Tier 1: Safety-adjacent oversampling (~15%) ---
    safety_pool = inbound[inbound["_is_safety"]].copy()
    if len(safety_pool) < n_safety:
        print(f"  WARNING: Only {len(safety_pool)} safety-adjacent tweets found (wanted {n_safety})")
        n_safety = len(safety_pool)
    
    safety_sample = safety_pool.sample(n=min(n_safety, len(safety_pool)), random_state=42)
    for _, row in safety_sample.iterrows():
        tid = str(row["tweet_id"])
        if tid in selected_ids:
            continue
        selected_ids.add(tid)
        ctx = build_thread_context(tid, full_df)
        examples.append({
            "tweet_id": tid,
            "text": str(row["text"]),
            "thread_context": ctx,
            "true_intent": "",          # BLANK — human labels this
            "true_escalation_decision": "",  # BLANK — human labels this
            "escalation_reason": "",    # BLANK — human labels this
            "ambiguity_flag": "",       # BLANK — human labels this
            "notes": f"[sampling: safety_adjacent, rough_bucket={row['_rough_bucket']}]",
        })
    print(f"  Safety-adjacent sampled: {len(examples)}")
    
    # --- Tier 2: Hard/ambiguous cases (~25%) ---
    hard_pool = inbound[
        (inbound["_is_hard"]) & (~inbound["tweet_id"].isin(selected_ids))
    ].copy()
    if len(hard_pool) < n_hard:
        print(f"  WARNING: Only {len(hard_pool)} hard cases found (wanted {n_hard})")
        n_hard = min(n_hard, len(hard_pool))
    
    hard_sample = hard_pool.sample(n=min(n_hard, len(hard_pool)), random_state=43)
    hard_count = 0
    for _, row in hard_sample.iterrows():
        tid = str(row["tweet_id"])
        if tid in selected_ids:
            continue
        selected_ids.add(tid)
        ctx = build_thread_context(tid, full_df)
        examples.append({
            "tweet_id": tid,
            "text": str(row["text"]),
            "thread_context": ctx,
            "true_intent": "",
            "true_escalation_decision": "",
            "escalation_reason": "",
            "ambiguity_flag": "",
            "notes": f"[sampling: hard_case, rough_bucket={row['_rough_bucket']}]",
        })
        hard_count += 1
    print(f"  Hard/ambiguous sampled: {hard_count}")
    
    # --- Tier 3: Stratified random (~60%) ---
    remaining = inbound[~inbound["tweet_id"].isin(selected_ids)].copy()
    n_remaining_needed = n_target - len(examples)
    
    # Stratify across rough buckets
    buckets = remaining["_rough_bucket"].unique()
    per_bucket = max(3, n_remaining_needed // len(buckets))
    
    strat_count = 0
    for bucket in buckets:
        bucket_pool = remaining[remaining["_rough_bucket"] == bucket]
        n_from_bucket = min(per_bucket, len(bucket_pool))
        if n_from_bucket == 0:
            continue
        bucket_sample = bucket_pool.sample(n=n_from_bucket, random_state=44)
        for _, row in bucket_sample.iterrows():
            tid = str(row["tweet_id"])
            if tid in selected_ids:
                continue
            selected_ids.add(tid)
            ctx = build_thread_context(tid, full_df)
            examples.append({
                "tweet_id": tid,
                "text": str(row["text"]),
                "thread_context": ctx,
                "true_intent": "",
                "true_escalation_decision": "",
                "escalation_reason": "",
                "ambiguity_flag": "",
                "notes": f"[sampling: stratified_random, rough_bucket={bucket}]",
            })
            strat_count += 1
            if len(examples) >= n_target:
                break
        if len(examples) >= n_target:
            break
    print(f"  Stratified random sampled: {strat_count}")
    
    # Fill remaining if needed
    if len(examples) < n_target:
        remaining2 = inbound[~inbound["tweet_id"].isin(selected_ids)]
        fill = remaining2.sample(n=min(n_target - len(examples), len(remaining2)), random_state=45)
        for _, row in fill.iterrows():
            tid = str(row["tweet_id"])
            if tid in selected_ids:
                continue
            selected_ids.add(tid)
            ctx = build_thread_context(tid, full_df)
            examples.append({
                "tweet_id": tid,
                "text": str(row["text"]),
                "thread_context": ctx,
                "true_intent": "",
                "true_escalation_decision": "",
                "escalation_reason": "",
                "ambiguity_flag": "",
                "notes": "[sampling: fill]",
            })
            if len(examples) >= n_target:
                break
    
    random.shuffle(examples)
    return examples[:n_target]


def main() -> None:
    parser = argparse.ArgumentParser(description="Sample real tweets for golden set labeling")
    parser.add_argument("--n", type=int, default=200, help="Target golden set size")
    parser.add_argument(
        "--output", type=str,
        default=str(ROOT / "eval" / "golden_set_unlabeled.csv"),
        help="Output path for blank-labels CSV",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("GOLDEN SET SAMPLING — Real Uber_Support Tweets")
    print("=" * 60)

    # Load full processed data (for thread context)
    threads_path = PROCESSED_DIR / "uber_threads.csv"
    full_df = pd.read_csv(threads_path, dtype=str)
    full_df["inbound"] = full_df["inbound"].map(
        {"True": True, "False": False, "true": True, "false": False}
    )

    inbound = load_uber_inbound(PROCESSED_DIR)
    examples = sample_golden_set(inbound, full_df, n_target=args.n)

    # Write CSV with blank label columns
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "tweet_id", "text", "thread_context",
        "true_intent", "true_escalation_decision",
        "escalation_reason", "ambiguity_flag", "notes",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(examples)

    print(f"\n{'=' * 60}")
    print(f"DONE — {len(examples)} tweets sampled → {output_path}")
    print(f"{'=' * 60}")
    print(f"\nNEXT STEPS:")
    print(f"  1. Open {output_path}")
    print(f"  2. For each row, fill in:")
    print(f"     - true_intent (from taxonomy in eval/golden_set_notes.md)")
    print(f"     - true_escalation_decision (auto_handle | escalate)")
    print(f"     - escalation_reason (one sentence, your own judgment)")
    print(f"     - ambiguity_flag (TRUE if genuinely could go either way)")
    print(f"  3. Label BEFORE looking at any model output (avoid anchoring)")
    print(f"  4. Do ~40-50 per session, re-read intent definitions each time")
    print(f"  5. Save labeled file as eval/golden_set.csv")
    print(f"  6. Then run: python scripts/validate_golden_set.py")


if __name__ == "__main__":
    main()
