from __future__ import annotations

from collections import defaultdict

import streamlit as st

from utils.navigation import render_app_sidebar
from utils.pdf_text import extract_unit_combined_text, unit_material_fingerprint
from utils.storage import (
    get_subject_pdf_paths,
    get_unit_pdf_paths,
    get_user_library,
    get_weak_subtopics,
    save_quiz_feedback,
)
from utils.styles import inject_styles, nav_to
from utils.teaching_agents import (
    STUDY_MATERIAL_MAX_CHARS,
    build_teaching_stack,
    extract_json_object,
    run_agent,
    study_prompt_prefix,
)

PHASE_SETUP   = "setup"
PHASE_QUIZ    = "quiz"
PHASE_RESULTS = "results"


def _quiz_css() -> None:
    st.markdown("""
    <style>
    .quiz-panel {
        background: #ffffff;
        border: 1.5px solid #e8e3d9;
        border-radius: 16px;
        padding: 0;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        overflow: hidden;
        margin-bottom: 1.5rem;
    }
    .quiz-panel-header {
        background: #1c1917;
        padding: 1.2rem 1.6rem;
    }
    .quiz-panel-title {
        font-family: 'DM Serif Display', serif;
        font-weight: 400;
        color: #faf8f4;
        font-size: 1.1rem;
    }
    .quiz-panel-meta {
        font-size: 0.76rem;
        color: #78716c;
        margin-top: 0.15rem;
        font-family: 'DM Mono', monospace;
    }
    .quiz-progress-wrap {
        background: #faf8f4;
        padding: 0.7rem 1.6rem;
        border-bottom: 1px solid #e8e3d9;
    }
    .quiz-progress-bar-bg {
        background: #e8e3d9;
        border-radius: 99px;
        height: 5px;
        width: 100%;
    }
    .quiz-progress-bar-fill {
        background: linear-gradient(90deg, #d97706, #f59e0b);
        border-radius: 99px;
        height: 5px;
    }
    .quiz-progress-label {
        font-size: 0.72rem;
        color: #a8a29e;
        margin-top: 0.3rem;
        text-align: right;
        font-family: 'DM Mono', monospace;
    }
    .quiz-question-body {
        padding: 1.6rem 1.6rem 0.5rem;
    }
    .quiz-q-number {
        font-size: 0.7rem;
        font-weight: 600;
        color: #d97706;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.5rem;
        font-family: 'DM Mono', monospace;
    }
    .quiz-q-text {
        font-weight: 600;
        color: #1c1917;
        font-size: 1rem;
        line-height: 1.6;
        margin-bottom: 1rem;
    }
    .result-panel {
        background: #ffffff;
        border: 1.5px solid #e8e3d9;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
        margin-bottom: 1.5rem;
    }
    .result-header {
        padding: 1.2rem 1.6rem;
        border-bottom: 1px solid #e8e3d9;
        background: #faf8f4;
    }
    .result-score-section {
        padding: 2rem 1.6rem 1.5rem;
        text-align: center;
    }
    .result-score-circle {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-family: 'DM Serif Display', serif;
        font-size: 1.7rem;
        font-weight: 400;
        margin: 0 auto 1rem;
    }
    </style>
    """, unsafe_allow_html=True)


