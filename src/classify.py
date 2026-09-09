"""Stage 1 — Intent classification with baselines and main LLM classifier."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from src.config import (
    INTENTS,
    KEYWORD_RULES,
    LLM_TEMPERATURE_CLASSIFY,
)
from src.utils import CLASSIFY_SCHEMA, call_llm, get_openai_client, parse_json_response

ClassifierName = Literal["keyword", "tfidf", "llm"]

CLASSIFY_SYSTEM_PROMPT = """You are an intent classifier for Uber customer support tweets. Classify the customer's message into exactly one of the intents below. Do not invent new intents. If nothing fits well, use "general_inquiry".

INTENTS:
- promo_code_failed: a discount/promo code didn't apply or errored at checkout
- receipt_request: customer wants a receipt, invoice, or trip record
- lost_item: item left in a vehicle, not yet involving a dispute over driver conduct
- app_technical_bug: app crashes, payment method won't save, GPS glitches, login issues
- fare_overcharge_dispute: customer disputes the fare amount or the route taken
- cancellation_fee_dispute: customer disputes being charged a cancellation fee
- driver_behavior_complaint: rude, unprofessional, or inappropriate driver conduct that is NOT a physical safety concern
- driver_unsafe_incident: physical safety concern — accident, harassment, dangerous/reckless driving, assault, or any language suggesting the customer felt physically unsafe
- account_access_issue: locked out, banned, or deactivated account
- general_inquiry: anything else — general questions, positive feedback, unclear intent

RULES:
- Base your decision only on the text given. Do not assume context not present.
- If multiple intents seem to apply, pick the one that represents the customer's PRIMARY ask.
- CRITICAL: err toward driver_unsafe_incident whenever language is ambiguous between "annoying/unprofessional" and "unsafe" — a false negative here is far worse than a false positive.
- Output confidence as your genuine calibrated belief (0.0-1.0).
- If confidence is low, name the second-most-likely intent in your reasoning.

OUTPUT FORMAT (strict JSON, no markdown fences):
{"intent": "<intent>", "confidence": <float>, "reasoning": "<one sentence>"}"""


@dataclass
class ClassificationResult:
    intent: str
    confidence: float
    reasoning: str
    classifier: ClassifierName


class KeywordClassifier:
    """Baseline A — trivial keyword/rule matcher."""

    def classify(self, text: str, thread_context: str = "") -> ClassificationResult:
        combined = f"{thread_context} {text}".lower()
        scores: dict[str, int] = {}

        for intent, keywords in KEYWORD_RULES.items():
            scores[intent] = sum(1 for kw in keywords if kw in combined)

        # Safety gets priority boost
        if scores.get("driver_unsafe_incident", 0) > 0:
            return ClassificationResult(
                intent="driver_unsafe_incident",
                confidence=min(0.95, 0.6 + 0.1 * scores["driver_unsafe_incident"]),
                reasoning="Safety keyword match (rule-based)",
                classifier="keyword",
            )

        best_intent = max(scores, key=scores.get)  # type: ignore[arg-type]
        best_score = scores[best_intent]

        if best_score == 0:
            return ClassificationResult(
                intent="general_inquiry",
                confidence=0.35,
                reasoning="No keyword match — default to general_inquiry",
                classifier="keyword",
            )

        confidence = min(0.85, 0.45 + 0.1 * best_score)
        return ClassificationResult(
            intent=best_intent,
            confidence=confidence,
            reasoning=f"Keyword match score={best_score} for {best_intent}",
            classifier="keyword",
        )


class TfidfClassifier:
    """Baseline B — TF-IDF + Logistic Regression."""

    def __init__(self) -> None:
        self.pipeline: Pipeline | None = None
        self.intent_labels: list[str] = []

    def fit(self, texts: list[str], labels: list[str]) -> None:
        self.intent_labels = sorted(set(labels))
        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        self.pipeline.fit(texts, labels)

    def classify(self, text: str, thread_context: str = "") -> ClassificationResult:
        if self.pipeline is None:
            raise RuntimeError("TfidfClassifier not fitted — call fit() first")

        combined = f"{thread_context} {text}".strip()
        intent = self.pipeline.predict([combined])[0]
        proba = self.pipeline.predict_proba([combined])[0]
        confidence = float(np.max(proba))

        return ClassificationResult(
            intent=str(intent),
            confidence=confidence,
            reasoning=f"TF-IDF+LR prediction (max prob={confidence:.2f})",
            classifier="tfidf",
        )


class LLMClassifier:
    """Main classifier — few-shot LLM with structured JSON output."""

    def classify(self, text: str, thread_context: str = "") -> ClassificationResult:
        user_prompt = f"""CUSTOMER MESSAGE:
