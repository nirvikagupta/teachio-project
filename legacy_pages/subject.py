"""Study tools grounded in unit PDFs."""

from __future__ import annotations

from collections import defaultdict
from typing import Optional

import streamlit as st


from utils.navigation import render_app_sidebar
from utils.pdf_text import extract_unit_combined_text, unit_material_fingerprint
from utils.storage import (
    get_unit_pdf_paths,
    update_unit_repetition,
    get_user_library,
    create_unit,
    save_pdf_to_unit,
    delete_unit,
    get_revision_schedule,
    build_profile_summary as get_profile_summary,
)
from utils.styles import inject_styles, nav_to

from utils.teaching_agents import (
    STUDY_MATERIAL_MAX_CHARS,
    build_teaching_stack,
    extract_json_object,
    groq_model_id,
    run_agent,
    study_prompt_prefix,
    podcast_prompt,
    mindmap_prompt,
    recap_prompt,
)
from utils.teachback import generate_teachback_round, evaluate_teachback_answer


def _study_source_tag(uid: str, subject: str, unit: str) -> str:
    paths = get_unit_pdf_paths(uid, subject, unit)
    fp = unit_material_fingerprint(paths)
    return f"{uid}|{subject}|{unit}|{fp}"


def _invalidate_study_cache(state_key: str, suffix: str, fingerprint: Optional[str] = None) -> None:
    uid = st.session_state.user_id
    subj = st.session_state.get("subject_name") or ""
    tag_key = f"_study_tag_{suffix}"
    cur = f"{uid}|{subj}|{fingerprint or ''}"
    if st.session_state.get(tag_key) != cur:
        st.session_state[state_key] = None
    st.session_state[tag_key] = cur

