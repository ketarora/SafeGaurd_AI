"""LLM-as-judge harness for reply quality scoring."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import OUTPUT_DIR
from src.utils import JUDGE_SCHEMA, call_llm, get_openai_client, save_json, setup_logging

JUDGE_SYSTEM_PROMPT = """You are scoring an AI-generated customer support reply against a rubric. Evaluate critically — do not default to high scores.

SCORE EACH DIMENSION 1-5:
1. CORRECTNESS: Does the reply address the issue? Are claims supported by precedents?
2. TONE: Professional, empathetic, matches Uber support tone?
3. ACTIONABILITY: Does the customer know what to do next?
4. ESCALATION-APPROPRIATENESS: Was auto_handle/escalate the right call? Score 1 if driver_unsafe_incident was auto-handled.

Also flag sounds_llm_generated: true if generic LLM phrasing is noticeable.

OUTPUT FORMAT (strict JSON):
{"correctness": 1-5, "tone": 1-5, "actionability": 1-5, "escalation_appropriateness": 1-5, "sounds_llm_generated": true/false, "overall_notes": "<1-2 sentences>"}"""


def rule_based_judge(row: dict, pipeline_output: dict) -> dict:
    """Demo-mode judge when no API key — heuristic scoring."""
    draft = pipeline_output.get("draft", {})
    esc = pipeline_output.get("escalation", {})
    reply = draft.get("draft_reply", "")
    gq = draft.get("grounding_quality", "none")
    intent = pipeline_output.get("classification", {}).get("intent", "")

    correctness = 4 if gq == "strong" else (3 if gq == "weak" else 2)
    tone = 3 if "DM us" in reply or "Sorry" in reply else 2
    actionability = 4 if "DM" in reply or "app" in reply.lower() else 2

    esc_decision = esc.get("decision", "escalate")
    true_esc = row.get("true_escalation_decision", "escalate")
    esc_ok = (esc_decision == true_esc)
    if intent == "driver_unsafe_incident" and esc_decision == "auto_handle":
        esc_score = 1
    else:
        esc_score = 5 if esc_ok else 2

    llm_phrases = ["I understand your frustration", "Thank you for reaching out", "We appreciate"]
    sounds_llm = any(p in reply for p in llm_phrases)

    return {
        "correctness": correctness,
        "tone": tone,
        "actionability": actionability,
        "escalation_appropriateness": esc_score,
        "sounds_llm_generated": sounds_llm,
        "overall_notes": f"Heuristic judge (demo mode): grounding={gq}, esc_match={esc_ok}",
    }


def llm_judge(row: dict, pipeline_output: dict) -> dict:
    user_prompt = json.dumps({
        "customer_message": row["text"],
        "true_intent": row.get("true_intent"),
        "true_escalation": row.get("true_escalation_decision"),
        "pipeline_output": pipeline_output,
    }, indent=2)

    return call_llm(
        JUDGE_SYSTEM_PROMPT,
        user_prompt,
        model=__import__("os").getenv("OPENAI_JUDGE_MODEL"),
        temperature=0.1,
        response_schema=JUDGE_SCHEMA,
    )


def run_judge(
    golden_path: Path,
    pipeline_log_path: Path,
    output_path: Path | None = None,
) -> pd.DataFrame:
    setup_logging()
    golden = pd.read_csv(golden_path)
    log_records = {}
    with pipeline_log_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            log_records[str(rec["tweet_id"])] = rec

    use_llm = get_openai_client() is not None
    results = []

    for _, row in golden.iterrows():
        tid = str(row["tweet_id"])
        if tid not in log_records:
            continue
        po = log_records[tid]
        try:
            if use_llm:
                scores = llm_judge(row.to_dict(), po)
            else:
                scores = rule_based_judge(row.to_dict(), po)
        except Exception as e:
            scores = rule_based_judge(row.to_dict(), po)
            scores["overall_notes"] = f"Judge error ({e}); heuristic fallback"

        results.append({"tweet_id": tid, **scores})

    df = pd.DataFrame(results)
    out = output_path or OUTPUT_DIR / "judge_scores.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    return df


def compute_agreement(judge_df: pd.DataFrame, golden: pd.DataFrame) -> dict:
    golden["tweet_id"] = golden["tweet_id"].astype(str)
    merged = judge_df.merge(golden, on="tweet_id", how="inner")

    # Human reference scores (if annotated in golden set)
    score_cols = ["correctness", "tone", "actionability", "escalation_appropriateness"]
    agreement = {}

    for col in score_cols:
        human_col = f"human_{col}"
        if human_col in merged.columns:
            diff = (merged[col] - merged[human_col]).abs()
            agreement[col] = {
                "mean_abs_error": round(diff.mean(), 2),
                "exact_match_pct": round((diff == 0).mean() * 100, 1),
                "within_1_pct": round((diff <= 1).mean() * 100, 1),
            }

    if "human_escalation_appropriate" in merged.columns:
        esc_match = (merged["escalation_appropriateness"] >= 4) == merged["human_escalation_appropriate"]
        agreement["escalation_binary"] = {"agreement_pct": round(esc_match.mean() * 100, 1)}

    return agreement


if __name__ == "__main__":
    golden_path = ROOT / "eval" / "golden_set.csv"
    log_path = OUTPUT_DIR / "eval_pipeline_log.jsonl"
    if not log_path.exists():
        log_path = OUTPUT_DIR / "golden_run.jsonl"
    if not log_path.exists():
        print("Run scripts/run_eval.py first to generate pipeline log")
        sys.exit(1)

    df = run_judge(golden_path, log_path)
    golden = pd.read_csv(golden_path)
    agreement = compute_agreement(df, golden)

    save_json(OUTPUT_DIR / "judge_agreement.json", agreement)
    print(f"Judge scores: {len(df)} examples")
    print(f"Agreement: {json.dumps(agreement, indent=2)}")
    print(f"Saved to {OUTPUT_DIR / 'judge_scores.csv'}")
