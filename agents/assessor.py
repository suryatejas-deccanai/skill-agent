"""Conversational assessment: adaptive questions per skill."""

from __future__ import annotations

from utils.llm import generate_text
from utils.prompts import ASSESSOR_QUESTION_PROMPT, ASSESSOR_SYSTEM

DONE_TOKEN = "<<DONE>>"
MAX_TURNS_PER_SKILL = 3


def next_question(
    skill: str,
    target_level: int,
    claimed_level: int,
    history: list[dict],
) -> str:
    """
    Generate the next interview question for `skill`, given the conversation so far.

    `history` is a list of {"role": "interviewer"|"candidate", "text": ...}.
    Returns the question text, or DONE_TOKEN when we have enough signal.
    """
    if len(history) >= MAX_TURNS_PER_SKILL * 2:
        return DONE_TOKEN

    history_text = (
        _format_history(history)
        if history
        else "(no conversation yet - this is the first question)"
    )
    prompt = ASSESSOR_QUESTION_PROMPT.format(
        skill=skill,
        target_level=target_level,
        claimed_level=claimed_level,
        history=history_text,
    )
    out = generate_text(prompt, system=ASSESSOR_SYSTEM, temperature=0.5)
    return out.strip()


def _format_history(history: list[dict]) -> str:
    lines = []
    for entry in history:
        role = "Q" if entry["role"] == "interviewer" else "A"
        lines.append(f"{role}: {entry['text']}")
    return "\n".join(lines)