def render() -> None:
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return
    render_app_sidebar()

    uid = st.session_state.user_id
    subject = st.session_state.get("subject_name")

    if not subject:
        st.markdown('<div class="page-title">Subject</div>', unsafe_allow_html=True)
        st.warning("Please select a subject from the Home dashboard.")
        if st.button("Go to Home", use_container_width=True):
            nav_to("home")
            return

    st.markdown(
        f'<div class="breadcrumb">🏠 Home &rsaquo; <span>{subject}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="page-title">📚 {subject} Overview</div>', unsafe_allow_html=True)

    st.markdown("---")

    schedule = get_revision_schedule(uid)
    due_today = [r for r in schedule["due"] if r["subject"] == subject]
    upcoming_subj = [r for r in schedule["upcoming"] if r["subject"] == subject]

    # --- Nudge: chapters due today ---
    if due_today:
        units_due_str = ", ".join(f"**{r['unit']}**" for r in due_today)
        st.markdown(
            f'<div style="background: linear-gradient(135deg,#3a0a1a,#1a0a2a); border: 1.5px solid #ff4a6f88; '
            f'border-radius: 12px; padding: 1rem 1.5rem; margin-bottom: 1rem;">'
            f'<div style="color:#ff7ea8;font-weight:700;font-size:1rem;">'
            f'🔔 Revision due today: {units_due_str}</div>'
            f'<div style="color:#aa8899;font-size:0.85rem;margin-top:0.3rem;">'
            f'Select the chapter(s) below and use the Review tab to log your recall.</div>'
            f'</div>',
            unsafe_allow_html=True
        )

    # --- Subject-specific revision plan ---
    if upcoming_subj:
        with st.expander(f"📅 {subject} revision plan ({len(upcoming_subj)} upcoming)", expanded=False):
            from collections import defaultdict as _dd
            from datetime import datetime as _dt
            by_date: dict = _dd(list)
            for rev in upcoming_subj:
                by_date[rev["date"].strftime("%Y-%m-%d")].append(rev["unit"])
            for dk in sorted(by_date.keys()):
                label = _dt.strptime(dk, "%Y-%m-%d").strftime("%A, %b %d")
                units_list = " · ".join(by_date[dk])
                st.markdown(
                    f'<div style="border-left:3px solid #4a6fff;padding:0.5rem 0.9rem;margin-bottom:0.5rem;'
                    f'background:rgba(74,111,255,0.07);border-radius:0 6px 6px 0;">'
                    f'<b style="color:#8faeff;">📆 {label}</b><br>'
                    f'<span style="color:#ccd;">{units_list}</span></div>',
                    unsafe_allow_html=True
                )

    library = get_user_library(uid)

    subject_data = library.get(subject, {})
    units = subject_data.get("units", {})

    st.markdown("### 📂 Chapters & Files")
    if not units:
        st.caption("No chapters yet. Add one below to get started.")


    selected_units = []

    for idx, (unit_name, unit_data) in enumerate(units.items(), start=1):
        pdfs = unit_data.get("pdfs", [])
        
        # Checkbox for multi-select (default to checked if it was pre-selected from dashboard)
        pre_sel = st.session_state.get("pre_select_unit") == unit_name
        is_checked = st.checkbox(f"Step {idx}: {unit_name}", value=pre_sel, key=f"sel_{unit_name}")
        if is_checked:
            selected_units.append(unit_name)

        if st.session_state.get("pre_select_unit") == unit_name:
            st.session_state.pop("pre_select_unit", None)  # Consume the pre-select instruction

        bc1, bc2 = st.columns([8, 2])
        with bc1:
            for pdf_entry in pdfs:
                st.markdown(f"<div style='font-size: 13px; color: #8899cc; margin-left:2rem;'>📄 {pdf_entry['original_name']}</div>", unsafe_allow_html=True)
        with bc2:
            with st.popover("⚙️ Manage Chapter"):
                if st.button("🗑️ Delete Chapter", key=f"del_unit_{unit_name}", use_container_width=True):
                    delete_unit(uid, subject, unit_name)
                    st.rerun()
                st.caption("Upload PDF")
                with st.form(key=f"upload_form_{unit_name}", clear_on_submit=True, border=False):
                    uploaded_files = st.file_uploader("PDFs", type=["pdf"], accept_multiple_files=True, label_visibility="collapsed")
                    if st.form_submit_button("Upload") and uploaded_files:
                        for f in uploaded_files:
                            save_pdf_to_unit(uid, subject, unit_name, f.name, f.read())
                        st.rerun()
        st.divider()

    with st.form(key="new_unit_form", clear_on_submit=True, border=True):
        nc1, nc2 = st.columns([3, 1])
        with nc1:
            new_unit = st.text_input("New Chapter Name", label_visibility="collapsed", placeholder="e.g. Kinematics")
        with nc2:
            if st.form_submit_button("Add Chapter") and new_unit.strip():
                create_unit(uid, subject, new_unit.strip().title())
                st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### 🧠 AI Study Tools")
    st.markdown("Select one or more chapters above. The AI tools below will read from **all selected chapters** simultaneously!")

    if not selected_units:
        st.info("Check at least one chapter up top.")
        return

    paths = []
    for u in selected_units:
        paths.extend(get_unit_pdf_paths(uid, subject, u))

    if not paths:
        st.warning("The selected chapters have no PDF files. Please upload files to use AI tools.")
        return

    unit_name_str = " + ".join(selected_units)
    # Re-map the variables for the rest of the study.py script so they don't break
    unit = unit_name_str

    material = extract_unit_combined_text(paths, max_chars=STUDY_MATERIAL_MAX_CHARS)
    fp = unit_material_fingerprint(paths)
    prefix = study_prompt_prefix(subject, unit_name_str, material)

    stack = build_teaching_stack()

    if not stack:
        st.error("Groq API key is not set. Please restart.")
        return

    # Invalidate caches BEFORE drawing any UI — avoids mid-render session_state
    # writes that cause Streamlit to schedule a re-run and produce blinking tabs.
    _invalidate_study_cache("mnemonics_content", "mnem", fp)
    _invalidate_study_cache("quiz_data", "quiz", fp)
    _invalidate_study_cache("mindmap_data", "mindmap", fp)
    _invalidate_study_cache("podcast_content", "podcast", fp)
    _invalidate_study_cache("recap_content", "recap", fp)
    _invalidate_study_cache("teachback_state", "teachback", fp)

    if "recap_content" not in st.session_state:
        st.session_state.recap_content = None

    st.markdown("---")

    # Nudge for first-time use of the tools
    if st.session_state.get("recap_content") and not st.session_state.get("study_aids_nudge_shown"):
        st.toast("✨ Knowledge snapshot ready! Scroll down for more AI study aids.")
        st.session_state.study_aids_nudge_shown = True

    t_rev, t_mnem, t_map, t_pod, t_quiz, t_tb, t_asgn = st.tabs([
        "🧠 Review Mode", "🔤 Mnemonics", "🕸️ Mind Map", "🎙️ Podcast", "📝 Quiz", "🗣️ Teach Back", "📝 Grade Predictor"
    ])

    # --- Review ---
    with t_rev:
        st.markdown('<div class="page-title">🧠 Review Mode</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">AI-generated knowledge snapshot from your chapter PDFs, tailored to your profile.</div>',
            unsafe_allow_html=True,
        )

        # Auto-generate recap when content is None
        recap_container = st.container()
        with recap_container:
            if st.session_state.get("recap_content") is None:
                with st.spinner("✨ Building your knowledge snapshot..."):
                    profile_sum = get_profile_summary(uid)
                    out, err = run_agent(
                        stack.recap_agent,
                        recap_prompt(subject, unit, material, profile_sum)
                    )
                    if err:
                        st.error(f"Could not generate recap: {err}")
                        st.session_state.recap_content = "__error__"
                    elif out:
                        st.session_state.recap_content = out.content
                st.rerun()

            recap = st.session_state.get("recap_content", "")
            if recap and recap != "__error__":
                st.markdown(recap)
                if st.button("🔄 Regenerate", key="regen_recap"):
                    st.session_state.recap_content = None
                    st.rerun()
            elif recap == "__error__":
                if st.button("🔄 Try Again", key="retry_recap", type="primary"):
                    st.session_state.recap_content = None
                    st.rerun()
        
        st.markdown("""
            <div style="background: #fffbeb; border: 2px solid #000000; border-radius: 12px; padding: 1rem; text-align: center; margin-top: 1.5rem; margin-bottom: 2rem;">
                <div style="font-weight: 700; color: #000000; font-size: 1.1rem;">👇 Scroll down for Study Aids</div>
                <div style="font-size: 0.85rem; color: #000000;">Mind Maps, Quizzes, Podcasts and more are available in the tabs at the top!</div>
            </div>
        """, unsafe_allow_html=True)

        st.divider()

        st.markdown("### How easily did you recall this unit?")
        st.caption("Be honest to optimize your spaced repetition schedule!")
        fb_cols = st.columns(4)
        with fb_cols[0]:
            if st.button("Blanked (1)", key="fb_rev_1", use_container_width=True):
                for u in selected_units: update_unit_repetition(uid, subject, u, 1)
                st.success("Interval reset.")
                st.session_state.page = "home"
                st.rerun()
        with fb_cols[1]:
            if st.button("Hard (3)", key="fb_rev_3", use_container_width=True):
                for u in selected_units: update_unit_repetition(uid, subject, u, 3)
                st.success("Review logged!")
                st.session_state.page = "home"
                st.rerun()
        with fb_cols[2]:
            if st.button("Good (4)", key="fb_rev_4", use_container_width=True):
                for u in selected_units: update_unit_repetition(uid, subject, u, 4)
                st.success("Review logged!")
                st.session_state.page = "home"
                st.rerun()
        with fb_cols[3]:
            if st.button("Perfect (5)", key="fb_rev_5", type="primary", use_container_width=True):
                for u in selected_units: update_unit_repetition(uid, subject, u, 5)
                st.success("Review logged!")
                st.session_state.page = "home"
                st.rerun()

    # --- Mnemonics ---
    with t_mnem:
        st.markdown('<div class="page-title">Mnemonics</div>', unsafe_allow_html=True)

        if st.button("Generate mnemonics", type="primary"):
            with st.spinner("Creating mnemonics..."):
                out, err = run_agent(
                    stack.mnemonics_agent,
                    prefix + "Generate high-quality, creative, and memorable mnemonics for the key concepts. Use clear Markdown headings and bold text.",
                )
                if err:
                    st.error(err)
                elif out:
                    st.session_state.mnemonics_content = out.content

        if st.session_state.mnemonics_content:
            st.markdown("### Your mnemonics")
            st.markdown(st.session_state.mnemonics_content)

    # --- Quiz ---
    with t_quiz:
        st.markdown('<div class="page-title">Quiz</div>', unsafe_allow_html=True)

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
        # --- Mindmap ---
    with t_map:
        import json as _json
        import streamlit.components.v1 as components



        st.markdown('<div class="page-title">Mind Map</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">AI-generated from your PDFs — fully editable and downloadable.</div>',
            unsafe_allow_html=True,
        )


        if st.button("✨ Generate Mind Map", type="primary"):
            with st.spinner("Analysing your material and building the mind map…"):
                prompt = mindmap_prompt(subject, unit, material)
                out, err = run_agent(stack.mindmap_agent, prompt)
                if err:
                    st.error(err)
                elif out:
                    data = extract_json_object(out.content)
                    if data and "topic" in data:
                        st.session_state.mindmap_data = data
                        st.rerun()
                    else:
                        st.error("Could not parse mind map JSON. Raw response below.")
                        st.code(out.content)

        mindmap_data = st.session_state.get("mindmap_data")

        if mindmap_data:
            data_json = _json.dumps(mindmap_data)

            mindmap_html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"/>
