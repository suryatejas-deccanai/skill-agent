"""
All LLM prompts in one place. Keeping them centralised makes them easier to
tune and inspect during the demo, and avoids surprises from copies drifting
out of sync.
"""

# ---------------------------------------------------------------------------
# 1. Skill extraction
# ---------------------------------------------------------------------------

SKILL_EXTRACTOR_SYSTEM = """You are a senior technical recruiter and skills taxonomist.
You extract skills from job descriptions and resumes with high precision and
no hallucination. You distinguish must-have skills from nice-to-haves, and
you map free-form text to canonical, lowercase skill names (e.g. "ReactJS"
and "React.js" both -> "react").
"""

SKILL_EXTRACTOR_PROMPT = """Extract skills from the following Job Description and Resume.

For the JD, return each required skill with:
- name (canonical, lowercase, e.g. "react", "python", "system design")
- importance: "must_have" | "nice_to_have"
- target_level: 1..4 (1=familiar, 2=working, 3=proficient, 4=expert)
- category: "language" | "framework" | "tool" | "concept" | "soft" | "domain"

For the Resume, return each demonstrated skill with:
- name (canonical, lowercase, matching JD names where the underlying skill is the same)
- claimed_level: 1..4 (your honest read of the resume's evidence)
- evidence: short quote or summary of where it appears in the resume

Skip generic filler ("communication", "team player") unless the JD specifically calls it out.
Skip deprecated/legacy tech that isn't actually demanded.

JOB DESCRIPTION:
---
{jd}
---

RESUME:
---
{resume}
---
"""