def _render_setup(uid: str, library: dict) -> None:
    subjects = list(library.keys())

    if not subjects:
        st.markdown("""
            <div style="text-align:center; padding: 3rem; background: #ffffff;
                        border: 1.5px dashed #c7d0ff; border-radius: 16px;">
                <div style="font-size: 3rem; margin-bottom: 1rem;"></div>
                <div style="color: #6b7280; font-size: 0.95rem;">
                    Create a subject and upload PDFs in your Library first.
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Go to Library →", type="primary", use_container_width=True):
            nav_to("library")
        return

    st.markdown("""
        <div style="background: #ffffff; border: 1px solid #e8e3d9; border-radius: 12px;
                    padding: 1.4rem; margin-bottom: 1.5rem;">
            <div style="font-family: 'DM Serif Display', serif; font-size: 1.3rem;
                        color: #1c1917; margin-bottom: 0.3rem;">Set up your quiz</div>
            <div style="font-size: 0.84rem; color: #78716c;">Choose a subject and scope, then generate.</div>
        </div>
    """, unsafe_allow_html=True)

    mode    = st.radio("Quiz scope", ["Unit quiz", "Subject quiz"], horizontal=True)
    subject = st.selectbox("Subject", subjects)

    if mode == "Unit quiz":
        units = list(library.get(subject, {}).get("units", {}).keys())
        if not units:
            st.warning("This subject has no units yet. Add units in the Library.")
            return
        unit  = st.selectbox("Unit", units)
        paths = get_unit_pdf_paths(uid, subject, unit)
        label = f"{subject}  ·  {unit}"
    else:
        unit  = "All Units"
        paths = get_subject_pdf_paths(uid, subject)
        label = f"{subject}  ·  Full Subject"

    if not paths:
        st.warning("No PDF material found for this selection. Upload PDFs in Library first.")
        return

    stack = build_teaching_stack()
    if not stack:
        st.error("Groq API key is missing in `utils/teaching_agents.py`.")
        return

    weak_subtopics = get_weak_subtopics(uid, subject, limit=4)
    if weak_subtopics:
        st.markdown(f"""
            <div style="background: #fffbeb; border: 1.5px solid #f59e0b33; border-radius: 10px;
                        padding: 0.8rem 1.1rem; margin-bottom: 1rem; font-size: 0.85rem; color: #92400e;">
                🎯 <strong>Adaptive focus:</strong> {", ".join(weak_subtopics)}
            </div>
        """, unsafe_allow_html=True)

    if st.button("🚀  Generate Quiz", type="primary", use_container_width=True):
        material   = extract_unit_combined_text(paths, max_chars=STUDY_MATERIAL_MAX_CHARS)
        focus_text = ""
        if weak_subtopics:
            focus_text = (
                "The student has been weak in these subtopics from past quizzes: "
                + ", ".join(weak_subtopics)
                + ". Create at least 60% of questions around these weak subtopics while still covering the rest."
            )
        prompt = (
            study_prompt_prefix(subject, unit, material)
            + focus_text
            + "\nOutput only the JSON object for the quiz."
        )
        with st.spinner("Building your quiz from your study material..."):
            out, err = run_agent(stack.quiz_agent, prompt)
            if err:
                st.error(err)
            elif out:
                data = extract_json_object(out.content)
                if data and isinstance(data.get("questions"), list):
                    fp = unit_material_fingerprint(paths)
                    st.session_state["active_quiz"] = {
                        "questions":  data["questions"],
                        "subject":    subject,
                        "unit":       unit,
                        "label":      label,
                        "fp":         fp,
                        "answers":    {},
                        "current_q":  0,
                    }
                    st.session_state["quiz_phase"] = PHASE_QUIZ
                    st.rerun()
                else:
                    st.error("Could not parse quiz. Please try again.")


def _render_quiz_panel() -> None:
    aq        = st.session_state["active_quiz"]
    questions = aq["questions"]
    total     = len(questions)
    current   = aq["current_q"]
    q         = questions[current]
    opts      = q.get("options") or []
    pct_done  = int(100 * current / total)

    st.markdown(f"""
        <div class="quiz-panel">
            <div class="quiz-panel-header">
                <div class="quiz-panel-title">{aq['label']}</div>
                <div class="quiz-panel-meta">{total} question{"s" if total != 1 else ""} · answer all then submit</div>
            </div>
            <div class="quiz-progress-wrap">
                <div class="quiz-progress-bar-bg">
                    <div class="quiz-progress-bar-fill" style="width: {pct_done}%;"></div>
                </div>
                <div class="quiz-progress-label">Question {current + 1} of {total}</div>
            </div>
            <div class="quiz-question-body">
                <div class="quiz-q-number">Question {current + 1}</div>
                <div class="quiz-q-text">{q.get('question', '')}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    chosen = None
    if opts:
        saved_answer = aq["answers"].get(current)
        chosen = st.radio(
            "Choose an answer",
            options=list(range(len(opts))),
            format_func=lambda j, o=opts: o[j] if j < len(o) else str(j),
            index=saved_answer if saved_answer is not None else 0,
            key=f"quiz_radio_{current}",
            label_visibility="collapsed",
        )
        aq["answers"][current] = chosen
        st.session_state["active_quiz"] = aq
    else:
        st.caption("(No options for this question.)")

    st.markdown("<br>", unsafe_allow_html=True)

    nav_cols = st.columns([1, 1, 1])
    with nav_cols[0]:
        if current > 0:
            if st.button("← Back", use_container_width=True):
                aq["current_q"] -= 1
                st.session_state["active_quiz"] = aq
                st.rerun()
        else:
            if st.button("✕ Exit Quiz", use_container_width=True):
                st.session_state["quiz_phase"] = PHASE_SETUP
                st.session_state.pop("active_quiz", None)
                st.rerun()

    with nav_cols[2]:
        if current < total - 1:
            if st.button("Next →", type="primary", use_container_width=True):
                if chosen is not None:
                    aq["answers"][current] = chosen
                aq["current_q"] += 1
                st.session_state["active_quiz"] = aq
                st.rerun()
        else:
            if st.button("✅ Submit Quiz", type="primary", use_container_width=True):
                if chosen is not None:
                    aq["answers"][current] = chosen
                st.session_state["active_quiz"] = aq
                _compute_and_store_results()
                st.session_state["quiz_phase"] = PHASE_RESULTS
                st.rerun()

    # Progress dots
    dots_html = "<div style='display:flex; gap:6px; justify-content:center; margin-top:1.2rem; flex-wrap:wrap;'>"
    for i in range(total):
        if i == current:
            color, size = "#d97706", "10px"
        elif i in aq["answers"]:
            color, size = "#10b981", "8px"
        else:
            color, size = "#d4cfc8", "8px"
        dots_html += f"<div style='width:{size}; height:{size}; border-radius:50%; background:{color};'></div>"
    dots_html += "</div>"
    st.markdown(dots_html, unsafe_allow_html=True)


def _compute_and_store_results() -> None:
    aq        = st.session_state["active_quiz"]
    questions = aq["questions"]
    answers   = aq["answers"]
    total     = len(questions)

    by_subtopic: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "total": 0})
    correct = 0
    results = []

    for i, q in enumerate(questions):
        opts        = q.get("options") or []
        answer_idx  = answers.get(i)
        correct_idx = q.get("correct_index")
        raw_sub     = q.get("subtopic")
        subtopic    = str(raw_sub).strip() if raw_sub else "General"
        is_ok       = answer_idx == correct_idx
        if is_ok:
            correct += 1
        by_subtopic[subtopic]["total"] += 1
        if is_ok:
            by_subtopic[subtopic]["correct"] += 1
        correct_label = (
            opts[correct_idx]
            if isinstance(correct_idx, int) and 0 <= correct_idx < len(opts)
            else str(correct_idx)
        )
        user_label = (
            opts[answer_idx]
            if isinstance(answer_idx, int) and 0 <= answer_idx < len(opts)
            else "Not answered"
        )
        results.append({
            "idx":           i,
            "question":      q.get("question", ""),
            "is_ok":         is_ok,
            "correct_label": correct_label,
            "user_label":    user_label,
        })

    aq["results"]     = results
    aq["correct"]     = correct
    aq["total"]       = total
    aq["by_subtopic"] = dict(by_subtopic)
    st.session_state["active_quiz"] = aq

    save_quiz_feedback(
        user_id=st.session_state.get("user_id", ""),
        subject=aq["subject"],
        unit=aq["unit"],
        score_correct=correct,
        score_total=total,
        by_subtopic=by_subtopic,
    )


