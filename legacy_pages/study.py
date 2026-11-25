"""Study tools: mnemonics, academic advisor, research librarian, quiz — grounded in unit PDFs."""

from __future__ import annotations

from collections import defaultdict

import streamlit as st

from utils.navigation import render_app_sidebar
from utils.pdf_text import extract_unit_combined_text, unit_material_fingerprint
from utils.storage import get_unit_pdf_paths
from utils.styles import inject_styles, nav_to
from utils.teaching_agents import (
    STUDY_MATERIAL_MAX_CHARS,
    build_teaching_stack,
    extract_google_doc_url,
    extract_json_object,
    groq_model_id,
    run_agent,
    study_prompt_prefix,
    podcast_prompt, 
)


def _study_source_tag(uid: str, subject: str, unit: str) -> str:
    paths = get_unit_pdf_paths(uid, subject, unit)
    fp = unit_material_fingerprint(paths)
    return f"{uid}|{subject}|{unit}|{fp}"


def _invalidate_study_cache(state_key: str, suffix: str) -> None:
    uid = st.session_state.user_id
    subj = st.session_state.get("study_subject") or ""
    unit = st.session_state.get("study_unit") or ""
    tag_key = f"_study_tag_{suffix}"
    cur = _study_source_tag(uid, subj, unit)
    if st.session_state.get(tag_key) != cur:
        st.session_state[state_key] = None
    st.session_state[tag_key] = cur


def _back_to_library_unit() -> None:
    st.session_state.page = "library"
    st.session_state.lib_view = "unit_detail"
    if st.session_state.get("study_subject"):
        st.session_state.lib_subject = st.session_state.study_subject
    if st.session_state.get("study_unit"):
        st.session_state.lib_unit = st.session_state.study_unit
    st.rerun()


def _hub_button(label: str, view: str, key: str) -> None:
    if st.button(label, key=key, use_container_width=True):
        st.session_state.study_view = view
        st.rerun()


