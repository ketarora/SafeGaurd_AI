"""Central configuration for the Uber Support Agent pipeline."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SAMPLE_DIR = DATA_DIR / "sample"
EVAL_DIR = PROJECT_ROOT / "eval"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# Uber support handle in the Kaggle dataset (author_id for outbound tweets)
UBER_SUPPORT_HANDLE = "Uber_Support"

INTENTS = [
    "promo_code_failed",
    "receipt_request",
    "lost_item",
    "app_technical_bug",
    "fare_overcharge_dispute",
    "cancellation_fee_dispute",
    "driver_behavior_complaint",
    "driver_unsafe_incident",
    "account_access_issue",
    "general_inquiry",
]

# Default escalation routing per intent (overridden by hard safety rules)
DEFAULT_ESCALATION = {
    "promo_code_failed": False,
    "receipt_request": False,
    "lost_item": False,
    "app_technical_bug": False,
    "fare_overcharge_dispute": True,
    "cancellation_fee_dispute": True,
    "driver_behavior_complaint": True,
    "driver_unsafe_incident": True,
    "account_access_issue": True,
    "general_inquiry": False,
}

# Safety keywords — deterministic escalation trigger (code-level, not LLM-only)
SAFETY_KEYWORDS = [
    "assault", "attacked", "harass", "harassed", "unsafe", "dangerous",
    "accident", "crash", "hit me", "hit and run", "drunk driver", "drunk driving",
    "sexual", "threatened", "threaten", "afraid", "scared", "fear for my life",
    "physical", "violence", "violent", "injured", "injury", "hospital",
    "kidnap", "stalking", "weapon", "gun", "knife", "molest",
]

# Keyword rules for Baseline A (trivial classifier)
KEYWORD_RULES: dict[str, list[str]] = {
    "driver_unsafe_incident": SAFETY_KEYWORDS + ["reckless driving", "nearly killed"],
    "driver_behavior_complaint": [
        "rude", "unprofessional", "disrespectful", "yelled at me", "screamed",
        "smoking", "smoke", "bad attitude", "inappropriate",
    ],
    "fare_overcharge_dispute": [
        "overcharged", "overcharge", "too much", "charged twice", "double charge",
        "wrong fare", "fare dispute", "rip off", "ripoff", "expensive route",
    ],
    "cancellation_fee_dispute": [
        "cancellation fee", "cancel fee", "charged for cancel", "cancelled and charged",
    ],
    "promo_code_failed": [
        "promo code", "promo", "discount code", "coupon", "code not working",
        "code didn't work", "code wont work",
    ],
    "receipt_request": [
        "receipt", "invoice", "trip record", "email me the trip", "proof of trip",
    ],
    "lost_item": [
        "left my", "forgot my", "lost item", "left in the car", "left in car",
        "forgot in", "phone in the", "wallet in",
    ],
    "app_technical_bug": [
        "app crash", "app won't", "app wont", "not loading", "gps", "payment method",
        "can't login", "cant login", "bug", "glitch", "frozen", "error message",
    ],
    "account_access_issue": [
        "locked out", "deactivated", "banned", "suspended", "can't access account",
        "cant access account", "account disabled",
    ],
}

# Escalation thresholds
CONFIDENCE_ESCALATE_THRESHOLD = 0.6
RETRIEVAL_WEAK_THRESHOLD = 0.55
RETRIEVAL_STRONG_THRESHOLD = 0.72

# LLM settings
LLM_TEMPERATURE_CLASSIFY = 0.1
LLM_TEMPERATURE_DRAFT = 0.5
LLM_TEMPERATURE_ESCALATE = 0.1
LLM_TEMPERATURE_JUDGE = 0.1

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K_PRECEDENTS = 3
