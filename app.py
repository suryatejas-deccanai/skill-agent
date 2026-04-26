"""
Streamlit app: AI-Powered Skill Assessment & Personalised Learning Plan Agent.

Run locally:
    streamlit run app.py

Make sure GEMINI_API_KEY is set in .env (see .env.example).
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from agents import assessor, gap_analyzer, learning_plan, scorer, skill_extractor
from utils.parsing import extract_resume_text

load_dotenv()

st.set_page_config(
    page_title="Skill Assessment Agent",
    page_icon="🎯",
    layout="wide",
)


# ---------------------------------------------------------------------------
# Session-state helpers
# ---------------------------------------------------------------------------

DEFAULTS = {
    "step": "input",
    "jd_text": "",
    "resume_text": "",
    "extracted": None,
    "merged": None,
    "to_assess": [],
    "current_skill_idx": 0,
    "histories": {},
    "scores": {},
    "current_question": None,
    "gaps": None,
    "plan": None,
}


def init_state() -> None:
    for k, v in DEFAULTS.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset() -> None:
    for k in DEFAULTS:
        st.session_state.pop(k, None)
    init_state()


init_state()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🎯 Skill Assessment & Learning Plan Agent")
st.caption(
    "Upload a resume + paste a JD. The agent runs a short adaptive interview, "
    "scores real proficiency, identifies gaps, and builds a personalised plan."
)

with st.sidebar:
    st.subheader("Progress")
    steps = ["1. Inputs", "2. Skills extracted", "3. Assessment", "4. Plan"]
    step_map = {"input": 0, "extracted": 1, "assessing": 2, "done": 3}
    current = step_map.get(st.session_state.step, 0)
    for i, s in enumerate(steps):
        marker = "🟢" if i < current else ("🔵" if i == current else "⚪")
        st.write(f"{marker} {s}")
    st.divider()
    if st.button("🔄 Start over", use_container_width=True):
        reset()
        st.rerun()
    st.caption("Powered by Gemini 2.5 Flash · Free tier")


# ---------------------------------------------------------------------------
# Step 1 - Inputs
# ---------------------------------------------------------------------------

if st.session_state.step == "input":
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Job Description")
        st.session_state.jd_text = st.text_area(
            "Paste the JD",
            value=st.session_state.jd_text,
            height=300,
            label_visibility="collapsed",
        )
        if st.button("Use sample JD"):
            sample = Path("samples/sample_jd.txt")
            if sample.exists():
                st.session_state.jd_text = sample.read_text(encoding="utf-8")
                st.rerun()

    with col2:
        st.subheader("Candidate Resume")
        uploaded = st.file_uploader(
            "Upload resume (PDF / TXT / MD)",
            type=["pdf", "txt", "md"],
            label_visibility="collapsed",
        )
        if uploaded is not None:
            st.session_state.resume_text = extract_resume_text(uploaded)
            st.success(f"Loaded {len(st.session_state.resume_text)} chars from {uploaded.name}")

        st.session_state.resume_text = st.text_area(
            "Or paste resume text",
            value=st.session_state.resume_text,
            height=200,
        )
        if st.button("Use sample resume"):
            sample = Path("samples/sample_resume.txt")
            if sample.exists():
                st.session_state.resume_text = sample.read_text(encoding="utf-8")
                st.rerun()

    st.divider()

    can_proceed = bool(st.session_state.jd_text.strip()) and bool(
        st.session_state.resume_text.strip()
    )
    if st.button("🔍 Extract skills", type="primary", disabled=not can_proceed):
        with st.spinner("Extracting skills from JD and resume..."):
            extracted = skill_extractor.extract_skills(
                st.session_state.jd_text, st.session_state.resume_text
            )
            merged = skill_extractor.merge_skills(
                extracted["jd_skills"], extracted["resume_skills"]
            )
            st.session_state.extracted = extracted
            st.session_state.merged = merged
            st.session_state.to_assess = skill_extractor.prioritise_for_assessment(
                merged, max_skills=6
            )
            st.session_state.step = "extracted"
        st.rerun()


# ---------------------------------------------------------------------------
# Step 2 - Confirm extracted skills
# ---------------------------------------------------------------------------

if st.session_state.step == "extracted":
    st.subheader("📋 Extracted skills")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**From the JD**")
        st.dataframe(
            st.session_state.extracted["jd_skills"],
            use_container_width=True,
            hide_index=True,
        )
    with col2:
        st.markdown("**From the resume**")
        st.dataframe(
            st.session_state.extracted["resume_skills"],
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("🎤 Skills queued for assessment")
    st.caption(
        "We prioritise must-haves and skills where the resume claim is close to "
        "the target - those are the most informative interviews."
    )
    st.dataframe(
        st.session_state.to_assess,
        use_container_width=True,
        hide_index=True,
    )

    if st.button("🚀 Start assessment", type="primary"):
        st.session_state.step = "assessing"
        st.session_state.current_question = None
        st.rerun()


# ---------------------------------------------------------------------------
# Step 3 - Conversational assessment
# ---------------------------------------------------------------------------

if st.session_state.step == "assessing":
    queue = st.session_state.to_assess
    idx = st.session_state.current_skill_idx

    if idx >= len(queue):
        with st.spinner("Analysing gaps and adjacent skills..."):
            assessed = [
                {"skill": s, "score": st.session_state.scores[s]}
                for s in st.session_state.scores
            ]
            st.session_state.gaps = gap_analyzer.analyse_gaps(
                jd_skills=st.session_state.extracted["jd_skills"],
                resume_skills=st.session_state.extracted["resume_skills"],
                assessed=assessed,
                jd_text=st.session_state.jd_text,
            )
        with st.spinner("Building your personalised learning plan..."):
            st.session_state.plan = learning_plan.build_plan(
                primary_gaps=st.session_state.gaps["primary_gaps"],
                adjacent_skills=st.session_state.gaps["adjacent_skills"],
                candidate_context=st.session_state.resume_text[:1500],
            )
            st.session_state.step = "done"
        st.rerun()

    skill = queue[idx]
    skill_name = skill["name"]
    history = st.session_state.histories.setdefault(skill_name, [])

    st.subheader(f"Skill {idx + 1}/{len(queue)}: `{skill_name}`")
    st.caption(
        f"Target level: {skill['target_level']}/4 · Resume claim: {skill['claimed_level']}/4 · {skill['importance']}"
    )
    st.progress((idx) / len(queue))

    if st.session_state.current_question is None and not history:
        with st.spinner("Thinking of a good opening question..."):
            q = assessor.next_question(
                skill=skill_name,
                target_level=skill["target_level"],
                claimed_level=skill["claimed_level"],
                history=history,
            )
        st.session_state.current_question = q

    for entry in history:
        with st.chat_message("assistant" if entry["role"] == "interviewer" else "user"):
            st.write(entry["text"])

    if st.session_state.current_question and st.session_state.current_question != assessor.DONE_TOKEN:
        with st.chat_message("assistant"):
            st.write(st.session_state.current_question)

        answer = st.chat_input("Your answer (or type 'skip' if you don't know)")
        if answer:
            history.append({"role": "interviewer", "text": st.session_state.current_question})
            history.append({"role": "candidate", "text": answer})
            st.session_state.current_question = None

            with st.spinner("Thinking..."):
                next_q = assessor.next_question(
                    skill=skill_name,
                    target_level=skill["target_level"],
                    claimed_level=skill["claimed_level"],
                    history=history,
                )
            st.session_state.current_question = next_q
            st.rerun()

    if st.session_state.current_question == assessor.DONE_TOKEN:
        with st.spinner(f"Scoring {skill_name}..."):
            st.session_state.scores[skill_name] = scorer.score_skill(skill_name, history)
        st.session_state.current_skill_idx += 1
        st.session_state.current_question = None
        st.rerun()

    if st.button("Skip this skill"):
        if history:
            with st.spinner(f"Scoring {skill_name}..."):
                st.session_state.scores[skill_name] = scorer.score_skill(skill_name, history)
        else:
            st.session_state.scores[skill_name] = {
                "overall_level": 0,
                "conceptual": 0,
                "applied": 0,
                "vocabulary": 0,
                "edge_cases": 0,
                "confidence": 0.3,
                "rationale": "Skill skipped without assessment.",
            }
        st.session_state.current_skill_idx += 1
        st.session_state.current_question = None
        st.rerun()


# ---------------------------------------------------------------------------
# Step 4 - Results
# ---------------------------------------------------------------------------

if st.session_state.step == "done":
    st.success("✅ Assessment complete")

    st.subheader("📊 Skill scorecard")
    rows = []
    for skill in st.session_state.merged:
        score = st.session_state.scores.get(skill["name"])
        rows.append(
            {
                "skill": skill["name"],
                "target": skill["target_level"],
                "assessed": score["overall_level"] if score else "-",
                "confidence": f"{score['confidence']:.2f}" if score else "-",
                "importance": skill["importance"],
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔻 Primary gaps")
        for gap in st.session_state.gaps["primary_gaps"]:
            with st.expander(
                f"`{gap['skill']}` — {gap['current_level']}/4 → {gap['target_level']}/4 (priority {gap['priority']:.1f})"
            ):
                st.write(gap["rationale"])

    with col2:
        st.subheader("✨ Adjacent skills (high leverage)")
        for adj in st.session_state.gaps["adjacent_skills"]:
            with st.expander(
                f"`{adj['skill']}` — ~{adj['weeks_to_basic']:.0f} weeks to working level"
            ):
                st.write(f"**Why:** {adj['why_relevant']}")
                st.write(
                    f"**Leverage from:** {', '.join(adj['leverage_from']) or '-'}"
                )

    st.divider()
    st.subheader("📚 Personalised learning plan")
    st.caption(
        f"Total estimated duration: ~{st.session_state.plan['total_weeks']:.0f} weeks"
    )

    for item in st.session_state.plan["items"]:
        kind_emoji = "🎯" if item["kind"] == "gap" else "✨"
        with st.expander(
            f"{kind_emoji} `{item['skill']}` — {item['estimated_weeks']:.0f} wk · {item['weekly_hours']:.0f} h/wk"
        ):
            st.markdown(f"**Capstone project:** {item['capstone']}")
            st.markdown("**Resources:**")
            for r in item["resources"]:
                st.markdown(f"- _{r['type']}_ — **{r['title']}**: {r['why']}")

    st.divider()
    st.subheader("🗓️ Suggested sequence")
    for phase in st.session_state.plan["sequence"]:
        st.markdown(
            f"- **{phase['weeks']}** — _{phase['focus']}_: {', '.join(phase['skills'])}"
        )

    st.divider()
    full_report = {
        "scorecard": rows,
        "gaps": st.session_state.gaps,
        "plan": st.session_state.plan,
    }
    st.download_button(
        "⬇️ Download full report (JSON)",
        data=json.dumps(full_report, indent=2),
        file_name="skill_report.json",
        mime="application/json",
    )