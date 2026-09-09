#!/usr/bin/env python3
"""
Prepare Uber_Support subsample from Kaggle twcs.csv OR use bundled sample data.

Usage:
  python scripts/prepare_data.py                    # uses bundled sample (fast)
  python scripts/prepare_data.py --kaggle path/to/twcs.csv  # full extraction
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import PROCESSED_DIR, RAW_DIR, SAMPLE_DIR, UBER_SUPPORT_HANDLE


def extract_uber_from_kaggle(csv_path: Path, max_threads: int = 5000) -> pd.DataFrame:
    """Extract Uber_Support threads from full Kaggle dataset efficiently using chunks."""
    print(f"Reading {csv_path} in chunks to find Uber threads...")
    
    thread_ids = set()
    author_counts = {}
    
    # Pass 1: Find all Uber_Support interactions
    chunk_count = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=100000):
        chunk_count += 1
        print(f"  Processed {chunk_count * 100000} rows...", end="\r")
        chunk["inbound"] = chunk["inbound"].map({"True": True, "False": False, True: True, False: False})
        
        # Count authors for stats
        outbound = chunk[chunk["inbound"] == False]
        for author in outbound["author_id"]:
            author_counts[author] = author_counts.get(author, 0) + 1
            
        # Find Uber replies
        uber_outbound = chunk[(chunk["author_id"] == UBER_SUPPORT_HANDLE) & (chunk["inbound"] == False)]
        thread_ids.update(uber_outbound["tweet_id"].dropna().tolist())
        thread_ids.update(uber_outbound["in_response_to_tweet_id"].dropna().tolist())
    
    print("\nTop support handles (estimated):")
    top_handles = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for handle, count in top_handles:
        print(f"  {handle}: {count}")
    
    print(f"\nFound {len(thread_ids)} unique tweet IDs related to Uber_Support.")
    
    # Pass 2: Extract those threads
    print("Extracting full thread context...")
    related_dfs = []
    chunk_count = 0
    for chunk in pd.read_csv(csv_path, dtype=str, chunksize=100000):
        chunk_count += 1
        print(f"  Extraction pass: processed {chunk_count * 100000} rows...", end="\r")
        chunk["inbound"] = chunk["inbound"].map({"True": True, "False": False, True: True, False: False})
        
        # We need tweets that are IN the thread_ids set OR respond to them (fast check)
        mask = (
            chunk["tweet_id"].isin(thread_ids) |
            chunk["in_response_to_tweet_id"].isin(thread_ids)
        )
        if mask.any():
            related_dfs.append(chunk[mask])
    
    print()
    if not related_dfs:
        print("No Uber_Support tweets found!")
        return pd.DataFrame()
        
    related = pd.concat(related_dfs, ignore_index=True)
    print(f"Extracted {len(related)} tweets in Uber_Support threads")
    return related.head(max_threads * 5)  # rough cap


def build_precedent_pairs(df: pd.DataFrame) -> list[dict]:
    """Build (customer_msg, brand_reply) pairs as resolution precedents."""
    pairs = []
    outbound = df[(df["author_id"] == UBER_SUPPORT_HANDLE) & (df["inbound"] == False)]

    for _, reply_row in outbound.iterrows():
        parent_id = reply_row.get("in_response_to_tweet_id")
        if pd.isna(parent_id):
            continue
        parent = df[df["tweet_id"] == parent_id]
        if parent.empty:
            continue
        customer = parent.iloc[0]
        if not customer.get("inbound", True):
            continue

        # Resolution proxy: no further inbound complaint within same thread within 24h
        # (simplified — full implementation would check thread continuation)
        pair_id = f"p_{reply_row['tweet_id']}"
        pairs.append({
            "id": pair_id,
            "customer_msg": str(customer["text"]),
            "brand_reply": str(reply_row["text"]),
            "tweet_id": str(customer["tweet_id"]),
            "reply_tweet_id": str(reply_row["tweet_id"]),
            "resolved": True,
        })
    return pairs


def use_bundled_sample() -> tuple[pd.DataFrame, list[dict]]:
    """Load pre-built sample data for fast reproducibility."""
    tweets_path = SAMPLE_DIR / "uber_tweets.csv"
    precedents_path = SAMPLE_DIR / "precedents.json"

    if not tweets_path.exists():
        raise FileNotFoundError(
            f"Bundled sample not found at {tweets_path}. "
            "Run with --kaggle or ensure sample data is present."
        )

    df = pd.read_csv(tweets_path, dtype=str)
    df["inbound"] = df["inbound"].map({"True": True, "False": False, "true": True, "false": False})

    with precedents_path.open(encoding="utf-8") as f:
        precedents = json.load(f)

    return df, precedents


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare Uber support data")
    parser.add_argument("--kaggle", type=str, help="Path to twcs.csv from Kaggle")
    parser.add_argument("--max-threads", type=int, default=5000)
    args = parser.parse_args()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if args.kaggle:
        csv_path = Path(args.kaggle)
        if not csv_path.exists():
            csv_path = RAW_DIR / "twcs.csv"
        df = extract_uber_from_kaggle(csv_path, args.max_threads)
        precedents = build_precedent_pairs(df)
        source = "kaggle"
    else:
        print("Using bundled sample data (fast path for <15 min repro)...")
        df, precedents = use_bundled_sample()
        source = "bundled_sample"

    df.to_csv(PROCESSED_DIR / "uber_threads.csv", index=False)

    with (PROCESSED_DIR / "precedents.json").open("w", encoding="utf-8") as f:
        json.dump(precedents, f, indent=2, ensure_ascii=False)

    # Compute detailed metadata for verification
    df_copy = df.copy()
    df_copy["inbound"] = df_copy["inbound"].map(
        {"True": True, "False": False, "true": True, "false": False, True: True, False: False}
    )
    n_inbound = int((df_copy["inbound"] == True).sum())
    n_outbound = int((df_copy["inbound"] == False).sum())
    
    date_range = {}
    if "created_at" in df_copy.columns:
        dates = pd.to_datetime(df_copy["created_at"], errors="coerce").dropna()
        if len(dates) > 0:
            date_range = {"earliest": str(dates.min()), "latest": str(dates.max())}
    
    uber_outbound = int(
        ((df_copy["author_id"] == UBER_SUPPORT_HANDLE) & (df_copy["inbound"] == False)).sum()
    )

    meta = {
        "source": source,
        "num_tweets": len(df),
        "num_inbound": n_inbound,
        "num_outbound": n_outbound,
        "num_uber_support_outbound": uber_outbound,
        "num_precedents": len(precedents),
        "brand": UBER_SUPPORT_HANDLE,
        "date_range": date_range,
    }
    with (PROCESSED_DIR / "data_meta.json").open("w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"\nSaved {len(df)} tweets, {len(precedents)} precedent pairs into {PROCESSED_DIR}")
    print(f"  Inbound: {n_inbound}, Outbound: {n_outbound}")
    print(f"  Uber_Support outbound: {uber_outbound}")
    if date_range:
        print(f"  Date range: {date_range['earliest']} → {date_range['latest']}")


if __name__ == "__main__":
    main()
