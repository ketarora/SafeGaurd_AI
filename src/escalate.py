"""Stage 3 — Escalation decision with hard-coded safety guardrail."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import (
    CONFIDENCE_ESCALATE_THRESHOLD,
    DEFAULT_ESCALATION,
    LLM_TEMPERATURE_ESCALATE,
    RETRIEVAL_STRONG_THRESHOLD,
    SAFETY_KEYWORDS,
)
from src.utils import ESCALATE_SCHEMA, call_llm, detect_safety_keywords, get_openai_client

ESCALATE_SYSTEM_PROMPT = """You decide whether an Uber support case can be auto-handled or must be escalated to a human.

HARD RULE (always applies — you cannot override):
- If intent is driver_unsafe_incident OR safety_keyword_flag is true: ALWAYS escalate.

ESCALATE IF:
- intent confidence < 0.6
- grounding_quality is none/weak AND intent involves money or account access
- repeat_contact_flag is true
- intent is fare_overcharge_dispute, cancellation_fee_dispute, or account_access_issue (default escalate unless confidence >= 0.85 AND grounding is strong)

OUTPUT FORMAT (strict JSON):
{"decision": "auto_handle|escalate", "reason": "<specific reason>", "risk_if_wrong": "<one sentence>"}"""


@dataclass
class EscalationResult:
    decision: str  # auto_handle | escalate
    reason: str
    risk_if_wrong: str
    hard_rule_triggered: bool
    safety_keyword_flag: bool


class EscalationDecider:
    """
    Deterministic safety guardrail FIRST, then rule-based logic, then optional LLM reasoning.
    driver_unsafe_incident CANNOT be auto-handled — enforced in code.
    """

    HIGH_STAKES_INTENTS = {
        "fare_overcharge_dispute",
        "cancellation_fee_dispute",
        "account_access_issue",
        "driver_behavior_complaint",
        "driver_unsafe_incident",
    }

    MONEY_INTENTS = {"fare_overcharge_dispute", "cancellation_fee_dispute"}

    def decide(
        self,
        *,
        text: str,
        intent: str,
        intent_confidence: float,
        draft_reply: str,
        grounding_quality: str,
        sentiment_flag: str = "neutral",
        repeat_contact_flag: bool = False,
    ) -> EscalationResult:
        safety_keyword_flag = detect_safety_keywords(text, SAFETY_KEYWORDS)

        # === HARD RULE — cannot be bypassed ===
        if intent == "driver_unsafe_incident" or safety_keyword_flag:
            return EscalationResult(
                decision="escalate",
                reason=(
                    f"HARD RULE: {'driver_unsafe_incident intent' if intent == 'driver_unsafe_incident' else ''}"
                    f"{' + safety keywords detected' if safety_keyword_flag else ''} "
                    "— physical safety cases always require human review"
                ).strip(),
                risk_if_wrong="Auto-handling a safety incident could leave a customer in danger and create legal liability",
                hard_rule_triggered=True,
                safety_keyword_flag=safety_keyword_flag,
            )

        # === Rule-based escalation logic ===
        reasons: list[str] = []

        if intent_confidence < CONFIDENCE_ESCALATE_THRESHOLD:
            reasons.append(f"Low classification confidence ({intent_confidence:.2f} < {CONFIDENCE_ESCALATE_THRESHOLD})")

        if grounding_quality in ("none", "weak") and intent in self.MONEY_INTENTS | {"account_access_issue"}:
            reasons.append(f"Weak/no grounding for high-stakes intent '{intent}'")

        if repeat_contact_flag:
            reasons.append("Repeat contact — prior unresolved issue")

        if sentiment_flag == "angry":
            reasons.append("Angry customer sentiment — human empathy needed")

        # Default escalate for high-stakes unless strong override conditions met
        if intent in self.HIGH_STAKES_INTENTS:
            override_ok = (
                intent_confidence >= 0.85
                and grounding_quality == "strong"
                and intent not in self.MONEY_INTENTS
            )
            if not override_ok and intent in self.MONEY_INTENTS | {"account_access_issue"}:
                reasons.append(f"Default escalate for '{intent}' — financial/account impact")
            elif not override_ok and intent == "driver_behavior_complaint":
                reasons.append("Driver conduct complaints require human judgment")

        # Low-stakes intents with good signals → auto_handle
        if not reasons and not DEFAULT_ESCALATION.get(intent, True):
            return EscalationResult(
                decision="auto_handle",
                reason=f"Low-stakes intent '{intent}' with confidence={intent_confidence:.2f} and grounding={grounding_quality}",
                risk_if_wrong="Customer may need follow-up if issue is more complex than classified",
                hard_rule_triggered=False,
                safety_keyword_flag=False,
            )

        if reasons:
            return EscalationResult(
                decision="escalate",
                reason="; ".join(reasons),
                risk_if_wrong=self._risk_for_intent(intent),
                hard_rule_triggered=False,
                safety_keyword_flag=False,
            )

        # Optional LLM layer for edge cases (never overrides hard rule — already passed)
        llm_result = self._llm_escalate(
            intent=intent,
            intent_confidence=intent_confidence,
            draft_reply=draft_reply,
            grounding_quality=grounding_quality,
            sentiment_flag=sentiment_flag,
            repeat_contact_flag=repeat_contact_flag,
            safety_keyword_flag=False,
        )
        if llm_result:
            return llm_result

        return EscalationResult(
            decision="auto_handle",
            reason=f"Passed all escalation checks for '{intent}'",
            risk_if_wrong="Edge case may be misclassified",
            hard_rule_triggered=False,
            safety_keyword_flag=False,
        )

    def _risk_for_intent(self, intent: str) -> str:
        risks = {
            "fare_overcharge_dispute": "Wrong auto-handle could deny legitimate refund, damaging trust",
            "cancellation_fee_dispute": "Customer charged unfairly with no recourse",
            "account_access_issue": "Locked-out customer cannot use service",
            "driver_behavior_complaint": "Pattern of bad driver behavior goes unaddressed",
        }
        return risks.get(intent, "Customer issue unresolved without human oversight")

    def _llm_escalate(self, **kwargs) -> EscalationResult | None:
        if get_openai_client() is None:
            return None
        try:
            data = call_llm(
                ESCALATE_SYSTEM_PROMPT,
                str(kwargs),
                temperature=LLM_TEMPERATURE_ESCALATE,
                response_schema=ESCALATE_SCHEMA,
            )
            # Safety check — never allow auto_handle if safety flag somehow set
            if kwargs.get("safety_keyword_flag"):
                data["decision"] = "escalate"
            return EscalationResult(
                decision=data["decision"],
                reason=data["reason"],
                risk_if_wrong=data["risk_if_wrong"],
                hard_rule_triggered=False,
                safety_keyword_flag=kwargs.get("safety_keyword_flag", False),
            )
        except Exception:
            return None


def evaluate_escalation_baseline(
    examples: list[dict],
    strategy: str = "always_escalate",
) -> dict:
    """Trivial escalation baselines."""
    decider = EscalationDecider()
    tp = fp = tn = fn = 0
    safety_recall_correct = 0
    safety_total = 0

    for ex in examples:
        true = ex["true_escalation_decision"]
        if strategy == "always_escalate":
            pred = "escalate"
            reason = "Baseline: always escalate"
        elif strategy == "never_escalate":
            pred = "auto_handle"
            reason = "Baseline: never escalate"
        else:
            result = decider.decide(
                text=ex["text"],
                intent=ex.get("pred_intent", ex["true_intent"]),
                intent_confidence=ex.get("pred_confidence", 0.8),
                draft_reply=ex.get("draft_reply", ""),
                grounding_quality=ex.get("grounding_quality", "weak"),
                sentiment_flag=ex.get("sentiment_flag", "neutral"),
                repeat_contact_flag=ex.get("repeat_contact_flag", False),
            )
            pred = result.decision
            reason = result.reason

        if true == "escalate":
            safety_total += 1 if ex["true_intent"] == "driver_unsafe_incident" else 0
            if ex["true_intent"] == "driver_unsafe_incident" and pred == "escalate":
                safety_recall_correct += 1
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
    safety_recall = (
        safety_recall_correct / safety_total if safety_total else 1.0
    )

    return {
        "strategy": strategy,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if (precision + recall) else 0,
        "driver_unsafe_recall": safety_recall,
    }
