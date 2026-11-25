from __future__ import annotations

import streamlit as st

from utils.navigation import render_app_sidebar
from utils.pdf_text import extract_unit_combined_text
from utils.storage import get_subject_pdf_paths, get_unit_pdf_paths, get_user_library
from utils.styles import inject_styles, nav_to
from utils.teaching_agents import (
    STUDY_MATERIAL_MAX_CHARS,
    build_teaching_stack,
)
from utils.teachback import generate_teachback_round, evaluate_teachback_answer

PHASE_SETUP = "setup"
PHASE_EXPLANATION = "explanation"
PHASE_QA = "qa"
PHASE_FEEDBACK = "feedback"


def _init_state() -> None:
    if "teachback_phase" not in st.session_state:
        st.session_state["teachback_phase"] = PHASE_SETUP
    if "teachback" not in st.session_state:
        st.session_state["teachback"] = {}


def _reset_session() -> None:
    st.session_state["teachback_phase"] = PHASE_SETUP
    st.session_state.pop("teachback", None)
    _init_state()


def _render_setup(uid: str, library: dict) -> None:
    subjects = list(library.keys())
    if not subjects:
        st.markdown(
            """
            <div style="text-align:center; padding: 3rem; background: #ffffff;
                        border: 1.5px dashed #c7d0ff; border-radius: 16px;">
                <div style="color: #6b7280; font-size: 0.95rem;">
                    Create a subject and upload PDFs in your Library first.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Go to Library →", type="primary", use_container_width=True):
            nav_to("library")
        return

    st.markdown('<div class="page-title">Teach Back</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="page-subtitle">Active recall loop: Explanation → Your answer → Feedback → repeat.</div>',
        unsafe_allow_html=True,
    )

    mode = st.radio("Scope", ["Unit", "Full subject"], horizontal=True)
    subject = st.selectbox("Subject", subjects)

    if mode == "Unit":
        units = list(library.get(subject, {}).get("units", {}).keys())
        if not units:
            st.warning("This subject has no units yet. Add units in the Library.")
            return
        unit = st.selectbox("Unit", units)
        paths = get_unit_pdf_paths(uid, subject, unit)
    else:
        unit = "All Units"
        paths = get_subject_pdf_paths(uid, subject)

    if not paths:
        st.warning("No PDF material found for this selection. Upload PDFs in Library first.")
        return

    rounds = st.number_input(
        "Rounds",
        min_value=3,
        max_value=10,
        value=5,
        step=1,
        help="Use the arrows to increase/decrease rounds.",
    )

    stack = build_teaching_stack()
    if not stack:
        st.error("Groq API key is missing in `utils/teaching_agents.py`.")
        return

    if st.button("Start Teach Back", type="primary", use_container_width=True):
        material = extract_unit_combined_text(paths, max_chars=STUDY_MATERIAL_MAX_CHARS)
        with st.spinner("Preparing your first explanation..."):
            rnd = generate_teachback_round(
                teachback_agent=stack.teachback_agent,
                subject=subject,
                unit=unit,
                material=material,
                focus_hint="",
            )
        if not rnd:
            st.error("Could not generate a teach-back round. Please try again.")
            return

        st.session_state["teachback"] = {
            "subject": subject,
            "unit": unit,
            "material": material,
            "rounds_total": rounds,
            "round_idx": 0,
            "current": rnd,  # subtopic/explanation/key_ideas/question
            "last_answer": "",
            "last_feedback": None,
        }
        st.session_state["teachback_phase"] = PHASE_EXPLANATION
        st.rerun()


def _render_explanation() -> None:
    tb = st.session_state["teachback"]
    cur = tb["current"]
    total = tb["rounds_total"]
    idx = tb["round_idx"] + 1

    st.markdown('<div class="page-title">Teach Back</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-subtitle">Round {idx} of {total} · Subtopic: <b>{cur.get("subtopic","")}</b></div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Explanation")
    st.write(cur.get("explanation", ""))

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("End session", use_container_width=True):
            _reset_session()
            st.rerun()
    with c2:
        if st.button("Next →", type="primary", use_container_width=True):
            st.session_state["teachback_phase"] = PHASE_QA
            st.rerun()


def _render_qa() -> None:
    tb = st.session_state["teachback"]
    cur = tb["current"]
    total = tb["rounds_total"]
    idx = tb["round_idx"] + 1

    st.markdown('<div class="page-title">Teach Back</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-subtitle">Round {idx} of {total} · Answer in your own words.</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Question")
    st.write(cur.get("question", ""))

    answer = st.text_area(
        "Your answer",
        value=tb.get("last_answer", ""),
        height=180,
        placeholder="Type your explanation here… (aim for 5–10 sentences)",
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("← Back", use_container_width=True):
            tb["last_answer"] = answer
            st.session_state["teachback"] = tb
            st.session_state["teachback_phase"] = PHASE_EXPLANATION
            st.rerun()
    with c2:
        if st.button("Check my answer", type="primary", use_container_width=True):
            stack = build_teaching_stack()
            if not stack:
                st.error("Groq API key is missing in `utils/teaching_agents.py`.")
                return
            with st.spinner("Evaluating your explanation..."):
                fb = evaluate_teachback_answer(
                    teachback_agent=stack.teachback_agent,
                    subject=tb["subject"],
                    unit=tb["unit"],
                    material=tb["material"],
                    subtopic=cur.get("subtopic", ""),
                    question=cur.get("question", ""),
                    key_ideas=[str(x) for x in (cur.get("key_ideas") or [])],
                    student_answer=answer,
                )
            if not fb:
                st.error("Could not evaluate the answer. Please try again.")
                return
            tb["last_answer"] = answer
            tb["last_feedback"] = fb
            st.session_state["teachback"] = tb
            st.session_state["teachback_phase"] = PHASE_FEEDBACK
            st.rerun()


def _render_feedback() -> None:
    tb = st.session_state["teachback"]
    cur = tb["current"]
    fb = tb.get("last_feedback") or {}
    total = tb["rounds_total"]
    idx = tb["round_idx"] + 1

    st.markdown('<div class="page-title">Teach Back</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="page-subtitle">Round {idx} of {total} · Feedback</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Feedback")
    st.write(f"**You explained:** {fb.get('score', '—')}")

    correct = fb.get("correct_ideas") or []
    missed = fb.get("missed_ideas") or []
    if correct:
        st.success("Covered ideas:\n\n" + "\n".join([f"- {c}" for c in correct]))
    if missed:
        st.warning("Missed ideas:\n\n" + "\n".join([f"- {m}" for m in missed]))

    if fb.get("accuracy_feedback"):
        st.markdown("**Accuracy**")
        st.write(fb.get("accuracy_feedback"))
    if fb.get("clarity_feedback"):
        st.markdown("**Clarity**")
        st.write(fb.get("clarity_feedback"))
    if fb.get("improvement_suggestion"):
        st.markdown("**Improve it**")
        st.write(fb.get("improvement_suggestion"))

    is_last = tb["round_idx"] >= (tb["rounds_total"] - 1)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("End session", use_container_width=True):
            _reset_session()
            st.rerun()
    with c2:
        if is_last:
            if st.button("Finish", type="primary", use_container_width=True):
                _reset_session()
                st.rerun()
        else:
            if st.button("Next round →", type="primary", use_container_width=True):
                stack = build_teaching_stack()
                if not stack:
                    st.error("Groq API key is missing in `utils/teaching_agents.py`.")
                    return
                with st.spinner("Generating next explanation..."):
                    rnd = generate_teachback_round(
                        teachback_agent=stack.teachback_agent,
                        subject=tb["subject"],
                        unit=tb["unit"],
                        material=tb["material"],
                        focus_hint="",
                    )
                if not rnd:
                    st.error("Could not generate the next round. Please try again.")
                    return
                tb["round_idx"] += 1
                tb["current"] = rnd
                tb["last_answer"] = ""
                tb["last_feedback"] = None
                st.session_state["teachback"] = tb
                st.session_state["teachback_phase"] = PHASE_EXPLANATION
                st.rerun()


def render() -> None:
    inject_styles()
    render_app_sidebar()
    _init_state()

    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    uid = st.session_state.user_id
    library = get_user_library(uid)
    phase = st.session_state.get("teachback_phase", PHASE_SETUP)

    if phase == PHASE_SETUP:
        if st.button("← Back to Library", key="teachback_back"):
            nav_to("library")
        _render_setup(uid, library)
    elif phase == PHASE_EXPLANATION:
        _render_explanation()
    elif phase == PHASE_QA:
        _render_qa()
    elif phase == PHASE_FEEDBACK:
        _render_feedback()
    else:
        _reset_session()
        st.rerun()

