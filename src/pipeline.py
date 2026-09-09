"""End-to-end pipeline orchestrating all 3 stages."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from src.classify import ClassificationResult, LLMClassifier, get_classifier
from src.config import OUTPUT_DIR
from src.draft import DraftResult, ReplyDrafter
from src.escalate import EscalationDecider, EscalationResult
from src.retrieve import PrecedentRetriever
from src.utils import append_jsonl, detect_sentiment, setup_logging

logger = __import__("logging").getLogger("uber_support_agent")


@dataclass
class PipelineOutput:
    tweet_id: str
    text: str
    thread_context: str
    classification: ClassificationResult
    draft: DraftResult
    escalation: EscalationResult
    sentiment_flag: str

    def to_dict(self) -> dict:
        return {
            "tweet_id": self.tweet_id,
            "text": self.text,
            "thread_context": self.thread_context,
            "classification": {
                "intent": self.classification.intent,
                "confidence": self.classification.confidence,
                "reasoning": self.classification.reasoning,
                "classifier": self.classification.classifier,
            },
            "draft": {
                "draft_reply": self.draft.draft_reply,
                "grounding_quality": self.draft.grounding_quality,
                "precedent_ids_used": self.draft.precedent_ids_used,
                "reasoning": self.draft.reasoning,
                "precedents": [
                    {"id": p.id, "similarity": p.similarity, "brand_reply": p.brand_reply[:100]}
                    for p in self.draft.precedents
                ],
            },
            "escalation": {
                "decision": self.escalation.decision,
                "reason": self.escalation.reason,
                "risk_if_wrong": self.escalation.risk_if_wrong,
                "hard_rule_triggered": self.escalation.hard_rule_triggered,
            },
            "sentiment_flag": self.sentiment_flag,
        }


class SupportAgentPipeline:
    def __init__(
        self,
        classifier_name: str = "llm",
        retriever: PrecedentRetriever | None = None,
    ) -> None:
        self.classifier = get_classifier(classifier_name)  # type: ignore[arg-type]
        self.retriever = retriever or PrecedentRetriever.from_processed()
        self.drafter = ReplyDrafter(self.retriever)
        self.escalator = EscalationDecider()

    def process(
        self,
        text: str,
        tweet_id: str = "manual",
        thread_context: str = "",
        repeat_contact_flag: bool = False,
    ) -> PipelineOutput:
        sentiment = detect_sentiment(text)
        classification = self.classifier.classify(text, thread_context)
        draft = self.drafter.draft(text, classification.intent)
        escalation = self.escalator.decide(
            text=text,
            intent=classification.intent,
            intent_confidence=classification.confidence,
            draft_reply=draft.draft_reply,
            grounding_quality=draft.grounding_quality,
            sentiment_flag=sentiment,
            repeat_contact_flag=repeat_contact_flag,
        )
        return PipelineOutput(
            tweet_id=tweet_id,
            text=text,
            thread_context=thread_context,
            classification=classification,
            draft=draft,
            escalation=escalation,
            sentiment_flag=sentiment,
        )

    def process_batch(
        self,
        examples: list[dict],
        log_path: Path | None = None,
    ) -> list[PipelineOutput]:
        outputs = []
        log_path = log_path or OUTPUT_DIR / "pipeline_log.jsonl"
        if log_path.exists():
            log_path.unlink()

        for i, ex in enumerate(examples):
            out = self.process(
                text=ex["text"],
                tweet_id=ex.get("tweet_id", f"ex_{i}"),
                thread_context=ex.get("thread_context", ""),
                repeat_contact_flag=ex.get("repeat_contact_flag", False),
            )
            outputs.append(out)
            append_jsonl(log_path, out.to_dict())
        return outputs


def run_on_golden_set(
    golden_path: Path,
    classifier: str = "llm",
    output_dir: Path | None = None,
) -> list[PipelineOutput]:
    setup_logging()
    df = pd.read_csv(golden_path)
    examples = df.to_dict("records")
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    pipeline = SupportAgentPipeline(classifier_name=classifier)
    return pipeline.process_batch(examples, log_path=out_dir / "golden_run.jsonl")
