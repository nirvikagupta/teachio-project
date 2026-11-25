"""Study Plan Page — Dedicated page for viewing, editing, customizing, and finalizing the Study & Action Plan."""

import streamlit as st
from utils.navigation import render_app_sidebar, render_assignment_journey_bar
from utils.styles import html, inject_styles, nav_to
from utils.adhd_agents import decompose_assignment
from utils.storage import (
    get_user_tasks,
    save_user_task,
    save_context_restore,
    save_active_auth_session,
    get_task_by_id,
    get_latest_resumable_task,
)
from views.add_task import _create_and_save_assignment


def _renumber_and_save_plan(uid: str, task: dict) -> dict:
    """Re-indexes all steps cleanly, persists the finalized plan, and refreshes Context Restore."""
    steps = task.get("steps", [])
    for idx, s in enumerate(steps):
        s["step_number"] = idx + 1
        s["completed"] = bool(s.get("completed", False))
        s["status"] = "Done" if s["completed"] else ("Ready" if idx == 0 else "Next")
    task["current_step_idx"] = min(task.get("current_step_idx", 0), max(0, len(steps) - 1))
    tid = save_user_task(uid, task)
    task["id"] = tid
    if steps:
        cur_s = steps[task["current_step_idx"]]
        save_context_restore(
            uid,
            tid,
            {
                "working_on": f"{cur_s.get('phase', 'Step')} — {cur_s.get('title', '')}",
                "completed": [s.get("title") for s in steps if s.get("completed")] or ["Finalized custom study plan"],
                "tried": f"Customized {len(steps)}-step study plan",
                "stuck_on": "None",
                "last_thought": task.get("simplified_brief", ""),
                "next_step": cur_s.get("first_action", "Begin first action"),
            },
        )
    st.session_state["decomposed_task"] = get_task_by_id(uid, tid) or task
    return st.session_state["decomposed_task"]


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    all_tasks = get_user_tasks(uid)
    if not all_tasks:
        d_title = "CV Assignment"
        d_brief = (
            "Compare two approaches for measuring computer-vision model performance "
            "(Approach A: IoU overlap metrics vs. Approach B: Runtime efficiency)."
        )
        _create_and_save_assignment(uid, d_title, d_brief, "Coursework", "Friday")
        all_tasks = get_user_tasks(uid)

    task_map = {t["id"]: t for t in all_tasks if t.get("id")}
    cur_tid = st.session_state.get("current_task_id")
    if cur_tid and cur_tid in task_map:
        decomposed = task_map[cur_tid]
    else:
        decomposed = get_latest_resumable_task(uid) or all_tasks[0]
        st.session_state["current_task_id"] = decomposed["id"]

    st.session_state["decomposed_task"] = decomposed

    # Interactive 4-Step Journey Bar at the top
    render_assignment_journey_bar("plan")

    title = decomposed.get("title", "CV Assignment")
    due_date = decomposed.get("due_date", "Friday")
    simplified = decomposed.get("simplified_brief", "")
    steps = decomposed.get("steps", [])
    task_id = decomposed.get("id", "draft")
    edit_mode = bool(st.session_state.get("plan_edit_mode", False))

    c_hdr, c_sw, c_edit_toggle, c_b2 = st.columns([2.3, 1.4, 1.25, 1.05], gap="small")
    with c_hdr:
        html(f"""
<div style="margin-bottom: 0.4rem;">
  <span class="rs-subhead">STUDY & ACTION PLAN · DUE {due_date.upper()}</span>
  <div class="page-title" style="margin:0; font-size:2.3rem;">{title}</div>
</div>
""")
    with c_sw:
        if task_map:
            tid_list = list(task_map.keys())
            picked_plan_tid = st.selectbox(
                "Assignment:",
                options=tid_list,
                format_func=lambda tid: task_map[tid].get("title", "Assignment"),
                index=tid_list.index(task_id) if task_id in tid_list else 0,
                key="plan_header_task_picker",
            )
            if picked_plan_tid != task_id:
                st.session_state["current_task_id"] = picked_plan_tid
                st.session_state["decomposed_task"] = task_map[picked_plan_tid]
                save_active_auth_session(uid, st.session_state.get("user_name", "Student"), True, picked_plan_tid)
                st.rerun()
    with c_edit_toggle:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        if st.button(
            "✓ View Plan" if edit_mode else "✎ Edit Plan",
            type="secondary" if edit_mode else "primary",
            use_container_width=True,
            key="btn_toggle_plan_edit",
        ):
            st.session_state["plan_edit_mode"] = not edit_mode
            st.rerun()
    with c_b2:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("+ New Assignment", use_container_width=True):
            st.session_state["plan_edit_mode"] = False
            nav_to("add_task")

    pastel_tints = [
        ("#fff5f6", "#fecdd3", "#d7262b"),  # Blush
        ("#eff6ff", "#bfdbfe", "#2563eb"),  # Powder Blue
        ("#fefce8", "#fde68a", "#b45309"),  # Soft Amber
        ("#f3e8ff", "#e9d5ff", "#7c3aed"),  # Soft Lavender
        ("#f0fdf4", "#bbf7d0", "#16a34a"),  # Soft Sage
        ("#fff7ed", "#fed7aa", "#ea580c"),  # Warm Peach
    ]

    # -------------------------------------------------------------------------
    # EDIT MODE: Full customization of Goal, Due Date, Steps, Subtasks, Order
    # -------------------------------------------------------------------------
    if edit_mode:
        html("""
<div style="background:#fff5f6; border:1.5px solid #fecdd3; border-radius:20px; padding:0.9rem 1.35rem; margin-bottom:1rem; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
  <div>
    <div class="rs-subhead" style="font-size:0.65rem;">CUSTOMIZE YOUR STUDY PLAN</div>
    <div style="font-size:0.92rem; color:#2a1714;">Edit any step title, first action, time estimate, or checklist items — or reorder, add, and remove steps before finalizing.</div>
  </div>
</div>
""")
        meta_c1, meta_c2, meta_c3 = st.columns([1.5, 0.8, 2.2], gap="medium")
        with meta_c1:
            edited_title = st.text_input("Assignment Title", value=title, key=f"ed_plan_title_{task_id}")
        with meta_c2:
            edited_due = st.text_input("Due Date", value=due_date, key=f"ed_plan_due_{task_id}")
        with meta_c3:
            edited_goal = st.text_input("Overall Study Goal", value=simplified, key=f"ed_plan_goal_{task_id}")

        decomposed["title"] = edited_title.strip() or title
        decomposed["due_date"] = edited_due.strip() or due_date
        decomposed["simplified_brief"] = edited_goal.strip() or simplified

        st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

        grid_cols = st.columns(2, gap="medium")
        step_to_delete = None
        step_to_swap = None

        for i, step in enumerate(steps):
            bg_col, border_col, accent_col = pastel_tints[i % len(pastel_tints)]
            with grid_cols[i % 2]:
                html(f"""
<div style="background:{bg_col}; border:1.5px solid {border_col}; border-radius:20px 20px 0 0; padding:0.75rem 1.15rem; margin-top:0.2rem; display:flex; justify-content:space-between; align-items:center;">
  <span style="background:#ffffff; color:{accent_col}; border:1px solid {border_col}; font-size:0.68rem; font-weight:700; padding:3px 10px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
    STEP 0{i + 1}
  </span>
  <span style="font-size:0.76rem; font-weight:700; color:{accent_col};">Editable Stage</span>
</div>
""")
                with st.container():
                    r1_c1, r1_c2 = st.columns([2.1, 1.1])
                    with r1_c1:
                        new_phase = st.text_input(
                            "Stage Label",
                            value=step.get("phase", f"Stage {i+1}"),
                            key=f"ed_phase_{task_id}_{i}",
                        )
                    with r1_c2:
                        new_est = st.number_input(
                            "Minutes",
                            min_value=2,
                            max_value=180,
                            value=int(step.get("est_minutes", 20)),
                            step=5,
                            key=f"ed_est_{task_id}_{i}",
                        )

                    new_st_title = st.text_input(
                        "Step Objective",
                        value=step.get("title", ""),
                        key=f"ed_st_title_{task_id}_{i}",
                    )
                    new_first_act = st.text_input(
                        "First Concrete Action (Start Mode Prompt)",
                        value=step.get("first_action", ""),
                        key=f"ed_first_act_{task_id}_{i}",
                    )
                    subtasks_list = step.get("subtasks") or [new_first_act]
                    new_subtasks_raw = st.text_area(
                        "Checklist Subtasks (one per line)",
                        value="\n".join(str(x) for x in subtasks_list if str(x).strip()),
                        height=76,
                        key=f"ed_subtasks_{task_id}_{i}",
                    )

                    step["phase"] = new_phase.strip() or f"Step {i+1}"
                    step["est_minutes"] = int(new_est)
                    step["title"] = new_st_title.strip() or f"Complete {step['phase']}"
                    step["first_action"] = new_first_act.strip() or step["title"]
                    parsed_subs = [ln.strip() for ln in new_subtasks_raw.split("\n") if ln.strip()]
                    step["subtasks"] = parsed_subs if parsed_subs else [step["first_action"]]

                    act_c1, act_c2, act_c3 = st.columns([1, 1, 1], gap="small")
                    with act_c1:
                        if st.button("↑ Up", key=f"ed_up_{task_id}_{i}", disabled=(i == 0), use_container_width=True):
                            step_to_swap = (i, i - 1)
                    with act_c2:
                        if st.button("↓ Down", key=f"ed_dn_{task_id}_{i}", disabled=(i == len(steps) - 1), use_container_width=True):
                            step_to_swap = (i, i + 1)
                    with act_c3:
                        if st.button("✕ Remove", key=f"ed_del_{task_id}_{i}", disabled=(len(steps) <= 1), use_container_width=True):
                            step_to_delete = i

                st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)

        if step_to_swap is not None:
            idx_a, idx_b = step_to_swap
            steps[idx_a], steps[idx_b] = steps[idx_b], steps[idx_a]
            _renumber_and_save_plan(uid, decomposed)
            st.rerun()

        if step_to_delete is not None:
            steps.pop(step_to_delete)
            _renumber_and_save_plan(uid, decomposed)
            st.rerun()

        st.markdown("<div style='height:0.3rem;'></div>", unsafe_allow_html=True)
        bar_c1, bar_c2, bar_c3, bar_c4 = st.columns([1, 1, 1, 1.2], gap="small")
        with bar_c1:
            if st.button("+ Add Step", use_container_width=True, key=f"btn_add_step_{task_id}"):
                next_num = len(steps) + 1
                steps.append({
                    "step_number": next_num,
                    "phase": f"Step {next_num}",
                    "title": "New custom study milestone",
                    "est_minutes": 15,
                    "first_action": "Write the first 3 bullet points for this section.",
                    "two_minute_version": "Open your notes and write 1 heading.",
                    "subtasks": ["Write key bullet points", "Review against assignment brief"],
                    "why_it_matters": "Keeps your custom study workflow moving forward.",
                    "completed": False,
                    "status": "Next",
                })
                _renumber_and_save_plan(uid, decomposed)
                st.rerun()
        with bar_c2:
            if st.button("↻ AI Reset", use_container_width=True, key=f"btn_regen_plan_{task_id}"):
                with st.spinner("Regenerating study plan from brief..."):
                    orig_brief = decomposed.get("original_brief") or simplified
                    _create_and_save_assignment(uid, decomposed["title"], orig_brief, decomposed.get("subject", "Coursework"), decomposed["due_date"])
                    st.session_state["plan_edit_mode"] = True
                st.rerun()
        with bar_c3:
            if st.button("✓ Save Plan", use_container_width=True, key=f"btn_finalize_plan_{task_id}"):
                _renumber_and_save_plan(uid, decomposed)
                st.session_state["plan_edit_mode"] = False
                st.rerun()
        with bar_c4:
            if st.button("✓ Finalize & Start →", type="primary", use_container_width=True, key=f"btn_finalize_go_{task_id}"):
                finalized = _renumber_and_save_plan(uid, decomposed)
                st.session_state["plan_edit_mode"] = False
                st.session_state["current_task_id"] = finalized["id"]
                st.session_state["session_mode"] = "workspace"
                nav_to("active_session")
        return

    # -------------------------------------------------------------------------
    # FINALIZED PLAN VIEW: Clean 2x3 Pastel Bento Grid + Edit Button on Every Step
    # -------------------------------------------------------------------------
    html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:20px; padding:1rem 1.35rem; margin-bottom:1.1rem; display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap;">
  <div style="font-size:0.96rem; color:#5b4540;">
    <b style="color:#2a1714;">Goal:</b> {simplified}
  </div>
  <span style="background:#e8f5e9; color:#15803d; font-size:0.72rem; font-weight:700; padding:4px 12px; border-radius:99px; letter-spacing:0.06em; text-transform:uppercase;">
    ✓ {len(steps)}-Step Plan Ready · Click '✎ Edit Plan' anytime to customize
  </span>
