#!/usr/bin/env python3
"""
Explore real Uber_Support data from processed Kaggle extract.
Print statistics needed to validate taxonomy and sampling strategy.

Usage:
  python scripts/explore_data.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import KEYWORD_RULES, PROCESSED_DIR, SAFETY_KEYWORDS, UBER_SUPPORT_HANDLE


def main() -> None:
    threads_path = PROCESSED_DIR / "uber_threads.csv"
    meta_path = PROCESSED_DIR / "data_meta.json"
    precedents_path = PROCESSED_DIR / "precedents.json"

    if not threads_path.exists():
        print(f"No processed data at {threads_path}")
        print("Run: python scripts/prepare_data.py --kaggle data/raw/twcs.csv")
        sys.exit(1)

    df = pd.read_csv(threads_path, dtype=str)
    df["inbound"] = df["inbound"].map({"True": True, "False": False, "true": True, "false": False})

    # Load metadata
    if meta_path.exists():
        with meta_path.open() as f:
            meta = json.load(f)
        print(f"Data source: {meta.get('source')}")
        print(f"Total tweets in extract: {meta.get('num_tweets')}")
        print(f"Precedent pairs: {meta.get('num_precedents')}")
    
    print(f"\n{'=' * 60}")
    print(f"UBER_SUPPORT DATA EXPLORATION")
    print(f"{'=' * 60}")

    # --- Basic stats ---
    n_total = len(df)
    n_inbound = (df["inbound"] == True).sum()
    n_outbound = (df["inbound"] == False).sum()
    
    print(f"\nTotal tweets: {n_total}")
    print(f"  Inbound (customer): {n_inbound} ({n_inbound/n_total*100:.1f}%)")
    print(f"  Outbound (brand):   {n_outbound} ({n_outbound/n_total*100:.1f}%)")

    # --- Author distribution ---
    print(f"\nTop authors (outbound):")
    outbound = df[df["inbound"] == False]
    top_authors = outbound["author_id"].value_counts().head(5)
    for author, count in top_authors.items():
        print(f"  {author}: {count}")

    uber_outbound = outbound[outbound["author_id"] == UBER_SUPPORT_HANDLE]
    print(f"\nUber_Support outbound tweets: {len(uber_outbound)}")

    # --- Date range ---
    if "created_at" in df.columns:
        dates = pd.to_datetime(df["created_at"], errors="coerce")
        valid_dates = dates.dropna()
        if len(valid_dates) > 0:
            print(f"\nDate range: {valid_dates.min()} to {valid_dates.max()}")
    
    # --- Inbound tweet analysis ---
    inbound = df[df["inbound"] == True].copy()
    inbound = inbound.dropna(subset=["text"])
    inbound["text_len"] = inbound["text"].str.len()
    
    print(f"\n{'=' * 60}")
    print(f"INBOUND TWEET ANALYSIS ({len(inbound)} tweets)")
    print(f"{'=' * 60}")
    
    print(f"\nText length: mean={inbound['text_len'].mean():.0f}, "
          f"median={inbound['text_len'].median():.0f}, "
          f"min={inbound['text_len'].min():.0f}, max={inbound['text_len'].max():.0f}")

    # --- Rough intent bucketing ---
    print(f"\n--- Rough Keyword-Based Intent Distribution ---")
    print(f"(This is heuristic, NOT ground truth — for taxonomy validation only)")
    
    def rough_bucket(text: str) -> str:
        lower = text.lower()
        if any(kw in lower for kw in SAFETY_KEYWORDS):
            return "safety_adjacent"
        for intent, keywords in KEYWORD_RULES.items():
            if intent == "driver_unsafe_incident":
                continue
            if any(kw in lower for kw in keywords):
                return intent
        return "unmatched"
    
    inbound["_bucket"] = inbound["text"].apply(rough_bucket)
    bucket_counts = inbound["_bucket"].value_counts()
    
    for bucket, count in bucket_counts.items():
        pct = count / len(inbound) * 100
        bar = "█" * int(pct / 2)
        print(f"  {bucket:<30} {count:>5} ({pct:5.1f}%) {bar}")

    # --- Safety keyword analysis ---
    print(f"\n--- Safety Keyword Analysis ---")
    safety_hits = inbound[inbound["_bucket"] == "safety_adjacent"]
    print(f"Tweets with safety keywords: {len(safety_hits)} ({len(safety_hits)/len(inbound)*100:.2f}%)")
    
    if len(safety_hits) > 0:
        print(f"\nFirst 10 safety-adjacent tweets (for taxonomy validation):")
        for i, (_, row) in enumerate(safety_hits.head(10).iterrows()):
            text = str(row["text"])[:120].replace("\n", " ")
            print(f"  [{i+1}] {text}")
    
    # --- Short/ambiguous messages ---
    short = inbound[inbound["text_len"] < 30]
    print(f"\n--- Short Messages (<30 chars) ---")
    print(f"Count: {len(short)} ({len(short)/len(inbound)*100:.1f}%)")
    if len(short) > 0:
        print(f"Examples:")
        for _, row in short.head(10).iterrows():
            print(f"  \"{row['text']}\"")

    # --- Unmatched (would default to general_inquiry) ---
    unmatched = inbound[inbound["_bucket"] == "unmatched"]
    print(f"\n--- Unmatched (no keyword hit → general_inquiry default) ---")
    print(f"Count: {len(unmatched)} ({len(unmatched)/len(inbound)*100:.1f}%)")
    if len(unmatched) > 0:
        sample = unmatched.sample(n=min(15, len(unmatched)), random_state=42)
        print(f"Random sample of 15:")
        for _, row in sample.iterrows():
            text = str(row["text"])[:120].replace("\n", " ")
            print(f"  \"{text}\"")

    # --- Thread structure ---
    print(f"\n--- Thread Structure ---")
    has_context = df["in_response_to_tweet_id"].notna() & (df["in_response_to_tweet_id"] != "")
    print(f"Tweets with in_response_to: {has_context.sum()} ({has_context.sum()/n_total*100:.1f}%)")
    
    # --- Precedent quality check ---
    if precedents_path.exists():
        with precedents_path.open(encoding="utf-8") as f:
            precedents = json.load(f)
        print(f"\n--- Precedent Pairs (for retrieval grounding) ---")
        print(f"Total: {len(precedents)}")
        reply_lens = [len(p.get("brand_reply", "")) for p in precedents]
        print(f"Reply length: mean={sum(reply_lens)/len(reply_lens):.0f}, "
              f"min={min(reply_lens)}, max={max(reply_lens)}")
        
        # Sample precedents
        print(f"\nSample precedent pairs:")
        import random
        random.seed(42)
        for p in random.sample(precedents, min(5, len(precedents))):
            cust = p["customer_msg"][:80].replace("\n", " ")
            reply = p["brand_reply"][:80].replace("\n", " ")
            print(f"  Customer: \"{cust}\"")
            print(f"  Reply:    \"{reply}\"")
            print()

    print(f"\n{'=' * 60}")
    print(f"TAXONOMY VALIDATION SUMMARY")
    print(f"{'=' * 60}")
    print(f"Review the distributions above. Check:")
    print(f"  1. Does the 10-intent taxonomy cover the major clusters?")
    print(f"  2. Are any categories too sparse to evaluate (<5 examples)?")
    print(f"  3. Is 'unmatched' hiding a real category we should add?")
    print(f"  4. Should any categories be merged?")
    print(f"  5. How many safety-adjacent tweets exist for oversampling?")


if __name__ == "__main__":
    main()
