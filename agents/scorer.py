"""Score per-skill conversations against a fixed rubric."""

from __future__ import annotations

from utils.llm import generate_json
from utils.prompts import SCORER_PROMPT, SCORER_SCHEMA, SCORER_SYSTEM


def score_skill(skill: str, history: list[dict]) -> dict:
    """
    Returns {
        overall_level: int,
        conceptual: int, applied: int, vocabulary: int, edge_cases: int,
        confidence: float, rationale: str
    }
    """
    transcript = _format_transcript(history)
    prompt = SCORER_PROMPT.format(skill=skill, transcript=transcript)
    return generate_json(
        prompt,
        schema=SCORER_SCHEMA,
        system=SCORER_SYSTEM,
        temperature=0.1,
    )


def _format_transcript(history: list[dict]) -> str:
    lines = []
    for entry in history:
        role = "Interviewer" if entry["role"] == "interviewer" else "Candidate"
        lines.append(f"{role}: {entry['text']}")
    return "\n\n".join(lines)