SKILL_EXTRACTOR_SCHEMA = {
    "type": "OBJECT",
    "required": ["jd_skills", "resume_skills"],
    "properties": {
        "jd_skills": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["name", "importance", "target_level", "category"],
                "properties": {
                    "name": {"type": "STRING"},
                    "importance": {"type": "STRING", "enum": ["must_have", "nice_to_have"]},
                    "target_level": {"type": "INTEGER"},
                    "category": {"type": "STRING"},
                },
            },
        },
        "resume_skills": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["name", "claimed_level", "evidence"],
                "properties": {
                    "name": {"type": "STRING"},
                    "claimed_level": {"type": "INTEGER"},
                    "evidence": {"type": "STRING"},
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# 2. Conversational assessment
# ---------------------------------------------------------------------------

ASSESSOR_SYSTEM = """You are a calm, encouraging technical interviewer.
Your job is to assess a candidate's real proficiency in a specific skill through
short, conversational questions, NOT a quiz.

Style rules:
- Ask ONE question at a time. Keep it under 3 sentences.
- Adapt difficulty to the candidate's previous answers. If they nail a basic
  question, escalate (applied scenario, edge cases, debugging). If they struggle,
  step down to fundamentals or pivot to an adjacent angle.
- Don't grade out loud. Don't say "correct" or "wrong" - just continue.
- Stay encouraging. The goal is signal, not intimidation.
"""

ASSESSOR_QUESTION_PROMPT = """SKILL UNDER ASSESSMENT: {skill}
TARGET LEVEL FOR THE ROLE: {target_level} (1=familiar, 4=expert)
CANDIDATE'S CLAIMED LEVEL: {claimed_level}

CONVERSATION SO FAR:
{history}

Generate the NEXT question. Rules:
- Turn 1: a conceptual opener that maps to the candidate's claimed level.
- Turn 2+: adapt based on the previous answer's depth. Aim to confirm or challenge
  the current proficiency estimate.
- If you've already gathered strong signal (3 turns or a clearly definitive answer),
  output the literal token "<<DONE>>" instead of a question.

Output ONLY the next question text, or "<<DONE>>". No preamble, no labels.
"""


# ---------------------------------------------------------------------------
# 3. Per-skill scoring
# ---------------------------------------------------------------------------

SCORER_SYSTEM = """You are a fair, calibrated technical evaluator.
You score candidate answers on a 0-4 proficiency scale using a fixed rubric.
You explain your reasoning briefly so a human can audit your call.
"""

SCORER_PROMPT = """Score the candidate's proficiency in this skill based on the
conversation below. Use this rubric:

0 = No knowledge / blank / off-topic
1 = Familiar - knows definitions, can recognise the concept
2 = Working - can apply it in straightforward cases, knows basic patterns
3 = Proficient - discusses tradeoffs, edge cases, debugging instincts
4 = Expert - architectural reasoning, can teach, anticipates failure modes

Score on FOUR sub-dimensions (0-4 each):
- conceptual: clarity of mental model
- applied: ability to use it in real scenarios
- vocabulary: precision and correctness of terminology
- edge_cases: awareness of failure modes, tradeoffs, gotchas

Then give an OVERALL level (0-4) - usually the floor of the average, but
you may adjust +/-1 if one dimension is exceptionally strong or weak.

Also estimate `confidence` (0.0-1.0) based on how much signal you got.

SKILL: {skill}
CONVERSATION:
{transcript}
"""

SCORER_SCHEMA = {
    "type": "OBJECT",
    "required": ["overall_level", "conceptual", "applied", "vocabulary", "edge_cases", "confidence", "rationale"],
    "properties": {
        "overall_level": {"type": "INTEGER"},
        "conceptual": {"type": "INTEGER"},
        "applied": {"type": "INTEGER"},
        "vocabulary": {"type": "INTEGER"},
        "edge_cases": {"type": "INTEGER"},
        "confidence": {"type": "NUMBER"},
        "rationale": {"type": "STRING"},
    },
}


# ---------------------------------------------------------------------------
# 4. Gap + adjacent skill analysis
# ---------------------------------------------------------------------------

GAP_ANALYZER_SYSTEM = """You are a career coach who specialises in pragmatic
upskilling plans. You identify the highest-leverage gaps and the adjacent
skills that a candidate is closest to acquiring, given what they already know.
"""

GAP_ANALYZER_PROMPT = """Analyse the candidate's skill profile and produce two lists:

1. PRIMARY GAPS - required skills (must_have) where assessed level < target level.
   For each, compute priority = (target_level - assessed_level) * importance_weight,
   where importance_weight is 1.0 for must_have and 0.5 for nice_to_have.

2. ADJACENT SKILLS - up to 5 skills that are NOT directly listed in the JD but
   are highly relevant to the role AND are within close reach given what the
   candidate already demonstrates. For each, explain why it's adjacent:
   "you already know X and Y, so Z is roughly N weeks away."

Be honest about feasibility. Don't recommend things that require huge prerequisite
jumps. Bias toward adjacencies that compound the candidate's existing strengths.

JD SKILLS (with target levels):
{jd_skills}

CANDIDATE ASSESSMENT (with assessed levels):
{assessed_skills}

CANDIDATE'S DEMONSTRATED SKILLS FROM RESUME:
{resume_skills}

ROLE CONTEXT (from JD):
{jd_context}
"""

GAP_ANALYZER_SCHEMA = {
    "type": "OBJECT",
    "required": ["primary_gaps", "adjacent_skills"],
    "properties": {
        "primary_gaps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["skill", "current_level", "target_level", "priority", "rationale"],
                "properties": {
                    "skill": {"type": "STRING"},
                    "current_level": {"type": "INTEGER"},
                    "target_level": {"type": "INTEGER"},
                    "priority": {"type": "NUMBER"},
                    "rationale": {"type": "STRING"},
                },
            },
        },
        "adjacent_skills": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["skill", "leverage_from", "weeks_to_basic", "why_relevant"],
                "properties": {
                    "skill": {"type": "STRING"},
                    "leverage_from": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                    "weeks_to_basic": {"type": "NUMBER"},
                    "why_relevant": {"type": "STRING"},
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# 5. Learning plan
# ---------------------------------------------------------------------------

LEARNING_PLAN_SYSTEM = """You are a curriculum designer who builds realistic,
sequenced learning plans for working professionals. You recommend a mix of
high-quality free resources (official docs, well-known courses, books, hands-on
projects). You give honest time estimates assuming ~5-7 hours/week of study.
"""

LEARNING_PLAN_PROMPT = """Build a personalised learning plan for the candidate.

Cover:
- Each PRIMARY GAP (in priority order) - close the gap from current_level to target_level.
- Each ADJACENT SKILL - get to a working level (level 2).

For each item, provide:
- 2-4 curated resources (mix of types: course, docs, book, project). Prefer free or
  widely available. Use real, well-known resources you are confident exist
  (e.g. "FastAPI official tutorial", "Designing Data-Intensive Applications").
  Do NOT invent URLs or course names.
- A weekly_hours suggestion (3-8).
- An estimated_weeks to reach the target level.
- A capstone project idea that proves the skill.

Then propose a SEQUENCE - which order to tackle items in, and roughly how the
weeks lay out across the next 12 weeks (assuming the candidate can run 1-2 tracks
in parallel).

PRIMARY GAPS:
{primary_gaps}

ADJACENT SKILLS:
{adjacent_skills}

CANDIDATE CONTEXT:
{candidate_context}
"""

LEARNING_PLAN_SCHEMA = {
    "type": "OBJECT",
    "required": ["items", "sequence", "total_weeks"],
    "properties": {
        "items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["skill", "kind", "current_level", "target_level", "resources", "weekly_hours", "estimated_weeks", "capstone"],
                "properties": {
                    "skill": {"type": "STRING"},
                    "kind": {"type": "STRING", "enum": ["gap", "adjacent"]},
                    "current_level": {"type": "INTEGER"},
                    "target_level": {"type": "INTEGER"},
                    "resources": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "required": ["title", "type", "why"],
                            "properties": {
                                "title": {"type": "STRING"},
                                "type": {"type": "STRING", "enum": ["course", "docs", "book", "project", "video", "article"]},
                                "why": {"type": "STRING"},
                            },
                        },
                    },
                    "weekly_hours": {"type": "NUMBER"},
                    "estimated_weeks": {"type": "NUMBER"},
                    "capstone": {"type": "STRING"},
                },
            },
        },
        "sequence": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["weeks", "focus", "skills"],
                "properties": {
                    "weeks": {"type": "STRING"},
                    "focus": {"type": "STRING"},
                    "skills": {
                        "type": "ARRAY",
                        "items": {"type": "STRING"},
                    },
                },
            },
        },
        "total_weeks": {"type": "NUMBER"},
    },
}