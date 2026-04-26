"""Compute gaps vs JD targets and surface high-leverage adjacent skills."""

from __future__ import annotations

import json

from utils.llm import generate_json
from utils.prompts import (
    GAP_ANALYZER_PROMPT,
    GAP_ANALYZER_SCHEMA,
    GAP_ANALYZER_SYSTEM,
)


def analyse_gaps(
    jd_skills: list[dict],
    resume_skills: list[dict],
    assessed: list[dict],
    jd_text: str,
) -> dict:
    """
    Args:
        jd_skills:     from skill_extractor (with target_level + importance)
        resume_skills: from skill_extractor (with claimed_level + evidence)
        assessed:      list of {skill, score: <scorer output>} we've assessed
        jd_text:       raw JD for context (truncated to keep prompt small)

    Returns dict with `primary_gaps` and `adjacent_skills`.
    """
    prompt = GAP_ANALYZER_PROMPT.format(
        jd_skills=json.dumps(jd_skills, indent=2),
        assessed_skills=json.dumps(_compact_assessed(assessed), indent=2),
        resume_skills=json.dumps(resume_skills, indent=2),
        jd_context=jd_text[:1500],
    )
    return generate_json(
        prompt,
        schema=GAP_ANALYZER_SCHEMA,
        system=GAP_ANALYZER_SYSTEM,
        temperature=0.4,
    )


def _compact_assessed(assessed: list[dict]) -> list[dict]:
    out = []
    for entry in assessed:
        score = entry["score"]
        out.append(
            {
                "skill": entry["skill"],
                "assessed_level": score["overall_level"],
                "confidence": score["confidence"],
                "rationale": score["rationale"],
            }
        )
    return out