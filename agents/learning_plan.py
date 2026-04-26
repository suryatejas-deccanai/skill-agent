"""Generate a personalised learning plan with curated resources + time estimates."""

from __future__ import annotations

import json

from utils.llm import generate_json
from utils.prompts import (
    LEARNING_PLAN_PROMPT,
    LEARNING_PLAN_SCHEMA,
    LEARNING_PLAN_SYSTEM,
)


def build_plan(
    primary_gaps: list[dict],
    adjacent_skills: list[dict],
    candidate_context: str = "",
) -> dict:
    """
    Returns dict with:
        items: per-skill learning items (resources, weekly hours, weeks, capstone)
        sequence: 12-week-ish phased plan
        total_weeks: float
    """
    prompt = LEARNING_PLAN_PROMPT.format(
        primary_gaps=json.dumps(primary_gaps, indent=2),
        adjacent_skills=json.dumps(adjacent_skills, indent=2),
        candidate_context=candidate_context or "(no extra context)",
    )
    return generate_json(
        prompt,
        schema=LEARNING_PLAN_SCHEMA,
        system=LEARNING_PLAN_SYSTEM,
        temperature=0.5,
    )