# 🎯 AI-Powered Skill Assessment & Personalised Learning Plan Agent

> A resume tells you what someone *claims* to know — not how well they actually know it.
> This agent takes a Job Description and a candidate's resume, runs a short adaptive interview to assess real proficiency on each required skill, identifies gaps, and generates a personalised learning plan focused on adjacent skills the candidate can realistically acquire — with curated resources and time estimates.

Built for **Catalyst** · Stack: Streamlit + Python + Google Gemini

## ✨ What it does

1. **Skill extraction** — Parses the JD into `{skill, target_level, importance}` and the resume into `{skill, claimed_level, evidence}`.
2. **Adaptive conversational assessment** — For each prioritised must-have skill, runs a short interview (1–3 turns). Difficulty adapts to the candidate's previous answers.
3. **Rubric-based scoring** — Scores each conversation on 4 sub-dimensions (conceptual, applied, vocabulary, edge-cases) → an overall 0–4 proficiency level with a confidence score.
4. **Gap + adjacency analysis** — Computes priority-ranked primary gaps and surfaces *adjacent* skills the candidate is close to acquiring (with rationale grounded in their existing skills).
5. **Personalised learning plan** — For each gap and adjacent skill: 2–4 curated resources, weekly hours, estimated weeks, capstone project, and a phased 12-week sequence.
6. **Downloadable JSON report** of the full assessment.

## 🚀 Quick start (local, ~2 minutes)

### Prerequisites
- Python 3.10+
- A free Gemini API key (no credit card needed): <https://aistudio.google.com/app/apikey>

### Setup
```bash
git clone <your-repo-url>
cd skill-agent
python -m venv .venv

# Mac/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Create .env with your key:
echo GEMINI_API_KEY=your_key_here > .env

streamlit run app.py
```

The app opens at <http://localhost:8501>.

### Try it without your own JD/resume
On the inputs screen, click **"Use sample JD"** and **"Use sample resume"** to load a realistic Senior Backend Engineer pairing.

## 🏗️ Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full diagram and component breakdown.

```
JD + Resume
   │
   ▼
[Skill Extractor]  →  jd_skills, resume_skills (structured JSON)
   │
   ▼
[Prioritiser]      →  top-N skills queued for interview
   │
   ▼
[Assessor]         →  adaptive 1–3 turn conversation per skill
   │
   ▼
[Scorer]           →  rubric-based 0-4 level + sub-dimension scores
   │
   ▼
[Gap Analyzer]     →  primary_gaps + adjacent_skills
   │
   ▼
[Learning Plan]    →  curated resources, time estimates, 12-wk sequence
```

## 🧮 Scoring logic

**Per-skill proficiency — 0-4 scale:**

| Level | Meaning |
|---|---|
| 0 | No knowledge |
| 1 | Familiar — knows definitions |
| 2 | Working — can apply, knows basic patterns |
| 3 | Proficient — discusses tradeoffs, edge cases, debugging instincts |
| 4 | Expert — architectural reasoning, anticipates failure modes |

**Each interview is scored on 4 sub-dimensions** (each 0-4): `conceptual`, `applied`, `vocabulary`, `edge_cases`. The overall level is the floor of the average, with a ±1 adjustment allowed for exceptional strength or weakness in one dimension.

**Gap priority** = `(target_level − assessed_level) × importance_weight`, where `importance_weight` is 1.0 for must-haves and 0.5 for nice-to-haves.

**Adjacent skill ranking** is qualitative, based on:
- *Leverage from existing skills* — what the candidate already demonstrates
- *Relevance to the role* — matched against the JD context
- *Honest weeks-to-basic estimate* given prerequisites

The differentiator vs. a generic skill-gap tool: every adjacent recommendation comes with a "you already know X and Y, so Z is roughly N weeks away" rationale.

## 📁 Project structure

```
skill-agent/
├── app.py                      # Streamlit UI + orchestration
├── agents/
│   ├── skill_extractor.py      # JD + resume → structured skill lists
│   ├── assessor.py             # adaptive conversational interviewer
│   ├── scorer.py               # rubric-based scoring engine
│   ├── gap_analyzer.py         # primary gaps + adjacent skills
│   └── learning_plan.py        # curated resources + sequenced plan
├── utils/
│   ├── llm.py                  # Gemini SDK wrapper (swappable provider)
│   ├── parsing.py              # PDF/text resume parsing
│   └── prompts.py              # all LLM prompts + JSON schemas
├── samples/
│   ├── sample_jd.txt
│   ├── sample_resume.txt
│   └── sample_output.json
├── docs/
│   └── ARCHITECTURE.md
├── requirements.txt
└── README.md
```

## 🔁 Swapping LLM providers

All LLM calls go through `utils/llm.py`. To swap to Claude or OpenAI:
1. Replace `generate_text` and `generate_json`.
2. Update `requirements.txt`.
3. Adjust the JSON schema syntax if the new provider expects a different format.

The agent code in `agents/*.py` is provider-agnostic.

## ⚠️ Free-tier note

Gemini 2.5 Flash on the free tier currently allows ~10 requests/minute. A full assessment uses ~15–30 calls — fine for the daily quota, but the LLM wrapper handles 429s with exponential backoff in case you hit RPM limits.

## License

MIT