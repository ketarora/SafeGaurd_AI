"""Stage 2 — Grounded reply drafting from retrieved precedents."""

from __future__ import annotations

from dataclasses import dataclass

from src.config import LLM_TEMPERATURE_DRAFT, RETRIEVAL_STRONG_THRESHOLD, RETRIEVAL_WEAK_THRESHOLD
from src.retrieve import Precedent, PrecedentRetriever
from src.utils import DRAFT_SCHEMA, call_llm, get_openai_client

DRAFT_SYSTEM_PROMPT = """You are drafting an Uber customer support reply. Ground your reply in how Uber has historically resolved similar issues, shown as precedent examples below. Do not invent policy details not supported by the precedents.

RULES:
- Match Uber's tone from precedents: concise, professional, empathetic, action-oriented.
- If precedents point to a specific next step, include it.
- If precedents are weak matches, flag grounding as weak and draft a generic helpful reply.
- Never promise outcomes you can't verify from precedents.
- For driver_unsafe_incident: brief acknowledgment ONLY — no resolution language.
- Keep reply under 280 characters when possible.

OUTPUT FORMAT (strict JSON):
{"draft_reply": "<text>", "grounding_quality": "strong|weak|none", "precedent_ids_used": ["id"], "reasoning": "<one sentence>"}"""


@dataclass
class DraftResult:
    draft_reply: str
    grounding_quality: str
    precedent_ids_used: list[str]
    reasoning: str
    precedents: list[Precedent]


# Template replies for demo mode (no API key)
DEMO_TEMPLATES: dict[str, str] = {
    "promo_code_failed": "Thanks for reaching out! Please DM us your trip details and the promo code you used — we'll look into why it didn't apply.",
    "receipt_request": "Hi there! You can find your trip receipt in the app under 'Your Trips' → select the trip → 'Receipt'. Happy to help via DM if you can't locate it.",
    "lost_item": "Sorry to hear that! Please use the in-app Lost Item feature (Your Trips → select trip → 'I lost an item') to connect directly with your driver.",
    "app_technical_bug": "Sorry for the trouble! Try force-closing and reopening the app. If the issue persists, DM us your device model and app version.",
    "fare_overcharge_dispute": "We understand fare concerns are frustrating. Please DM us your trip details — our team will review the route and charges.",
    "cancellation_fee_dispute": "Cancellation fees can be confusing — DM us the trip date and we'll review whether the fee applies.",
    "driver_behavior_complaint": "We're sorry about your experience. Please DM us trip details so our team can investigate the driver's conduct.",
    "driver_unsafe_incident": "We're very sorry you had this experience. Your safety is our priority — a specialist will reach out to you shortly.",
    "account_access_issue": "Sorry you're locked out. Please DM us the email on your account — we'll help restore access.",
    "general_inquiry": "Thanks for contacting Uber Support! How can we help? DM us for account-specific assistance.",
}


class ReplyDrafter:
    def __init__(self, retriever: PrecedentRetriever) -> None:
        self.retriever = retriever

    def draft(self, text: str, intent: str) -> DraftResult:
        precedents = self.retriever.retrieve(text)
        best_sim = precedents[0].similarity if precedents else 0.0

        client = get_openai_client()
        if client is None:
            return self._demo_draft(text, intent, precedents, best_sim)

        user_prompt = f"""CUSTOMER MESSAGE:
\"\"\"
{text}
\"\"\"
CLASSIFIED INTENT: {intent}

RETRIEVED PRECEDENT THREADS:
{self.retriever.precedents_to_prompt_format(precedents)}"""

        try:
            data = call_llm(
                DRAFT_SYSTEM_PROMPT,
                user_prompt,
                temperature=LLM_TEMPERATURE_DRAFT,
                response_schema=DRAFT_SCHEMA,
            )
            return DraftResult(
                draft_reply=data["draft_reply"],
                grounding_quality=data["grounding_quality"],
                precedent_ids_used=data["precedent_ids_used"],
                reasoning=data["reasoning"],
                precedents=precedents,
            )
        except Exception as e:
            result = self._demo_draft(text, intent, precedents, best_sim)
            result.reasoning = f"LLM failed ({e}); template fallback"
            return result

    def _demo_draft(
        self,
        text: str,
        intent: str,
        precedents: list[Precedent],
        best_sim: float,
    ) -> DraftResult:
        if intent == "driver_unsafe_incident":
            reply = DEMO_TEMPLATES["driver_unsafe_incident"]
            gq = "none"
        elif best_sim >= RETRIEVAL_STRONG_THRESHOLD and precedents:
            # Adapt closest precedent tone
            reply = precedents[0].brand_reply[:280]
            gq = "strong"
        elif best_sim >= RETRIEVAL_WEAK_THRESHOLD and precedents:
            reply = DEMO_TEMPLATES.get(intent, DEMO_TEMPLATES["general_inquiry"])
            gq = "weak"
        else:
            reply = DEMO_TEMPLATES.get(intent, DEMO_TEMPLATES["general_inquiry"])
            gq = "none"

        ids = [p.id for p in precedents[:2]] if precedents and gq != "none" else []
        return DraftResult(
            draft_reply=reply,
            grounding_quality=gq,
            precedent_ids_used=ids,
            reasoning=f"Demo/template draft (best_sim={best_sim:.2f}, quality={gq})",
            precedents=precedents,
        )
