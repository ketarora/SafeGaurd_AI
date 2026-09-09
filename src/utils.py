"""Shared utilities for the Uber Support Agent pipeline."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from jsonschema import ValidationError, validate

load_dotenv()

logger = logging.getLogger("uber_support_agent")


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def get_openai_client():
    """Return OpenAI client if API key is set, else None (demo mode)."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-your"):
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except Exception as e:
        logger.warning("OpenAI client unavailable: %s", e)
        return None


def call_llm(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
    response_schema: dict | None = None,
) -> dict[str, Any]:
    """Call OpenAI chat completion and parse JSON response."""
    client = get_openai_client()
    if client is None:
        raise RuntimeError("OPENAI_API_KEY not configured — use demo/rule-based paths")

    model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if response_schema:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    raw = response.choices[0].message.content or "{}"
    return parse_json_response(raw, response_schema)


def parse_json_response(raw: str, schema: dict | None = None) -> dict[str, Any]:
    """Extract and validate JSON from LLM output."""
    text = raw.strip()
    # Strip markdown fences if present
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence_match:
        text = fence_match.group(1).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find first JSON object
        obj_match = re.search(r"\{[\s\S]*\}", text)
        if not obj_match:
            raise ValueError(f"Could not parse JSON from LLM output: {raw[:200]}")
        data = json.loads(obj_match.group())

    if schema:
        try:
            validate(instance=data, schema=schema)
        except ValidationError as e:
            raise ValueError(f"JSON schema validation failed: {e.message}") from e
    return data


def detect_safety_keywords(text: str, keywords: list[str]) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in keywords)


def detect_sentiment(text: str) -> str:
    """Simple rule-based sentiment for escalation signals."""
    lower = text.lower()
    angry_markers = [
        "!!!", "wtf", "fuck", "scam", "fraud", "worst", "never again",
        "disgusting", "unacceptable", "lawyer", "sue", "report you",
    ]
    negative_markers = [
        "disappointed", "frustrated", "unhappy", "not happy", "terrible",
        "awful", "ridiculous", "still waiting", "no response",
    ]
    if any(m in lower for m in angry_markers):
        return "angry"
    if any(m in lower for m in negative_markers):
        return "negative"
    return "neutral"


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# JSON schemas for pipeline stage outputs
CLASSIFY_SCHEMA = {
    "type": "object",
    "required": ["intent", "confidence", "reasoning"],
    "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "reasoning": {"type": "string"},
    },
}

DRAFT_SCHEMA = {
    "type": "object",
    "required": ["draft_reply", "grounding_quality", "precedent_ids_used", "reasoning"],
    "properties": {
        "draft_reply": {"type": "string"},
        "grounding_quality": {"type": "string", "enum": ["strong", "weak", "none"]},
        "precedent_ids_used": {"type": "array", "items": {"type": "string"}},
        "reasoning": {"type": "string"},
    },
}

ESCALATE_SCHEMA = {
    "type": "object",
    "required": ["decision", "reason", "risk_if_wrong"],
    "properties": {
        "decision": {"type": "string", "enum": ["auto_handle", "escalate"]},
        "reason": {"type": "string"},
        "risk_if_wrong": {"type": "string"},
    },
}

JUDGE_SCHEMA = {
    "type": "object",
    "required": [
        "correctness", "tone", "actionability", "escalation_appropriateness",
        "sounds_llm_generated", "overall_notes",
    ],
    "properties": {
        "correctness": {"type": "integer", "minimum": 1, "maximum": 5},
        "tone": {"type": "integer", "minimum": 1, "maximum": 5},
        "actionability": {"type": "integer", "minimum": 1, "maximum": 5},
        "escalation_appropriateness": {"type": "integer", "minimum": 1, "maximum": 5},
        "sounds_llm_generated": {"type": "boolean"},
        "overall_notes": {"type": "string"},
    },
}