def _render_results_panel() -> None:
    aq          = st.session_state["active_quiz"]
    correct     = aq["correct"]
    total       = aq["total"]
    results     = aq["results"]
    by_subtopic = aq["by_subtopic"]
    pct         = (100 * correct / total) if total else 0

    score_color = "#10b981" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
    score_bg    = "#f0fdf4" if pct >= 70 else "#fffbeb"  if pct >= 40 else "#fef2f2"
    score_emoji = "🎉"      if pct >= 70 else "📈"       if pct >= 40 else "💪"
    score_msg   = "Great work!" if pct >= 70 else "Keep it up!" if pct >= 40 else "Keep practising!"

    st.markdown(f"""
        <div class="result-panel">
            <div class="result-header">
                <div style="font-family:'Poppins',sans-serif; font-weight:700; color:#1a1d2e;">
                    Quiz Results — {aq['label']}
                </div>
            </div>
            <div class="result-score-section">
                <div class="result-score-circle" style="background:{score_bg}; border: 3px solid {score_color}33; color:{score_color};">
                    {pct:.0f}%
                </div>
                <div style="font-size:1.6rem; margin-bottom:0.3rem;">{score_emoji}</div>
                <div style="font-size:1rem; font-weight:600; color:#1a1d2e;">{correct} of {total} correct</div>
                <div style="font-size:0.88rem; color:#6b7280; margin-top:0.2rem;">{score_msg}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    strong, weak = [], []
    for subtopic, stats in by_subtopic.items():
        if stats["correct"] == stats["total"]:
            strong.append(subtopic)
        elif stats["correct"] < stats["total"]:
            weak.append((subtopic, stats["correct"], stats["total"]))

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        st.markdown(f"""
            <div style="background:#f0fdf4; border:1.5px solid #10b98133;
                        border-radius:12px; padding:1.1rem 1.3rem; margin-bottom:1rem;">
                <div style="font-weight:700; color:#10b981; margin-bottom:0.5rem;">Strong areas</div>
                <div style="font-size:0.88rem; color:#374151;">
                    {", ".join(sorted(strong)) if strong else "Keep going — strengths will show!"}
                </div>
            </div>
        """, unsafe_allow_html=True)
    with fb_col2:
        weak_sorted = sorted(weak, key=lambda x: (x[1] / x[2], x[0]))
        weak_html   = "<br>".join(
            [f"<b>{s}</b>: {c}/{t} correct" for s, c, t in weak_sorted]
        ) if weak_sorted else "None — excellent consistency! 🏆"
        st.markdown(f"""
            <div style="background:#fffbeb; border:1.5px solid #f59e0b33;
                        border-radius:12px; padding:1.1rem 1.3rem; margin-bottom:1rem;">
                <div style="font-weight:700; color:#f59e0b; margin-bottom:0.5rem;">Needs more focus</div>
                <div style="font-size:0.88rem; color:#374151;">{weak_html}</div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <div style="font-family:'Poppins',sans-serif; font-weight:700; color:#1a1d2e;
                    font-size:1rem; margin:1rem 0 0.7rem;">Question Review</div>
    """, unsafe_allow_html=True)

    for r in results:
        icon   = "✅" if r["is_ok"] else "❌"
        bg     = "#f0fdf4" if r["is_ok"] else "#fef2f2"
        border = "#10b98133" if r["is_ok"] else "#ef444433"
        wrong_row = (
            "" if r["is_ok"] else
            f'<div style="font-size:0.8rem; color:#6b7280; margin-top:0.25rem;">'
            f'Your answer: <span style="color:#ef4444;">{r["user_label"]}</span>'
            f'&nbsp;·&nbsp;Correct: <strong style="color:#10b981;">{r["correct_label"]}</strong></div>'
        )
        st.markdown(f"""
            <div style="background:{bg}; border:1.5px solid {border};
                        border-radius:10px; padding:0.8rem 1.1rem; margin-bottom:0.5rem;">
                <div style="font-weight:600; color:#1a1d2e; font-size:0.88rem;">
                    {icon} Q{r['idx']+1}: {r['question']}
                </div>
                {wrong_row}
            </div>
        """, unsafe_allow_html=True)

    st.info("Saved! Your next quiz will focus more on your weak areas.")
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Try Another Quiz", use_container_width=True):
            st.session_state["quiz_phase"] = PHASE_SETUP
            st.session_state.pop("active_quiz", None)
            st.rerun()
    with col2:
        if st.button("View History", use_container_width=True):
            st.session_state["quiz_phase"] = PHASE_SETUP
            st.session_state.pop("active_quiz", None)
            nav_to("profile")
    with col3:
        if st.button("← Back to Library", use_container_width=True):
            st.session_state["quiz_phase"] = PHASE_SETUP
            st.session_state.pop("active_quiz", None)
            nav_to("library")


def render() -> None:
    inject_styles()
    _quiz_css()
    render_app_sidebar()

    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    uid     = st.session_state.user_id
    library = get_user_library(uid)
    phase   = st.session_state.get("quiz_phase", PHASE_SETUP)

    if phase == PHASE_SETUP:
        if st.button("← Back to Library", key="quiz_back"):
            nav_to("library")
        st.markdown('<div class="page-title">Quizzes</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">Test yourself on your own study material — unit by unit or the full subject.</div>',
            unsafe_allow_html=True,
        )
        _render_setup(uid, library)

    elif phase == PHASE_QUIZ:
        st.markdown('<div class="page-title">Quiz</div>', unsafe_allow_html=True)
        _render_quiz_panel()

    elif phase == PHASE_RESULTS:
        st.markdown('<div class="page-title">Results</div>', unsafe_allow_html=True)
        _render_results_panel()