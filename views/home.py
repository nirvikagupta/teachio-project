"""Home & My Work — Unified Project Hub & Progress Overview."""

import streamlit as st
from datetime import datetime
from utils.navigation import render_app_sidebar
from utils.styles import html, inject_styles, nav_to
from utils.storage import (
    get_user_tasks,
    get_latest_resumable_task,
    save_user_task,
    save_context_restore,
    delete_user_task,
    get_adhd_metrics,
    log_task_metric,
)
from utils.adhd_agents import decompose_assignment


def _seed_sample_cv_assignment(uid: str) -> str:
    brief = (
        "Compare two approaches for measuring computer-vision model performance "
        "(Approach A: IoU overlap vs. Approach B: Runtime efficiency) using 3–5 sources."
    )
    task = decompose_assignment("CV Assignment", brief, "Computer Vision", "Friday")
    task["subject"] = "Computer Vision"
    task["due_date"] = "Friday"
    task["original_brief"] = brief
    task["current_step_idx"] = 2
    task["status"] = "active"
    if len(task.get("steps", [])) >= 2:
        task["steps"][0]["completed"] = True
        task["steps"][1]["completed"] = True
    task["notes"] = "Found 2 sources. Comparing Approach A and B, stuck on measuring overlap."
    tid = save_user_task(uid, task)
    save_context_restore(
        uid,
        tid,
        {
            "working_on": "Comparing Approach A & B",
            "completed": ["Found 2 sources"],
            "tried": "Evaluated Approach A runtime",
            "stuck_on": "Measuring overlap",
            "last_thought": "Need a common metric.",
            "next_step": "Draft the comparison paragraph.",
        },
    )
    return tid


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id
    user_name = st.session_state.get("user_name", "Priya")

    hour = datetime.now().hour
    greeting = "Good morning" if hour < 12 else ("Good afternoon" if hour < 17 else "Good evening")

    c_head, c_new = st.columns([3.8, 1.3])
    with c_head:
        html(f"""
<div style="margin-bottom: 0.8rem;">
  <div class="rs-subhead">HOME · MY WORK · PROGRESS</div>
  <div class="page-title" style="margin:0;">{greeting}, <i>{user_name}</i></div>
</div>
""")
    with c_new:
        st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
        if st.button("+ New Assignment", type="primary", use_container_width=True):
            st.session_state.pop("decomposed_task", None)
            st.session_state["add_task_mode"] = "input"
            nav_to("add_task")

    all_tasks = get_user_tasks(uid)
    resumable_task = get_latest_resumable_task(uid)

    if not all_tasks:
        html("""
<div style="background:#ffffff; border-radius:26px; padding:3rem 2rem; text-align:center; border:1.5px solid #f2e2dc; margin:1rem 0;">
  <div class="rs-serif" style="font-size: 2.3rem; color: #2a1714; margin-bottom: 0.4rem;">
    Ready when you <i>are</i>
  </div>
  <div style="font-size: 0.96rem; color: #6b524c; max-width:420px; margin:0 auto;">
    Add an assignment to break it into bite-sized steps or explore concepts in the Study Space.
  </div>
</div>
""")
        _, c_b1, c_b2, _ = st.columns([1.2, 1.5, 1.5, 1.2])
        with c_b1:
            if st.button("Add Assignment →", type="primary", use_container_width=True):
                nav_to("add_task")
        with c_b2:
            if st.button("Load Sample Project", use_container_width=True):
                tid = _seed_sample_cv_assignment(uid)
                st.session_state["current_task_id"] = tid
                st.rerun()
        return

    # 1. PROGRESS BENTO ROW
    metrics = get_adhd_metrics(uid)
    total_steps_done = sum(sum(1 for s in t.get("steps", []) if s.get("completed")) for t in all_tasks)
    total_snaps = sum(len(t.get("context_history", [])) or (1 if t.get("context_restore") else 0) for t in all_tasks)
    total_restored = max(int(metrics.get("interrupted_sessions_resumed", 1)), len([t for t in all_tasks if t.get("context_restore")]))

    html(f"""
<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:14px; margin-bottom:1.4rem;">
  <div style="background:#e8f5e9; border-radius:22px; padding:1.15rem 1.35rem; display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div class="rs-subhead" style="color:#15803d; font-size:0.64rem;">STEPS COMPLETED</div>
      <div style="font-size:0.84rem; color:#166534; margin-top:2px;">Milestones finished</div>
    </div>
    <div class="rs-serif" style="font-size:2.4rem; color:#14532d; line-height:1;">{total_steps_done}</div>
  </div>
  <div style="background:#eff6ff; border-radius:22px; padding:1.15rem 1.35rem; display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div class="rs-subhead" style="color:#1d4ed8; font-size:0.64rem;">CONTEXT SNAPSHOTS</div>
      <div style="font-size:0.84rem; color:#1e40af; margin-top:2px;">Thinking states saved</div>
    </div>
    <div class="rs-serif" style="font-size:2.4rem; color:#1e3a8a; line-height:1;">{total_snaps}</div>
  </div>
  <div style="background:#f3e8ff; border-radius:22px; padding:1.15rem 1.35rem; display:flex; justify-content:space-between; align-items:center;">
    <div>
      <div class="rs-subhead" style="color:#6d28d9; font-size:0.64rem;">ACTIVE PROJECTS</div>
      <div style="font-size:0.84rem; color:#5b21b6; margin-top:2px;">{total_restored} seamless resumes</div>
    </div>
    <div class="rs-serif" style="font-size:2.4rem; color:#4c1d95; line-height:1;">{len(all_tasks)}</div>
  </div>
</div>
""")

    # 2. ALL ASSIGNMENTS ("My Work" Bento Grid)
    html("<div class='rs-serif' style='font-size:1.95rem; margin:0.4rem 0 0.8rem 0;'>Your <i>Assignments</i></div>")

    pastel_cards = [
        ("#fff5f6", "#fecdd3", "#d7262b"),
        ("#eff6ff", "#bfdbfe", "#2563eb"),
        ("#e8f5e9", "#bbf7d0", "#16a34a"),
        ("#f3e8ff", "#e9d5ff", "#7c3aed"),
    ]

    grid_cols = st.columns(2, gap="large")
    for idx, t in enumerate(all_tasks):
        steps = t.get("steps", [])
        done_cnt = sum(1 for s in steps if s.get("completed"))
        total_cnt = max(len(steps), 1)
        pct = int((done_cnt / total_cnt) * 100)
        cur_idx = min(t.get("current_step_idx", 0), max(0, len(steps) - 1))
        cur_step = steps[cur_idx] if steps else {}
        next_act = t.get("context_restore", {}).get("next_step") or cur_step.get("first_action", "Start next step")
        bg, border_c, accent_c = pastel_cards[idx % len(pastel_cards)]

        with grid_cols[idx % 2]:
            html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:26px; padding:1.45rem 1.65rem; margin-bottom:0.55rem; min-height:205px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 8px 22px rgba(160,40,50,0.04);">
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="background:{bg}; color:{accent_c}; border:1px solid {border_c}; font-size:0.68rem; font-weight:700; padding:3px 11px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
        Due {t.get('due_date', 'Friday')}
      </span>
      <span style="font-size:0.8rem; font-weight:700; color:#6b524c;">{done_cnt}/{total_cnt} steps ({pct}%)</span>
    </div>

    <div class="rs-serif" style="font-size:1.8rem; color:#2a1714; margin:0.35rem 0 0.5rem 0; line-height:1.15;">
      {t.get('title')}
    </div>

    <div class="adhd-progress-bg"><div class="adhd-progress-fg" style="width:{pct}%; background:{accent_c};"></div></div>
  </div>

  <div style="background:{bg}; border-radius:14px; padding:0.75rem 0.95rem; margin-top:0.75rem; font-size:0.86rem; color:#2a1714; line-height:1.45;">
    <b style="color:{accent_c};">Next action:</b> {next_act}
  </div>
</div>
""")
            b1, b2, b3, b4 = st.columns([1.2, 1.05, 1.0, 0.95], gap="small")
            with b1:
                if st.button("Workspace", key=f"h_ws_{t['id']}", type="primary", use_container_width=True):
                    st.session_state["current_task_id"] = t["id"]
                    st.session_state["session_mode"] = "workspace"
                    log_task_metric(uid, "tasks_resumed", 1)
                    nav_to("active_session")
            with b2:
                if st.button("Study Plan", key=f"h_st_{t['id']}", use_container_width=True):
                    st.session_state["current_task_id"] = t["id"]
                    st.session_state["decomposed_task"] = t
                    st.session_state["plan_edit_mode"] = False
                    nav_to("study_plan")
            with b3:
                if st.button("Restore", key=f"h_cr_{t['id']}", use_container_width=True):
                    st.session_state["current_task_id"] = t["id"]
                    st.session_state["interrupted_task_id"] = t["id"]
                    nav_to("context_restore")
            with b4:
                if st.button("Delete", key=f"h_del_{t['id']}", use_container_width=True):
                    delete_user_task(uid, t["id"])
                    st.rerun()
            st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)