</div>
""")

    grid_cols = st.columns(2, gap="medium")
    for i, step in enumerate(steps):
        step_num = i + 1
        phase = step.get("phase") or f"Step {step_num}"
        step_title = step.get("title", "")
        est_min = step.get("est_minutes", 20)
        first_act = step.get("first_action", "")
        subtasks = step.get("subtasks", [])
        is_done = bool(step.get("completed", False))
        bg_col, border_col, accent_col = pastel_tints[i % len(pastel_tints)]

        subtask_pills = "".join(
            f"<div style='font-size:0.8rem; color:#5b4540; margin-top:3px;'>• {st_item}</div>"
            for st_item in subtasks[:3]
        )

        with grid_cols[i % 2]:
            html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:24px; padding:1.3rem 1.45rem; margin-bottom:0.55rem; min-height:195px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 8px 22px rgba(160,40,50,0.04);">
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.4rem;">
      <span style="background:{bg_col}; color:{accent_col}; border:1px solid {border_col}; font-size:0.7rem; font-weight:700; padding:3px 10px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
        0{step_num} · {phase}
      </span>
      <span style="font-size:0.78rem; color:#6b524c; font-weight:600;">
        {'✓ Completed' if is_done else f'~{est_min} min'}
      </span>
    </div>
    <div class="rs-serif" style="font-size:1.45rem; color:#2a1714; line-height:1.15; margin:0.25rem 0 0.45rem 0;">
      {step_title}
    </div>
    <div style="margin-bottom:0.65rem;">
      {subtask_pills}
    </div>
  </div>
  <div style="background:{bg_col}; border-radius:14px; padding:0.7rem 0.95rem; font-size:0.86rem; color:#2a1714;">
    <b style="color:{accent_col};">First action:</b> {first_act}
  </div>
</div>
""")
            btn_c1, btn_c2 = st.columns([2.2, 1], gap="small")
            with btn_c1:
                if st.button(
                    f"{'Review' if is_done else 'Start'} {phase} →",
                    key=f"start_bd_step_{i}",
                    type="primary" if i == decomposed.get("current_step_idx", 0) else "secondary",
                    use_container_width=True,
                ):
                    decomposed["current_step_idx"] = i
                    decomposed["status"] = "active"
                    saved_tid = save_user_task(uid, decomposed)
                    save_context_restore(
                        uid,
                        saved_tid,
                        {
                            "working_on": f"{phase} — {step_title}",
                            "completed": [s.get("title") for s in steps if s.get("completed")] or ["Finalized study plan"],
                            "tried": f"Started {phase}",
                            "stuck_on": "None",
                            "last_thought": simplified,
                            "next_step": first_act,
                        },
                    )
                    st.session_state["current_task_id"] = saved_tid
                    st.session_state["session_mode"] = "start_mode"
                    nav_to("active_session")
            with btn_c2:
                if st.button("✎ Edit", key=f"quick_ed_step_{i}", use_container_width=True):
                    st.session_state["plan_edit_mode"] = True
                    st.rerun()
            st.markdown("<div style='height:0.45rem;'></div>", unsafe_allow_html=True)
