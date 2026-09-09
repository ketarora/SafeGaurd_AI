#!/usr/bin/env python3
"""Generate bundled sample data and golden evaluation set."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = ROOT / "data" / "sample"
EVAL_DIR = ROOT / "eval"

random.seed(42)

# Realistic Uber support tweet templates by intent
TEMPLATES = {
    "promo_code_failed": [
        "My promo code SAVE20 didn't work at checkout, charged full price @Uber_Support",
        "Applied discount code but still got charged $45, code was supposed to be 50% off",
        "Why won't my uber promo apply? Tried 3 times",
        "Code UBEREATS25 says invalid but it's from your email campaign",
        "Promo not working again!!! This is the 2nd time this month",
    ],
    "receipt_request": [
        "Need a receipt for my trip yesterday for expense report @Uber_Support",
        "Can you email me the invoice for trip on March 15?",
        "How do I get a receipt? Can't find it in the app",
        "Business trip receipt needed - trip ID 12345",
        "Please send receipt to my work email for reimbursement",
    ],
    "lost_item": [
        "Left my phone in the Uber last night, white Toyota Camry around 11pm",
        "Forgot my wallet in the car, driver already left. Trip was to airport",
        "I left my keys in the back seat, need to contact driver",
        "Lost item - blue backpack left in vehicle, trip ended 30 min ago",
        "My AirPods are still in the car from my ride this morning",
    ],
    "app_technical_bug": [
        "App keeps crashing when I try to request a ride @Uber_Support",
        "Payment method won't save, keeps saying error occurred",
        "GPS showing wrong location, can't get picked up",
        "Can't login to my account, stuck on loading screen",
        "App frozen on splash screen after update, iPhone 14",
    ],
    "fare_overcharge_dispute": [
        "Charged $67 for a trip that normally costs $25, this is ridiculous @Uber_Support",
        "Driver took a longer route on purpose, fare was double what it should be",
        "Got charged twice for the same trip!!!",
        "Upfront price was $18, final charge was $34. Why?",
        "This fare is way too high for a 2 mile trip, disputing this",
    ],
    "cancellation_fee_dispute": [
        "Charged $5 cancellation fee but driver never showed up @Uber_Support",
        "Why am I being charged for cancelling when the wait was 20 min?",
        "Cancelled because driver was going wrong direction, still got fee",
        "Unfair cancellation charge - app said driver was 15 min away for 25 min",
        "Fee for cancelling a ride where driver never arrived at pickup",
    ],
    "driver_behavior_complaint": [
        "Driver was extremely rude and yelled at me @Uber_Support",
        "Driver was smoking in the car, very unprofessional",
        "Driver took a phone call the entire ride on speaker, ignored me",
        "Driver had terrible attitude, refused to help with bags",
        "Most disrespectful driver I've ever had, complained about the tip",
    ],
    "driver_unsafe_incident": [
        "Driver ran a red light and I almost got hurt @Uber_Support this is NOT ok",
        "Felt unsafe - driver was driving recklessly, swerving between lanes",
        "Driver made me feel physically threatened, would not unlock doors",
        "Got into an accident because driver was texting while driving",
        "Driver harassed me during the ride, I was scared for my safety",
        "Unsafe driving - nearly hit a pedestrian, I'm reporting this",
        "Driver appeared intoxicated, I got out early because I was afraid",
        "Sexual harassment from driver during ride, this is assault",
    ],
    "account_access_issue": [
        "Locked out of my account, can't reset password @Uber_Support",
        "My account was deactivated for no reason, need it back",
        "Banned from uber with no explanation, I did nothing wrong",
        "Can't access account after phone number change",
        "Account suspended - I rely on Uber for work, please help",
    ],
    "general_inquiry": [
        "How do I schedule a ride in advance?",
        "Thanks for the great service last night!",
        "Do you operate in Portland Oregon?",
        "What's the difference between UberX and Comfort?",
        "Can I add a stop during my ride?",
    ],
}

BRAND_REPLIES = {
    "promo_code_failed": "Sorry about that! Please DM us your trip details and the promo code — we'll check why it didn't apply.",
    "receipt_request": "You can find receipts in the app under Your Trips → select trip → Receipt. DM us if you need help!",
    "lost_item": "Sorry to hear that! Use the in-app Lost Item feature (Your Trips → trip → I lost an item) to contact your driver.",
    "app_technical_bug": "Sorry for the trouble! Try force-closing the app. If it persists, DM us your device and app version.",
    "fare_overcharge_dispute": "We understand fare concerns. Please DM us trip details — our team will review the route and charges.",
    "cancellation_fee_dispute": "Cancellation fees can be confusing. DM us the trip date and we'll review whether the fee applies.",
    "driver_behavior_complaint": "We're sorry about your experience. Please DM us trip details so we can investigate.",
    "driver_unsafe_incident": "We're very sorry. Your safety is our priority — a specialist will reach out shortly.",
    "account_access_issue": "Sorry you're locked out. Please DM us the email on your account and we'll help restore access.",
    "general_inquiry": "Thanks for reaching out! DM us for account-specific help.",
}

# Hard/ambiguous cases
HARD_CASES = [
    ("app_technical_bug", "App crashed AND driver was rude AND I want a refund @Uber_Support", True, "escalate"),
    ("driver_unsafe_incident", "Driver was reckless but also overcharged me", True, "escalate"),
    ("general_inquiry", "???", True, "auto_handle"),
    ("fare_overcharge_dispute", "scam", True, "escalate"),
    ("driver_behavior_complaint", "worst driver ever", True, "escalate"),
    ("lost_item", "phone", False, "auto_handle"),
    ("driver_unsafe_incident", "not safe", True, "escalate"),
    ("promo_code_failed", "code no work 😤", False, "auto_handle"),
    ("account_access_issue", "help cant get in", True, "escalate"),
    ("driver_unsafe_incident", "he scared me", True, "escalate"),
]


def generate_precedents() -> list[dict]:
    precedents = []
    pid = 0
    for intent, templates in TEMPLATES.items():
        for tmpl in templates:
            pid += 1
            precedents.append({
                "id": f"p_{pid:04d}",
                "customer_msg": tmpl.replace(" @Uber_Support", "").replace("@Uber_Support ", ""),
                "brand_reply": BRAND_REPLIES[intent],
                "tweet_id": f"t_{pid:04d}",
                "reply_tweet_id": f"r_{pid:04d}",
                "resolved": True,
                "intent": intent,
            })
    return precedents


def generate_tweets(precedents: list[dict]) -> list[dict]:
    tweets = []
    tid = 0
    for p in precedents:
        tid += 1
        tweets.append({
            "tweet_id": p["tweet_id"],
            "author_id": "customer_123",
            "inbound": True,
            "created_at": "2020-01-15 10:00:00",
            "text": p["customer_msg"],
            "response_tweet_id": p["reply_tweet_id"],
            "in_response_to_tweet_id": "",
        })
        tid += 1
        tweets.append({
            "tweet_id": p["reply_tweet_id"],
            "author_id": "Uber_Support",
            "inbound": False,
            "created_at": "2020-01-15 10:05:00",
            "text": p["brand_reply"],
            "response_tweet_id": "",
            "in_response_to_tweet_id": p["tweet_id"],
        })
    return tweets


def generate_golden_set(n_target: int = 200) -> list[dict]:
    """Generate stratified golden set following the methodology."""
    examples = []
    eid = 0

    # ~60% stratified random from each intent
    n_stratified = int(n_target * 0.60)
    per_intent = max(8, n_stratified // len(TEMPLATES))

    for intent, templates in TEMPLATES.items():
        default_esc = "escalate" if intent in (
            "fare_overcharge_dispute", "cancellation_fee_dispute",
            "driver_behavior_complaint", "driver_unsafe_incident", "account_access_issue",
        ) else "auto_handle"

        pool = templates * 3  # repeat for variety
        random.shuffle(pool)
        for i in range(min(per_intent, len(pool))):
            eid += 1
            text = pool[i]
            examples.append({
                "tweet_id": f"g_{eid:04d}",
                "text": text,
                "thread_context": "",
                "true_intent": intent,
                "true_escalation_decision": default_esc,
                "escalation_reason": f"Default routing for {intent}",
                "ambiguity_flag": False,
                "human_correctness": 4 if default_esc == "auto_handle" else 3,
                "human_tone": 4,
                "human_actionability": 4,
                "human_escalation_appropriate": default_esc == "escalate",
                "notes": "",
            })

    # ~25% hard/ambiguous
    n_hard = int(n_target * 0.25)
    hard_pool = HARD_CASES * 5
    random.shuffle(hard_pool)
    for i in range(min(n_hard, len(hard_pool))):
        intent, text, amb, esc = hard_pool[i]
        eid += 1
        examples.append({
            "tweet_id": f"g_{eid:04d}",
            "text": text,
            "thread_context": "",
            "true_intent": intent,
            "true_escalation_decision": esc,
            "escalation_reason": "Ambiguous/multi-issue — conservative escalate" if esc == "escalate" else "Low-stakes despite ambiguity",
            "ambiguity_flag": amb,
            "human_correctness": 3,
            "human_tone": 3,
            "human_actionability": 3,
            "human_escalation_appropriate": esc == "escalate",
            "notes": "Hard case — deliberately sampled",
        })

    # ~15% safety oversample
    n_safety = int(n_target * 0.15)
    safety_templates = TEMPLATES["driver_unsafe_incident"] * 4
    random.shuffle(safety_templates)
    for i in range(min(n_safety, len(safety_templates))):
        eid += 1
        text = safety_templates[i]
        examples.append({
            "tweet_id": f"g_{eid:04d}",
            "text": text,
            "thread_context": "",
            "true_intent": "driver_unsafe_incident",
            "true_escalation_decision": "escalate",
            "escalation_reason": "Physical safety — always escalate",
            "ambiguity_flag": False,
            "human_correctness": 3,
            "human_tone": 4,
            "human_actionability": 3,
            "human_escalation_appropriate": True,
            "notes": "Safety oversample",
        })

    # Trim to target
    random.shuffle(examples)
    return examples[:n_target]


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    precedents = generate_precedents()
    tweets = generate_tweets(precedents)
    golden = generate_golden_set(200)

    with (SAMPLE_DIR / "precedents.json").open("w", encoding="utf-8") as f:
        json.dump(precedents, f, indent=2, ensure_ascii=False)

    with (SAMPLE_DIR / "uber_tweets.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=tweets[0].keys())
        writer.writeheader()
        writer.writerows(tweets)

    fieldnames = list(golden[0].keys())
    with (EVAL_DIR / "golden_set.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(golden)

    print(f"Generated {len(precedents)} precedents, {len(tweets)} tweets, {len(golden)} golden examples")
    intents = {}
    for g in golden:
        intents[g["true_intent"]] = intents.get(g["true_intent"], 0) + 1
    print("Golden set intent distribution:", intents)
    safety = sum(1 for g in golden if g["true_intent"] == "driver_unsafe_incident")
    print(f"Safety incidents in golden set: {safety}")


if __name__ == "__main__":
    main()