def render() -> None:
    inject_styles()

    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return
    render_app_sidebar()

    uid = st.session_state.user_id
    subject = st.session_state.get("study_subject")
    unit = st.session_state.get("study_unit")

    if not subject or not unit:
        st.markdown('<div class="page-title">Study tools</div>', unsafe_allow_html=True)
        st.warning("Open this from **Library** after you pick a unit with PDFs.")
        if st.button("Go to Library", use_container_width=True):
            nav_to("library")
        return

    paths = get_unit_pdf_paths(uid, subject, unit)
    if not paths:
        st.markdown('<div class="page-title">Study tools</div>', unsafe_allow_html=True)
        st.warning("This unit has no PDF files. Upload at least one PDF in the Library.")
        if st.button("Back to Library", use_container_width=True):
            _back_to_library_unit()
        return

    material = extract_unit_combined_text(paths, max_chars=STUDY_MATERIAL_MAX_CHARS)
    fp = unit_material_fingerprint(paths)
    prefix = study_prompt_prefix(subject, unit, material)

    stack = build_teaching_stack()
    view = st.session_state.get("study_view", "hub")

    st.markdown(
        f"""
        <div class="breadcrumb">📚 Library &rsaquo; <span>{subject}</span> &rsaquo; <span>{unit}</span> &rsaquo; Study</div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        f"PDF excerpt per request: up to **{STUDY_MATERIAL_MAX_CHARS:,}** characters "
        "(keeps Groq requests within tier limits). Edit `STUDY_MATERIAL_MAX_CHARS` in "
        "`utils/teaching_agents.py` to raise or lower."
    )

    if not stack:
        st.error(
            "Groq API key is not set. Open **`utils/teaching_agents.py`** and paste your key into "
            "`HARDCODED_GROQ_API_KEY`, then restart the app."
        )
        if st.button("Back to Library", use_container_width=True):
            _back_to_library_unit()
        return

    # --- Hub ---
    if view == "hub":
        st.markdown('<div class="page-title">AI study tools</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">Grounded in your uploaded PDFs for this unit.</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            _hub_button("Mnemonics", "mnemonics", "study_btn_mnem")
            _hub_button("Academic Advisor", "advisor", "study_btn_adv")
        with c2:
            _hub_button("Research Librarian", "librarian", "study_btn_lib")
            _hub_button("Quiz (10 questions)", "quiz", "study_btn_quiz")
            _hub_button("Mindmap", "mindmap", "study_btn_mindmap")
            _hub_button("🎙️ Podcast", "podcast", "study_btn_podcast")

        st.markdown("---")
        st.caption(
            f"Groq model: `{groq_model_id()}` (set **GROQ_MODEL** to override). "
            "Advisor and librarian use Google Docs when Composio is configured."
        )
        if st.button("← Back to unit", use_container_width=True):
            _back_to_library_unit()
        return

    # --- Mnemonics ---
    if view == "mnemonics":
        _invalidate_study_cache("mnemonics_content", "mnem")
        st.markdown('<div class="page-title">Mnemonics</div>', unsafe_allow_html=True)
        if st.button("← Back to study tools"):
            st.session_state.study_view = "hub"
            st.rerun()

        if st.button("Generate mnemonics", type="primary"):
            with st.spinner("Creating mnemonics..."):
                out, err = run_agent(
                    stack.mnemonics_agent,
                    prefix + "Produce Markdown mnemonics only.",
                )
                if err:
                    st.error(err)
                elif out:
                    st.session_state.mnemonics_content = out.content

        if st.session_state.mnemonics_content:
            st.markdown("### Your mnemonics")
            st.markdown(st.session_state.mnemonics_content)
        return

    # --- Advisor ---
    if view == "advisor":
        _invalidate_study_cache("advisor_content", "adv")
        st.markdown('<div class="page-title">Academic Advisor</div>', unsafe_allow_html=True)
        if st.button("← Back to study tools", key="adv_back"):
            st.session_state.study_view = "hub"
            st.rerun()

        if not stack.google_docs_tool:
            st.info(
                "Composio / Google Docs is not configured. The advisor will return a **Markdown** roadmap only. "
                "Set **COMPOSIO_API_KEY** to create a Google Doc automatically."
            )

        if st.button("Generate learning roadmap", type="primary"):
            with st.spinner("Building roadmap..."):
                out, err = run_agent(
                    stack.academic_advisor_agent,
                    prefix + "Create the roadmap; if tools allow, create the Google Doc and include its link.",
                )
                if err:
                    st.error(err)
                elif out:
                    st.session_state.advisor_content = out.content

        if st.session_state.advisor_content:
            url = extract_google_doc_url(st.session_state.advisor_content)
            if url:
                st.markdown(f"[Open roadmap in Google Docs]({url})")
            st.markdown(st.session_state.advisor_content)
        return

    # --- Librarian ---
    if view == "librarian":
        _invalidate_study_cache("librarian_content", "lib")
        st.markdown('<div class="page-title">Research Librarian</div>', unsafe_allow_html=True)
        if st.button("← Back to study tools", key="lib_back"):
            st.session_state.study_view = "hub"
            st.rerun()

        if not stack.serp_key:
            st.caption("No **SERPAPI_API_KEY**: search tools are disabled; the librarian will still suggest resources from general knowledge.")
        if not stack.google_docs_tool:
            st.caption("No **COMPOSIO_API_KEY**: output stays in the app (no auto Google Doc).")

        if st.button("Curate resources", type="primary"):
            with st.spinner("Curating resources..."):
                out, err = run_agent(
                    stack.research_librarian_agent,
                    prefix + "Search briefly if search is available, then deliver the resource list "
                    "(and create a Google Doc with the link if the tool exists).",
                )
                if err:
                    st.error(err)
                elif out:
                    st.session_state.librarian_content = out.content

        if st.session_state.librarian_content:
            url = extract_google_doc_url(st.session_state.librarian_content)
            if url:
                st.markdown(f"[Open resource list in Google Docs]({url})")
            st.markdown(st.session_state.librarian_content)
        return

    # --- Quiz ---
    if view == "quiz":
        _invalidate_study_cache("quiz_data", "quiz")
        st.markdown('<div class="page-title">Quiz</div>', unsafe_allow_html=True)
        if st.button("← Back to study tools", key="quiz_back"):
            st.session_state.study_view = "hub"
            st.rerun()

        if st.button("Generate quiz", type="primary"):
            with st.spinner("Writing questions..."):
                out, err = run_agent(
                    stack.quiz_agent,
                    prefix + "Output only the JSON object for the quiz.",
                )
                if err:
                    st.session_state.quiz_data = None
                    st.error(err)
                elif out:
                    data = extract_json_object(out.content)
                    if data and "questions" in data:
                        st.session_state.quiz_data = data
                    else:
                        st.session_state.quiz_data = None
                        st.error("Could not parse quiz JSON. Raw response below.")
                        st.code(out.content)

        qd = st.session_state.quiz_data
        if qd and isinstance(qd.get("questions"), list):
            questions = qd["questions"]
            st.subheader(f"{subject} · {unit}")
            if len(questions) != 10:
                st.warning(
                    f"This quiz has **{len(questions)}** question(s). "
                    "Regenerate if you want a full set of 10."
                )

            for i, q in enumerate(questions):
                opts = q.get("options") or []
                st.markdown(f"**{i + 1}.** {q.get('question', '')}")
                if not opts:
                    st.caption("(No options for this question.)")
                    continue
                st.radio(
                    "Choose an answer",
                    options=list(range(len(opts))),
                    format_func=lambda j, o=opts: o[j] if j < len(o) else str(j),
                    key=f"quiz_{fp}_{i}",
                    label_visibility="collapsed",
                )

            if st.button("Check answers"):
                results: list[dict] = []
                correct = 0
                for i, q in enumerate(questions):
                    opts = q.get("options") or []
                    ci = q.get("correct_index")
                    ans = st.session_state.get(f"quiz_{fp}_{i}")
                    ok = ci == ans
                    if ok:
                        correct += 1
                    raw_sub = q.get("subtopic")
                    subtopic = (
                        str(raw_sub).strip()
                        if raw_sub is not None and str(raw_sub).strip()
                        else "General"
                    )
                    corr_label = (
                        opts[ci]
                        if isinstance(ci, int) and 0 <= ci < len(opts)
                        else str(ci)
                    )
                    st.write(
                        f"**Q{i + 1}:** {'Correct' if ok else 'Incorrect'} "
                        f"(correct: {corr_label})"
                    )
                    results.append({"ok": ok, "subtopic": subtopic, "index": i + 1})

                n = len(questions)
                pct = (100.0 * correct / n) if n else 0.0
                st.success(f"Score: {correct} / {n} ({pct:.0f}%)")

                by_subtopic: dict[str, dict[str, int]] = defaultdict(
                    lambda: {"correct": 0, "total": 0}
                )
                for r in results:
                    s = r["subtopic"]
                    by_subtopic[s]["total"] += 1
                    if r["ok"]:
                        by_subtopic[s]["correct"] += 1

                strengths = [
                    s
                    for s, v in by_subtopic.items()
                    if v["total"] and v["correct"] == v["total"]
                ]
                need_focus = [
                    s
                    for s, v in by_subtopic.items()
                    if v["total"] and v["correct"] < v["total"]
                ]
                need_focus.sort(
                    key=lambda s: (
                        by_subtopic[s]["correct"] / by_subtopic[s]["total"],
                        s,
                    )
                )

                st.markdown("### Feedback")
                if pct >= 80:
                    tone = "Strong work overall."
                elif pct >= 50:
                    tone = "You're partway there; targeted review will help."
                else:
                    tone = "Keep going—use the areas below to guide your next study session."

                st.markdown(
                    f"{tone} You answered **{correct}** of **{n}** questions correctly."
                )

                st.markdown("**Areas you have a good grasp on**")
                if strengths:
                    for s in sorted(strengths):
                        v = by_subtopic[s]
                        st.markdown(
                            f"- **{s}** — {v['correct']}/{v['total']} correct in this area."
                        )
                else:
                    st.markdown(
                        "_No subtopic was perfect yet. Revisit the questions you missed "
                        "and try another quiz when ready._"
                    )

                st.markdown("**Where to focus more**")
                if need_focus:
                    for s in need_focus:
                        v = by_subtopic[s]
                        missed = v["total"] - v["correct"]
                        st.markdown(
                            f"- **{s}** — {v['correct']}/{v['total']} correct "
                            f"({missed} question{'s' if missed != 1 else ''} to review)."
                        )
                else:
                    st.markdown("_You did not miss any subtopic bucket—nice consistency._")
        return
        # --- Mindmap ---
    if view == "mindmap":
        _invalidate_study_cache("mindmap_content", "mindmap")

        st.markdown('<div class="page-title">Mindmap</div>', unsafe_allow_html=True)

        if st.button("← Back to study tools", key="mindmap_back"):
            st.session_state.study_view = "hub"
            st.rerun()

        if st.button("Generate mindmap", type="primary"):
            with st.spinner("Building mindmap..."):
                prompt = prefix + """
Create a Mermaid mindmap.

STRICT FORMAT:
mindmap
  root((Main Topic))
    Branch 1
      Subtopic A
      Subtopic B
    Branch 2
      Subtopic C

Rules:
- Keep it hierarchical
- Keep it clean (not too long)
- No explanations, ONLY the Mermaid code
"""

                out, err = run_agent(
                    stack.mnemonics_agent,  # reuse agent (fast + simple)
                    prompt,
                )

                if err:
                    st.error(err)
                elif out:
                    st.session_state.mindmap_content = out.content

        if st.session_state.get("mindmap_content"):
            st.markdown("### Your mindmap")

            st.markdown(
                f"```mermaid\n{st.session_state.mindmap_content}\n```"
            )

            st.download_button(
                "Download mindmap",
                st.session_state.mindmap_content,
                file_name="mindmap.md"
            )

        return
    # --- Podcast ---
    if view == "podcast":
        from utils.storage import get_profile, build_profile_summary
        from utils.tts import text_to_speech

        _invalidate_study_cache("podcast_content", "podcast")

        st.markdown('<div class="page-title">🎙️ Podcast</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">A personalized audio episode based on your PDFs and profile.</div>',
            unsafe_allow_html=True,
        )

        if st.button("← Back to study tools", key="podcast_back"):
            st.session_state.study_view = "hub"
            st.rerun()

        if st.button("Generate podcast", type="primary"):
            profile_summary = build_profile_summary(uid)
            prompt = podcast_prompt(subject, unit, material, profile_summary)

            with st.spinner("Writing your personalized script..."):
                out, err = run_agent(stack.mnemonics_agent, prompt)  # reuse any fast agent
                if err:
                    st.error(err)
                else:
                    script = out.content.strip()
                    st.session_state.podcast_content = script

                    # Generate audio
                    with st.spinner("Converting script to audio..."):
                        try:
                            from pathlib import Path as _Path
                            audio_dir = _Path(__file__).parent.parent / "data" / "podcasts"
                            audio_path = text_to_speech(script, audio_dir)
                            st.session_state.podcast_audio_path = str(audio_path)
                        except Exception as e:
                            st.warning(f"Script generated but TTS failed: {e}")
                            st.session_state.podcast_audio_path = None

        if st.session_state.get("podcast_content"):
            st.markdown("### 📜 Podcast Script")
            st.markdown(st.session_state.podcast_content)

            if st.session_state.get("podcast_audio_path"):
                st.markdown("### 🔊 Listen")
                audio_bytes = open(st.session_state.podcast_audio_path, "rb").read()
                st.audio(audio_bytes, format="audio/mp3")

                st.download_button(
                    "⬇️ Download MP3",
                    audio_bytes,
                    file_name=f"{subject}_{unit}_podcast.mp3",
                    mime="audio/mp3",
                )
        return
    st.session_state.study_view = "hub"
    st.rerun()