\"\"\"
{text}
\"\"\"

THREAD CONTEXT (prior messages, oldest first):
{thread_context or "(none)"}"""

        client = get_openai_client()
        if client is None:
            # Fallback to keyword in demo mode
            return KeywordClassifier().classify(text, thread_context)

        try:
            data = call_llm(
                CLASSIFY_SYSTEM_PROMPT,
                user_prompt,
                temperature=LLM_TEMPERATURE_CLASSIFY,
                response_schema=CLASSIFY_SCHEMA,
            )
            intent = data["intent"]
            if intent not in INTENTS:
                intent = "general_inquiry"
            return ClassificationResult(
                intent=intent,
                confidence=float(data["confidence"]),
                reasoning=data["reasoning"],
                classifier="llm",
            )
        except Exception as e:
            # Graceful degradation
            kw = KeywordClassifier().classify(text, thread_context)
            kw.reasoning = f"LLM failed ({e}); keyword fallback: {kw.reasoning}"
            return kw


def get_classifier(name: ClassifierName) -> KeywordClassifier | TfidfClassifier | LLMClassifier:
    if name == "keyword":
        return KeywordClassifier()
    if name == "tfidf":
        return TfidfClassifier()
    return LLMClassifier()


def evaluate_classifier(
    classifier_name: ClassifierName,
    examples: list[dict],
    tfidf_train: list[dict] | None = None,
) -> dict:
    """Evaluate classifier on labeled examples with leakage prevention."""
    if classifier_name == "tfidf":
        from sklearn.model_selection import KFold, cross_val_predict
        import warnings
        warnings.filterwarnings('ignore')
        
        train = tfidf_train or examples
        texts = [f"{e.get('thread_context','')} {e['text']}" for e in train]
        labels = [e["true_intent"] for e in train]
        classes = sorted(set(labels))
        
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(max_features=5000, ngram_range=(1, 2), min_df=1)),
            ("clf", LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        cv = KFold(n_splits=5, shuffle=True, random_state=42)
        cv_proba = cross_val_predict(pipeline, texts, labels, cv=cv, method="predict_proba")
        
        correct = 0
        per_intent: dict[str, dict[str, int]] = {i: {"tp": 0, "total": 0} for i in INTENTS}
        predictions = []

        for i, ex in enumerate(examples):
            true = ex["true_intent"]
            per_intent[true]["total"] += 1
            
            pred_idx = np.argmax(cv_proba[i])
            pred_intent = classes[pred_idx]
            confidence = float(cv_proba[i][pred_idx])
            
            if pred_intent == true:
                correct += 1
                per_intent[true]["tp"] += 1
            predictions.append({"true": true, "pred": pred_intent, "confidence": confidence})
            
        accuracy = correct / len(examples) if examples else 0
        per_intent_acc = {
            intent: (stats["tp"] / stats["total"] if stats["total"] else None)
            for intent, stats in per_intent.items()
            if stats["total"] > 0
        }

        return {
            "classifier": classifier_name,
            "accuracy": accuracy,
            "n": len(examples),
            "per_intent_accuracy": per_intent_acc,
            "predictions": predictions,
        }

    else:
        clf = get_classifier(classifier_name)

        correct = 0
        per_intent: dict[str, dict[str, int]] = {i: {"tp": 0, "total": 0} for i in INTENTS}
        predictions = []

        for ex in examples:
            result = clf.classify(ex["text"], ex.get("thread_context", ""))
            true = ex["true_intent"]
            per_intent[true]["total"] += 1
            if result.intent == true:
                correct += 1
                per_intent[true]["tp"] += 1
            predictions.append({"true": true, "pred": result.intent, "confidence": result.confidence})

        accuracy = correct / len(examples) if examples else 0
        per_intent_acc = {
            intent: (stats["tp"] / stats["total"] if stats["total"] else None)
            for intent, stats in per_intent.items()
            if stats["total"] > 0
        }

        return {
            "classifier": classifier_name,
            "accuracy": accuracy,
            "n": len(examples),
            "per_intent_accuracy": per_intent_acc,
            "predictions": predictions,
        }
