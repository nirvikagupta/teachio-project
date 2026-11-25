"""New Assignment Page — Strictly for uploading or pasting a new assignment brief."""

import io
import os
import streamlit as st
from utils.navigation import render_app_sidebar
from utils.styles import html, inject_styles, nav_to
from utils.adhd_agents import decompose_assignment
from utils.storage import (
    save_user_task,
    save_context_restore,
    save_active_auth_session,
    log_task_metric,
    get_task_by_id,
)


def _extract_uploaded_text(uploaded_file) -> str:
    if not uploaded_file:
        return ""
    name = uploaded_file.name.lower()
    raw_bytes = uploaded_file.getvalue()
    if name.endswith(".txt") or name.endswith(".md"):
        return raw_bytes.decode("utf-8", errors="ignore").strip()
    if name.endswith(".pdf"):
        for mod_name in ("pypdf", "PyPDF2"):
            try:
                mod = __import__(mod_name)
                reader = mod.PdfReader(io.BytesIO(raw_bytes))
                txt = "\n".join(page.extract_text() or "" for page in reader.pages).strip()
                if txt:
                    return txt
            except Exception:
                pass
        return f"Assignment: {uploaded_file.name}\nCompare core approaches using peer-reviewed sources and draft a report."
    if name.endswith(".docx"):
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
                xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)
            paragraphs = [elem.text for elem in tree.iter() if elem.text]
            txt = " ".join(paragraphs).strip()
            if txt:
                return txt
        except Exception:
            pass
        return f"Assignment: {uploaded_file.name}"
    return raw_bytes.decode("utf-8", errors="ignore").strip()


def _create_and_save_assignment(uid: str, title: str, brief: str, subject: str, due_date: str, uploaded_filename: str = "") -> dict:
    result = decompose_assignment(title, brief, subject, due_date)
    result["title"] = title.strip() or result.get("title", "Assignment")
    result["subject"] = subject.strip() or "Coursework"
    result["due_date"] = due_date.strip() or "Friday"
    result["original_brief"] = brief.strip()
    if uploaded_filename:
        result["uploaded_materials"] = [uploaded_filename]
    for idx, s in enumerate(result.get("steps", [])):
        s["step_number"] = idx + 1
        s["completed"] = bool(s.get("completed", False))
        s["status"] = "Done" if s["completed"] else ("Ready" if idx == 0 else "Next")
    result["current_step_idx"] = 0
    result["status"] = "active"
    task_id = save_user_task(uid, result)
    result["id"] = task_id

    first_st = result.get("steps", [{}])[0] if result.get("steps") else {}
    save_context_restore(
        uid,
        task_id,
        {
            "working_on": f"{first_st.get('phase', 'Understand')} — {first_st.get('title', 'Getting started')}",
            "completed": ["Assignment uploaded"],
            "tried": f"Reviewed {result['title']}",
            "stuck_on": "Starting first action",
            "last_thought": result.get("simplified_brief", ""),
            "next_step": first_st.get("first_action", "Find one paper comparing Approach A and B."),
        },
    )
    st.session_state["current_task_id"] = task_id
    st.session_state["decomposed_task"] = get_task_by_id(uid, task_id) or result
    save_active_auth_session(uid, st.session_state.get("user_name", "Student"), True, task_id)
    for prefix in ("extracted_concepts_", "study_cards_", "study_quiz_", "study_mindmap_"):
        st.session_state.pop(f"{prefix}{task_id}", None)
    st.session_state.pop("reading_layer_output", None)
    st.session_state["reading_layer_mode"] = "original"
    return st.session_state["decomposed_task"]


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    html("""
<div style="margin-bottom: 1rem;">
  <div class="rs-subhead">ADD NEW ASSIGNMENT</div>
  <div class="page-title" style="margin:0;">Add Your <i>Assignment</i></div>
</div>
""")

    default_brief = (
        "Compare two approaches for measuring computer-vision model performance "
        "(Approach A: IoU overlap metrics vs. Approach B: Runtime efficiency). "
        "Use 3–5 sources and justify which is better for real-time use."
    )

    col_left, col_right = st.columns([1.35, 1], gap="large")

    with col_left:
        col_title, col_due = st.columns([2.4, 1.2])
        with col_title:
            task_title = st.text_input(
                "Assignment Title",
                value=st.session_state.get("draft_title_input", ""),
                key="draft_title_input",
                placeholder="e.g. Macroeconomics Essay, Biology Lab Report, CV Assignment...",
            )
        with col_due:
            due_date = st.text_input(
                "Due Date",
                value=st.session_state.get("draft_due_input", "Friday"),
                key="draft_due_input",
            )

        if "draft_brief_area" not in st.session_state:
            st.session_state["draft_brief_area"] = ""

        brief_text = st.text_area(
            "Assignment Brief",
            height=165,
            key="draft_brief_area",
            placeholder="Paste your assignment prompt, syllabus instructions, or essay question here...",
        )
        if st.button("Prefill Sample Brief", key="btn_prefill_sample"):
            st.session_state["draft_title_input"] = "CV Assignment"
            st.session_state["draft_brief_area"] = default_brief
            st.rerun()

    with col_right:
        html("""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:22px; padding:1.2rem 1.4rem; margin-bottom:0.8rem;">
  <div class="rs-subhead" style="font-size:0.65rem;">UPLOAD BRIEF FILE</div>
  <div class="rs-serif" style="font-size:1.45rem; margin:2px 0 4px 0;">Drop a PDF, DOCX, or TXT</div>
  <div style="font-size:0.84rem; color:#6b524c;">We'll extract the requirements automatically.</div>
</div>
""")
        up_file = st.file_uploader(
            "Upload file",
            type=["pdf", "docx", "txt"],
            key="stage01_file_uploader",
            label_visibility="collapsed",
        )

        uploaded_filename = ""
        if up_file is not None:
            uploaded_filename = up_file.name
            if st.session_state.get("last_uploaded_filename") != uploaded_filename:
                extracted = _extract_uploaded_text(up_file)
                st.session_state["last_uploaded_filename"] = uploaded_filename
                st.session_state["draft_brief_area"] = extracted
                clean_stem = os.path.splitext(uploaded_filename)[0].replace("_", " ").replace("-", " ").title()
                if clean_stem:
                    st.session_state["draft_title_input"] = clean_stem
                st.rerun()
            st.success(f"Loaded **{uploaded_filename}**")

    st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
    col_study, col_decompose = st.columns(2, gap="medium")

    with col_study:
        if st.button("📖 Create & Learn Concepts First →", use_container_width=True, key="btn_path_a_study"):
            if not task_title.strip() or not brief_text.strip():
                st.error("Please enter a title and brief.")
                return
            with st.spinner("Extracting concepts & opening Learn Concepts..."):
                _create_and_save_assignment(uid, task_title, brief_text, "Coursework", due_date, uploaded_filename)
                st.session_state.pop("draft_title_input", None)
                st.session_state.pop("draft_brief_area", None)
            nav_to("resources")

    with col_decompose:
        if st.button("🗓️ Create & Open Study Plan →", type="primary", use_container_width=True, key="btn_path_b_decompose"):
            if not task_title.strip() or not brief_text.strip():
                st.error("Please enter a title and brief.")
                return
            with st.spinner("Generating your editable study & action plan..."):
                _create_and_save_assignment(uid, task_title, brief_text, "Coursework", due_date, uploaded_filename)
                st.session_state["plan_edit_mode"] = True
                st.session_state.pop("draft_title_input", None)
                st.session_state.pop("draft_brief_area", None)
                log_task_metric(uid, "tasks_started", 1)
            nav_to("study_plan")