<style>
:root{{--bg:#0d0f14;--sur:#161a24;--sur2:#1e2536;--bdr:#2a3350;--tx:#e0e4f4;--dim:#6a7494;--acc:#4a6fff;}}
*{{box-sizing:border-box;margin:0;padding:0;}}
html,body{{width:100%;height:100%;background:var(--bg);color:var(--tx);font-family:'Segoe UI',system-ui,sans-serif;overflow:hidden;}}
body{{display:flex;flex-direction:column;}}
#tb{{display:flex;align-items:center;gap:7px;padding:7px 12px;background:var(--sur);border-bottom:1px solid var(--bdr);flex-shrink:0;z-index:10;}}
.btn{{background:var(--sur2);border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:4px 10px;font-size:12px;cursor:pointer;transition:all .15s;white-space:nowrap;}}
.btn:hover{{background:#2a3550;border-color:var(--acc);color:#fff;}}
.btn.pri{{background:linear-gradient(135deg,#3a5fff,#5a3fff);border:none;color:#fff;font-weight:600;}}
.btn.pri:hover{{box-shadow:0 0 14px #3a5fff55;}}
.sep{{width:1px;height:18px;background:var(--bdr);flex-shrink:0;}}
.lbl{{font-size:11px;color:var(--dim);white-space:nowrap;}}
select{{background:var(--sur2);border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:4px 7px;font-size:12px;}}
#cw{{flex:1;position:relative;overflow:hidden;cursor:grab;}}
#cw.pan{{cursor:grabbing;}}
svg{{width:100%;height:100%;}}
/* Inspector */
#insp{{position:absolute;bottom:12px;left:50%;transform:translateX(-50%) translateY(28px);opacity:0;pointer-events:none;transition:all .22s cubic-bezier(.34,1.56,.64,1);background:var(--sur);border:1px solid var(--bdr);border-radius:14px;padding:9px 12px;display:flex;align-items:center;gap:9px;box-shadow:0 10px 36px #000a;z-index:50;white-space:nowrap;}}
#insp.on{{opacity:1;pointer-events:all;transform:translateX(-50%) translateY(0);}}
#insp-name{{font-size:11px;color:var(--dim);max-width:80px;overflow:hidden;text-overflow:ellipsis;}}
#ledit{{background:#090b11;border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:4px 9px;font-size:13px;width:150px;outline:none;transition:border-color .15s;}}
#ledit:focus{{border-color:var(--acc);}}
.ib{{background:var(--sur2);border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:4px 9px;font-size:12px;cursor:pointer;transition:all .15s;white-space:nowrap;}}
.ib:hover{{background:#2a3550;border-color:var(--acc);}}
.ib.g{{background:linear-gradient(135deg,#1e50ff,#4030ff);border:none;color:#fff;font-weight:600;}}
.ib.g:hover{{box-shadow:0 0 10px #3a5fff55;}}
.ib.r{{border-color:#ff4a6f44;color:#ff7ea8;}}
.ib.r:hover{{background:#3a1524;border-color:#ff4a6f;}}
#sw{{display:flex;gap:4px;align-items:center;}}
.sw{{width:18px;height:18px;border-radius:50%;cursor:pointer;border:2.5px solid transparent;transition:all .15s;flex-shrink:0;}}
.sw:hover{{transform:scale(1.3);}}
.sw.on{{border-color:#fff!important;transform:scale(1.3);}}
/* Float panels */
.fp{{position:absolute;display:none;background:var(--sur);border:1px solid var(--acc);border-radius:12px;padding:12px;box-shadow:0 10px 36px #000a;z-index:60;flex-direction:column;gap:8px;min-width:200px;}}
.fp.on{{display:flex;}}
.fp-ttl{{font-size:12px;font-weight:600;color:#8899cc;}}
.fi{{background:#090b11;border:1px solid var(--bdr);color:var(--tx);border-radius:7px;padding:6px 10px;font-size:13px;width:100%;outline:none;transition:border-color .15s;}}
.fi:focus{{border-color:var(--acc);}}
.fr{{display:flex;gap:6px;}}
#hint{{position:absolute;bottom:12px;right:12px;font-size:10px;color:var(--dim);pointer-events:none;z-index:5;}}
</style>
</head><body>
<div id="tb">
  <button class="btn" onclick="zi()">＋</button>
  <button class="btn" onclick="zo()">－</button>
  <button class="btn" onclick="rv()">⊙ Fit</button>
  <div class="sep"></div>
  <span class="lbl">Theme</span>
  <select onchange="applyTheme(this.value)">
    <option value="blue">Ocean Blue</option><option value="purple">Violet</option>
    <option value="green">Emerald</option><option value="amber">Amber</option>
    <option value="teal">Teal</option><option value="pink">Rose</option>
  </select>
  <div class="sep"></div>
  <button class="btn pri" onclick="dlPNG()">⬇ PNG</button>
  <span class="lbl" style="margin-left:auto;font-size:10px">Click node to select &amp; edit</span>
</div>
<div id="cw">
  <svg id="svg" xmlns="http://www.w3.org/2000/svg"><g id="rg"></g></svg>
  <div id="insp">
    <span id="insp-name">Node</span>
    <div class="sep"></div>
    <input type="text" id="ledit" placeholder="Edit label…"/>
    <button class="ib g" onclick="applyLbl()">✓</button>
    <div class="sep"></div>
    <div id="sw"></div>
    <div class="sep"></div>
    <button class="ib" onclick="showAdd()">＋ Child</button>
    <button class="ib r" onclick="showDel()">🗑</button>
  </div>
  <div id="ap" class="fp">
    <div class="fp-ttl">＋ New child node</div>
    <input type="text" class="fi" id="ai" placeholder="Enter label…"/>
    <div class="fr">
      <button class="ib g" onclick="doAdd()" style="flex:1">Add</button>
      <button class="ib" onclick="cancelAdd()">✕</button>
    </div>
  </div>
  <div id="dp" class="fp" style="border-color:#ff4a6f55;text-align:center;">
    <div class="fp-ttl" style="color:#ff7ea8">Delete this node?</div>
    <div style="font-size:12px;color:var(--dim)" id="dn"></div>
    <div class="fr">
      <button class="ib r" onclick="doDel()" style="flex:1">Delete</button>
      <button class="ib" onclick="cancelDel()">Cancel</button>
    </div>
  </div>
  <div id="hint">Scroll to zoom · drag to pan · click node to edit</div>
</div>
<script>
const RAW={data_json};
const TH={{
  blue:{{root:'#1d4ed8',L1:['#3a5fff','#1e40c0','#2547d4','#2d57e8','#1b46d4','#1e44cc'],L2:'#1e2a5e',edge:'#3a5fff99'}},
  purple:{{root:'#6d28d9',L1:['#7c3aed','#5b21b6','#8b5cf6','#6d28d9','#4c1d95','#7236d4'],L2:'#2e1065',edge:'#8b5cf699'}},
  green:{{root:'#047857',L1:['#059669','#065f46','#10b981','#047857','#0d7040','#08635a'],L2:'#022c22',edge:'#10b98199'}},
  amber:{{root:'#b45309',L1:['#d97706','#92400e','#f59e0b','#b45309','#c46008','#a65200'],L2:'#3a1a00',edge:'#f59e0b99'}},
  teal:{{root:'#0e7490',L1:['#0891b2','#155e75','#06b6d4','#0e7490','#0a7fa0','#167080'],L2:'#042030',edge:'#06b6d499'}},
  pink:{{root:'#be185d',L1:['#db2777','#9d174d','#ec4899','#be185d','#c72780','#b01e6a'],L2:'#3a0520',edge:'#ec489999'}},
}};
let theme=TH.blue;
const SWCOLS=[null,'#3a5fff','#7c3aed','#059669','#d97706','#0891b2','#db2777','#e11d48','#16a34a','#0284c7','#f97316','#64748b','#0f766e'];
const RDIST=[170,260,185]; // ring distance from parent per depth
let _nid=1;
function mkN(r,d=0){{
  const n={{id:_nid++,topic:String(r.topic||'Node').trim(),depth:d,color:null,children:[],cx:0,cy:0,r:36,collapsed:false}};
  (r.children||[]).forEach(c=>n.children.push(mkN(c,d+1)));
  return n;
}}
let tree=mkN(RAW),selId=null;
function nr(d){{return[56,38,27,20][Math.min(d,3)];}}
function leaves(n){{if(n.collapsed||!n.children.length)return 1;return n.children.reduce((s,c)=>s+leaves(c),0);}}
function layout(n,cx,cy,af,at,d){{
  n.cx=cx;n.cy=cy;n.r=nr(d);
  if(n.collapsed||!n.children.length)return;
  const dist=RDIST[Math.min(d,2)];
  const tot=leaves(n);let st=af;
  n.children.forEach(c=>{{
    const fr=leaves(c)/tot,arc=(at-af)*fr,mid=st+arc/2,rad=mid*Math.PI/180;
    layout(c,cx+dist*Math.cos(rad),cy+dist*Math.sin(rad),st,st+arc,d+1);
    st+=arc;
  }});
}}
function doLayout(){{
  const sv=document.getElementById('svg');
  layout(tree,sv.clientWidth/2||350,sv.clientHeight/2||260,-180,180,0);
}}
let vx=0,vy=0,vs=1,pan=false,ps=null;
const cw=document.getElementById('cw'),rg=document.getElementById('rg');
function apT(){{rg.setAttribute('transform',`translate(${{vx}},${{vy}}) scale(${{vs}})`);}}
function zi(){{vs=Math.min(vs*1.2,4);apT();}}
function zo(){{vs=Math.max(vs/1.2,.2);apT();}}
function rv(){{vx=0;vy=0;vs=1;apT();}}
cw.addEventListener('mousedown',e=>{{
  const t=e.target;
  if(t===cw||t.tagName==='svg'||t.id==='rg'){{pan=true;ps={{x:e.clientX-vx,y:e.clientY-vy}};cw.classList.add('pan');desel();}}
}});
window.addEventListener('mousemove',e=>{{if(!pan)return;vx=e.clientX-ps.x;vy=e.clientY-ps.y;apT();}});
window.addEventListener('mouseup',()=>{{pan=false;cw.classList.remove('pan');}});
cw.addEventListener('wheel',e=>{{e.preventDefault();vs=Math.min(Math.max(vs*(e.deltaY<0?1.12:.88),.2),4);apT();}},{{passive:false}});
function desel(){{selId=null;hideInsp();hideAdd();hideDel();render();}}
function nCol(n){{
  if(n.color)return n.color;
  if(n.depth===0)return theme.root;
  if(n.depth===1)return theme.L1[n.id%theme.L1.length];
  return theme.L2;
}}
const NS='http://www.w3.org/2000/svg';
function se(tag,a={{}}){{const e=document.createElementNS(NS,tag);Object.entries(a).forEach(([k,v])=>e.setAttribute(k,v));return e;}}
function render(){{
  rg.innerHTML='';doLayout();
  const eg=se('g');rg.appendChild(eg);drawE(eg,tree);
  const ng=se('g');rg.appendChild(ng);drawN(ng,tree);
  apT();
}}
function drawE(g,n){{
  if(n.collapsed)return;
  n.children.forEach(c=>{{
    const dx=c.cx-n.cx,dy=c.cy-n.cy,d=Math.sqrt(dx*dx+dy*dy)||1;
    const sx=n.cx+(n.r/d)*dx,sy=n.cy+(n.r/d)*dy,ex=c.cx-(c.r/d)*dx,ey=c.cy-(c.r/d)*dy;
    const mx=(sx+ex)/2,my=(sy+ey)/2;
    g.appendChild(se('path',{{d:`M${{sx}} ${{sy}} Q${{mx}} ${{my}} ${{ex}} ${{ey}}`,fill:'none',
      stroke:nCol(n),'stroke-width':n.depth===0?3:2,opacity:.55,'stroke-linecap':'round'}}));
    drawE(g,c);
  }});
}}
function drawN(g,n){{
  const col=nCol(n),sel=n.id===selId;
  const grp=se('g');grp.setAttribute('data-id',n.id);grp.style.cursor='pointer';
  if(sel)grp.appendChild(se('circle',{{cx:n.cx,cy:n.cy,r:n.r+10,fill:col,opacity:.2}}));
  if(n.depth>0)grp.appendChild(se('circle',{{cx:n.cx,cy:n.cy,r:n.r+3,fill:'none',stroke:col,'stroke-width':1.5,opacity:.35}}));
  grp.appendChild(se('circle',{{cx:n.cx,cy:n.cy,r:n.r,fill:col,stroke:sel?'#fff':'none','stroke-width':sel?2.5:0}}));
  const fs=n.depth===0?15:n.depth===1?12:10;
  const words=n.topic.split(' ');const mx2=n.r*1.5;
  let lines=[],line='';
  words.forEach(w=>{{const t=line?line+' '+w:w;if(t.length*fs*.55>mx2&&line){{lines.push(line);line=w;}}else line=t;}});
  if(line)lines.push(line);lines=lines.slice(0,3);
  const lh=fs*1.3,th=lines.length*lh;
  lines.forEach((ln,i)=>{{
    const t=se('text',{{x:n.cx,y:n.cy-th/2+lh/2+i*lh,'text-anchor':'middle','dominant-baseline':'central',
      fill:'#fff','font-size':fs,'font-family':'"Segoe UI",sans-serif','font-weight':n.depth===0?700:600,'pointer-events':'none'}});
    t.textContent=ln;grp.appendChild(t);
  }});
  if(n.children.length){{
    const tr2=n.r+4,tx=n.cx+tr2*.71,ty=n.cy-tr2*.71;
    const tb=se('circle',{{cx:tx,cy:ty,r:8,fill:'#0d0f14',stroke:col,'stroke-width':1.5}});
    const tt=se('text',{{x:tx,y:ty,'text-anchor':'middle','dominant-baseline':'central',fill:col,'font-size':11,'font-weight':700}});
    tt.textContent=n.collapsed?'+':'−';
    [tb,tt].forEach(el=>{{
      el.style.cursor='pointer';
      el.addEventListener('click',e=>{{e.stopPropagation();n.collapsed=!n.collapsed;render();}});
      grp.appendChild(el);
    }});
  }}
  grp.addEventListener('click',e=>{{e.stopPropagation();selId=n.id;render();openInsp(n);}});
  g.appendChild(grp);
  if(!n.collapsed)n.children.forEach(c=>drawN(g,c));
}}
const insp=document.getElementById('insp'),ledit=document.getElementById('ledit');
const inspName=document.getElementById('insp-name'),swDiv=document.getElementById('sw');
function buildSw(n){{
  swDiv.innerHTML='';
  SWCOLS.forEach(col=>{{
    const isAuto=col===null,dc=isAuto?nCol(n):col,act=isAuto?!n.color:n.color===col;
    const s=document.createElement('div');
    s.className='sw'+(act?' on':'');s.style.background=dc;s.title=isAuto?'Theme':col;
    s.addEventListener('click',()=>{{n.color=isAuto?null:col;render();openInsp(findN(selId)||n);}});
    swDiv.appendChild(s);
  }});
}}
function openInsp(n){{
  inspName.textContent=n.topic.length>14?n.topic.slice(0,13)+'…':n.topic;
  ledit.value=n.topic;buildSw(n);insp.classList.add('on');
}}
function hideInsp(){{insp.classList.remove('on');}}
function applyLbl(){{
  const n=findN(selId);if(!n)return;const v=ledit.value.trim();if(!v)return;
  n.topic=v;render();openInsp(n);
}}
ledit.addEventListener('keydown',e=>{{if(e.key==='Enter')applyLbl();}});
// Add panel
const ap=document.getElementById('ap'),ai=document.getElementById('ai');
let _ap=null;
function s2s(sx,sy){{return{{x:sx*vs+vx,y:sy*vs+vy}};}}
function posP(el,sx,sy){{
  const p=s2s(sx,sy);
  el.style.left=Math.max(4,Math.min(p.x,cw.clientWidth-215))+'px';
  el.style.top=Math.max(4,Math.min(p.y,cw.clientHeight-130))+'px';
}}
function showAdd(){{
  if(!selId)return;_ap=selId;const n=findN(selId);
  posP(ap,n.cx+n.r+12,n.cy-45);ai.value='';ap.classList.add('on');ap.style.display='flex';
  setTimeout(()=>ai.focus(),40);
}}
function doAdd(){{
  const lbl=ai.value.trim();if(!lbl)return;
  const par=findN(_ap);if(!par)return;
  par.children.push(mkN({{topic:lbl}},par.depth+1));
  par.collapsed=false;cancelAdd();render();openInsp(par);
}}
function cancelAdd(){{ap.classList.remove('on');ap.style.display='none';_ap=null;}}
ai.addEventListener('keydown',e=>{{if(e.key==='Enter')doAdd();if(e.key==='Escape')cancelAdd();}});
// Delete panel
const dp=document.getElementById('dp'),dn=document.getElementById('dn');
let _dt=null;
function showDel(){{
  if(!selId)return;const n=findN(selId);
  if(n.id===tree.id){{inspName.textContent='⚠ Cannot delete root';return;}}
  _dt=selId;dn.textContent='"'+n.topic+'"';
  posP(dp,n.cx-80,n.cy-n.r-85);dp.classList.add('on');dp.style.display='flex';
}}
function doDel(){{
  if(!_dt)return;const par=findP(_dt);
  if(par)par.children=par.children.filter(c=>c.id!==_dt);
  selId=null;_dt=null;hideDel();hideInsp();render();
}}
function cancelDel(){{hideDel();}}
function hideDel(){{dp.classList.remove('on');dp.style.display='none';_dt=null;}}
// Tree helpers
function findN(id,n=tree){{if(n.id===id)return n;for(const c of n.children){{const r=findN(id,c);if(r)return r;}}return null;}}
function findP(id,n=tree,p=null){{if(n.id===id)return p;for(const c of n.children){{const r=findP(id,c,n);if(r)return r;}}return null;}}
function applyTheme(t){{theme=TH[t]||TH.blue;render();}}
function dlPNG(){{
  const sv=document.getElementById('svg');
  const W=sv.clientWidth*2,H=sv.clientHeight*2;
  const xml=new XMLSerializer().serializeToString(sv);
  const ca=document.createElement('canvas');ca.width=W;ca.height=H;
  const ctx=ca.getContext('2d');ctx.fillStyle='#0d0f14';ctx.fillRect(0,0,W,H);
  const img=new Image();
  const bl=new Blob([xml],{{type:'image/svg+xml'}});
  const url=URL.createObjectURL(bl);
  img.onload=()=>{{ctx.scale(2,2);ctx.drawImage(img,0,0);const a=document.createElement('a');a.download='mindmap.png';a.href=ca.toDataURL('image/png');a.click();URL.revokeObjectURL(url);}};
  img.src=url;
}}
window.addEventListener('load',()=>setTimeout(()=>render(),60));
new ResizeObserver(()=>render()).observe(cw);
</script></body></html>"""
            components.html(mindmap_html, height=650, scrolling=False)
            st.caption("💡 Click a node to open the editor bar · change individual node colours with the swatches · add/delete via the floating panels · ⬇ PNG to save.")

    # --- Podcast ---
    with t_pod:
        from utils.tts import text_to_speech


        st.markdown('<div class="page-title">Podcast</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">A personalized audio episode based on your PDFs and profile.</div>',
            unsafe_allow_html=True,
        )


        if st.button("Generate podcast", type="primary"):
            profile_summary = get_profile_summary(uid)
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

    # --- Teach Back ---
    with t_tb:
        st.markdown('<div class="page-title">Teach Back</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">Active recall loop: explanation → your answer → feedback.</div>',
            unsafe_allow_html=True,
        )

        TB_PHASE_SETUP = "setup"
        TB_PHASE_EXPL = "explanation"
        TB_PHASE_QA = "qa"
        TB_PHASE_FB = "feedback"

        if "teachback_state" not in st.session_state or not isinstance(st.session_state.get("teachback_state"), dict):
            st.session_state.teachback_state = {"phase": TB_PHASE_SETUP}

        tb = st.session_state.teachback_state
        phase = tb.get("phase", TB_PHASE_SETUP)

        def _tb_reset() -> None:
            st.session_state.teachback_state = {"phase": TB_PHASE_SETUP}

        # Setup
        if phase == TB_PHASE_SETUP:
            rounds = st.number_input(
                "Rounds",
                min_value=3,
                max_value=10,
                value=5,
                step=1,
                key="tb_rounds",
                help="Use the arrows to increase/decrease rounds.",
            )
            if st.button("Start Teach Back", type="primary", use_container_width=True, key="tb_start"):
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
                else:
                    st.session_state.teachback_state = {
                        "phase": TB_PHASE_EXPL,
                        "rounds_total": rounds,
                        "round_idx": 0,
                        "current": rnd,
                        "last_answer": "",
                        "last_feedback": None,
                    }
                    st.rerun()

        # Explanation (ONLY explanation)
        elif phase == TB_PHASE_EXPL:
            cur = tb.get("current") or {}
            total = int(tb.get("rounds_total") or 5)
            idx = int(tb.get("round_idx") or 0) + 1
            st.caption(f"Round {idx} of {total} · Subtopic: {cur.get('subtopic','')}")
            st.markdown("### Explanation")
            st.write(cur.get("explanation", ""))
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("End session", use_container_width=True, key="tb_end1"):
                    _tb_reset()
                    st.rerun()
            with c2:
                if st.button("Next →", type="primary", use_container_width=True, key="tb_to_qa"):
                    tb["phase"] = TB_PHASE_QA
                    st.session_state.teachback_state = tb
                    st.rerun()

        # Q&A (ONLY question + answer input)
        elif phase == TB_PHASE_QA:
            cur = tb.get("current") or {}
            total = int(tb.get("rounds_total") or 5)
            idx = int(tb.get("round_idx") or 0) + 1
            st.caption(f"Round {idx} of {total} · Answer in your own words.")
            st.markdown("### Question")
            st.write(cur.get("question", ""))
            answer = st.text_area(
                "Your answer",
                value=tb.get("last_answer", ""),
                height=180,
                placeholder="Type your explanation here… (aim for 5–10 sentences)",
                label_visibility="collapsed",
                key="tb_answer",
            )
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("← Back", use_container_width=True, key="tb_back_to_expl"):
                    tb["last_answer"] = answer
                    tb["phase"] = TB_PHASE_EXPL
                    st.session_state.teachback_state = tb
                    st.rerun()
            with c2:
                if st.button("Check my answer", type="primary", use_container_width=True, key="tb_check"):
                    with st.spinner("Evaluating your explanation..."):
                        fb = evaluate_teachback_answer(
                            teachback_agent=stack.teachback_agent,
                            subject=subject,
                            unit=unit,
                            material=material,
                            subtopic=cur.get("subtopic", ""),
                            question=cur.get("question", ""),
                            key_ideas=[str(x) for x in (cur.get("key_ideas") or [])],
                            student_answer=answer,
                        )
                    if not fb:
                        st.error("Could not evaluate the answer. Please try again.")
                    else:
                        tb["last_answer"] = answer
                        tb["last_feedback"] = fb
                        tb["phase"] = TB_PHASE_FB
                        st.session_state.teachback_state = tb
                        st.rerun()

        # Feedback (ONLY feedback + next)
        elif phase == TB_PHASE_FB:
            cur = tb.get("current") or {}
            fb = tb.get("last_feedback") or {}
            total = int(tb.get("rounds_total") or 5)
            ridx = int(tb.get("round_idx") or 0)
            idx = ridx + 1
            st.caption(f"Round {idx} of {total} · Feedback")
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

            is_last = ridx >= (total - 1)
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("End session", use_container_width=True, key="tb_end2"):
                    _tb_reset()
                    st.rerun()
            with c2:
                if is_last:
                    if st.button("Finish", type="primary", use_container_width=True, key="tb_finish"):
                        _tb_reset()
                        st.rerun()
                else:
                    if st.button("Next round →", type="primary", use_container_width=True, key="tb_next"):
                        with st.spinner("Generating next explanation..."):
                            rnd = generate_teachback_round(
                                teachback_agent=stack.teachback_agent,
                                subject=subject,
                                unit=unit,
                                material=material,
                                focus_hint="",
                            )
                        if not rnd:
                            st.error("Could not generate the next round. Please try again.")
                        else:
                            tb["round_idx"] = ridx + 1
                            tb["current"] = rnd
                            tb["last_answer"] = ""
                            tb["last_feedback"] = None
                            tb["phase"] = TB_PHASE_EXPL
                            st.session_state.teachback_state = tb
                            st.rerun()

        else:
            _tb_reset()
            st.rerun()
    # --- Assignment Grade Predictor ---
    with t_asgn:
        st.markdown('<div class="page-title">Grade Predictor</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="page-subtitle">Predict your grade and get feedback on how to improve your assignment.</div>',
            unsafe_allow_html=True,
        )

        def _get_input_text(label: str, key_prefix: str) -> Optional[str]:
            st.markdown(f"**{label}**")
            mode = st.radio(f"Input mode for {label}", ["Text", "File (PDF)"], key=f"{key_prefix}_mode", label_visibility="collapsed")
            if mode == "Text":
                return st.text_area(f"{label} text", height=150, placeholder=f"Paste {label.lower()} here...", key=f"{key_prefix}_text", label_visibility="collapsed")
            else:
                uploaded = st.file_uploader(f"Upload {label} PDF", type=["pdf"], key=f"{key_prefix}_pdf", label_visibility="collapsed")
                if uploaded:
                    try:
                        from pypdf import PdfReader
                        reader = PdfReader(uploaded)
                        text = ""
                        for pg in reader.pages:
                            text += pg.extract_text() or ""
                        return text
                    except Exception as e:
                        st.error(f"Error reading PDF: {e}")
                return None

        col1, col2 = st.columns(2)
        with col1:
            instructions_text = _get_input_text("Assignment Instructions", "asgn_inst")
        with col2:
            rubric_text = _get_input_text("Grading Rubric (Optional)", "asgn_rubric")
        
        st.markdown("---")
        student_work_text = _get_input_text("Your Assignment / Work", "asgn_work")

        if st.button("Predict Grade", type="primary", use_container_width=True):
            if not instructions_text or not student_work_text:
                st.error("Please provide both the assignment instructions and your work.")
            else:
                with st.spinner("Analyzing your assignment..."):
                    # Truncate to avoid Groq TPM limits (6000 tokens)
                    # 4000 characters is roughly 1000 tokens.
                    MAX_CHARS = 4000 
                    it = (instructions_text[:MAX_CHARS] + "...") if len(instructions_text) > MAX_CHARS else instructions_text
                    rt = ((rubric_text[:MAX_CHARS] + "...") if len(rubric_text) > MAX_CHARS else rubric_text) if rubric_text else None
                    sw = (student_work_text[:MAX_CHARS] + "...") if len(student_work_text) > MAX_CHARS else student_work_text

                    from utils.teaching_agents import assignment_predictor_prompt
                    asgn_prompt = assignment_predictor_prompt(it, rt, sw)
                    out, err = run_agent(stack.assignment_advisor_agent, asgn_prompt)
                    if err:
                        st.error(err)
                    else:
                        st.session_state.assignment_predictor_result = out.content
                        st.rerun()

        if st.session_state.get("assignment_predictor_result"):
            st.markdown("---")
            st.markdown(st.session_state.assignment_predictor_result)
            if st.button("Clear Results"):
                st.session_state.assignment_predictor_result = None
                st.rerun()
