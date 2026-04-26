"""Skill extraction: JD + resume -> structured skill lists."""

from __future__ import annotations

from utils.llm import generate_json
from utils.prompts import (
    SKILL_EXTRACTOR_PROMPT,
    SKILL_EXTRACTOR_SCHEMA,
    SKILL_EXTRACTOR_SYSTEM,
)


def extract_skills(jd: str, resume: str) -> dict:
    """
    Returns:
        {
            "jd_skills": [{name, importance, target_level, category}, ...],
            "resume_skills": [{name, claimed_level, evidence}, ...]
        }
    """
    prompt = SKILL_EXTRACTOR_PROMPT.format(jd=jd.strip(), resume=resume.strip())
    return generate_json(
        prompt,
        schema=SKILL_EXTRACTOR_SCHEMA,
        system=SKILL_EXTRACTOR_SYSTEM,
        temperature=0.2,
    )


def merge_skills(jd_skills: list[dict], resume_skills: list[dict]) -> list[dict]:
    """
    For each JD skill, find the matching resume skill (case-insensitive name)
    and produce a merged record we can use to drive the assessment.
    """
    resume_by_name = {s["name"].lower(): s for s in resume_skills}
    merged = []
    for jd_skill in jd_skills:
        name = jd_skill["name"].lower()
        resume_match = resume_by_name.get(name)
        merged.append(
            {
                "name": name,
                "importance": jd_skill["importance"],
                "target_level": jd_skill["target_level"],
                "category": jd_skill.get("category", ""),
                "claimed_level": resume_match["claimed_level"] if resume_match else 0,
                "evidence": resume_match["evidence"] if resume_match else "Not on resume",
            }
        )
    return merged


def prioritise_for_assessment(merged: list[dict], max_skills: int = 6) -> list[dict]:
    """
    Pick which skills to actually assess. We don't have time to interview on
    everything - focus on must-haves, highest target levels first, with a
    preference for skills where the resume claim is close to the target.
    """

    def score(s: dict) -> float:
        importance_weight = 1.0 if s["importance"] == "must_have" else 0.4
        target = s["target_level"]
        gap = max(0, target - s["claimed_level"])
        gap_signal = 1.0 if gap <= 1 else 0.6
        return importance_weight * target * gap_signal

    return sorted(merged, key=score, reverse=True)[:max_skills]