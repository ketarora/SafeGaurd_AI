#!/usr/bin/env python3
"""Minimal CLI demo — input tweet → intent → precedent → draft → escalate."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.pipeline import SupportAgentPipeline
from src.utils import setup_logging

console = Console()


def display_result(output) -> None:
    d = output.to_dict()
    c = d["classification"]
    dr = d["draft"]
    e = d["escalation"]

    table = Table(title="Uber Support Agent — Pipeline Output", show_header=True)
    table.add_column("Stage", style="cyan")
    table.add_column("Output", style="white")

    table.add_row("Intent", f"{c['intent']} (confidence: {c['confidence']:.2f})")
    table.add_row("Reasoning", c["reasoning"])
    table.add_row("Grounding", dr["grounding_quality"])
    table.add_row("Precedents", ", ".join(dr["precedent_ids_used"]) or "(none)")
    table.add_row("Draft Reply", dr["draft_reply"])
    table.add_row(
        "Escalation",
        f"[{'red' if e['decision'] == 'escalate' else 'green'}]{e['decision']}[/] — {e['reason']}",
    )
    if e["hard_rule_triggered"]:
        table.add_row("⚠ Hard Rule", "Safety guardrail triggered — cannot auto-handle")

    console.print(table)

    if dr.get("precedents"):
        console.print("\n[bold]Retrieved Precedents:[/]")
        for p in dr["precedents"][:3]:
            console.print(Panel(
                f"Similarity: {p['similarity']:.3f}\nReply: {p['brand_reply']}",
                title=p["id"],
            ))


def main() -> None:
    setup_logging()
    console.print("[bold blue]Uber AI Support Agent — Demo CLI[/]")
    console.print("Type a customer message (or 'quit' to exit)\n")

    pipeline = SupportAgentPipeline(classifier_name="llm")

    if len(sys.argv) > 1:
        # Single-shot mode: python demo/cli.py "your message here"
        text = " ".join(sys.argv[1:])
        result = pipeline.process(text)
        display_result(result)
        return

    while True:
        try:
            text = console.input("[bold green]Customer message:[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if text.lower() in ("quit", "exit", "q"):
            break
        if not text:
            continue
        result = pipeline.process(text)
        display_result(result)
        console.print()


if __name__ == "__main__":
    main()
