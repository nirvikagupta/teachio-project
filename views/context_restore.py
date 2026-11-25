"""Context Restore — Dedicated Cognitive Continuity & Snapshot History Page."""

import streamlit as st
from utils.navigation import render_app_sidebar, render_assignment_journey_bar
from utils.styles import html, inject_styles, nav_to
from utils.storage import (
    get_task_by_id,
    get_latest_resumable_task,
    get_user_tasks,
    save_user_task,
    save_context_restore,
    save_active_auth_session,
    restore_context_from_history,
    log_task_metric,
)
from utils.adhd_agents import decompose_assignment
from views.active_session import _build_instant_snapshot


def _create_default_cv_task_with_context(uid: str) -> dict:
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
            "last_thought": "Need a unified overlap table.",
            "next_step": "Draft the comparison paragraph.",
        },
    )
    return get_task_by_id(uid, tid)


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    all_user_tasks = get_user_tasks(uid)
    task_id = st.session_state.get("interrupted_task_id") or st.session_state.get("current_task_id")
    task = get_task_by_id(uid, task_id) if task_id else None
    if not task:
        task = get_latest_resumable_task(uid)
    if not task and all_user_tasks:
        task = all_user_tasks[0]
    if not task:
        task = _create_default_cv_task_with_context(uid)
        all_user_tasks = get_user_tasks(uid)

    st.session_state["current_task_id"] = task["id"]

    # Interactive 4-Step Journey Bar at the top
    render_assignment_journey_bar("restore")

    if st.session_state.pop("snapshot_saved_banner", False):
        st.success(f"✓ Snapshot saved for **{task.get('title')}**! You can safely close the tab or resume anytime.")

    # Assignment switcher + Instant Snapshot Capture button
    c_hdr, c_sw, c_new_snap = st.columns([2.6, 1.5, 1.2], gap="medium")
    with c_hdr:
        html(f"""
<div style="margin-bottom: 0.5rem;">
  <span class="rs-subhead">COGNITIVE SNAPSHOT · SAVED {task.get('context_restore', {}).get('display_time', 'RECENTLY').upper()}</span>
  <div class="page-title" style="margin:0; font-size:2.3rem;">Context <i>Snapshot</i></div>
</div>
""")
    with c_sw:
        task_map = {t["id"]: t for t in all_user_tasks if t.get("id")}
        tid_list = list(task_map.keys())
        picked_tid = st.selectbox(
            "Assignment:",
            options=tid_list,
            format_func=lambda tid: task_map[tid].get("title", "Assignment"),
            index=tid_list.index(task["id"]) if task["id"] in tid_list else 0,
            key="cr_header_task_picker",
        )
        if picked_tid != task["id"]:
            st.session_state["current_task_id"] = picked_tid
            st.session_state["interrupted_task_id"] = picked_tid
            save_active_auth_session(uid, st.session_state.get("user_name", "Student"), True, picked_tid)
            st.rerun()
    with c_new_snap:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("📸 Capture Snapshot", use_container_width=True, key="cr_capture_now_btn"):
            fresh_snap = _build_instant_snapshot(task, task.get("notes", ""))
            fresh_snap["force_new_entry"] = True
            save_context_restore(uid, task["id"], fresh_snap)
            st.toast("Captured fresh snapshot from your Workspace!", icon="📸")
            st.rerun()

    steps = task.get("steps", [])
    cur_idx = min(task.get("current_step_idx", 0), max(0, len(steps) - 1))
    cur_step = steps[cur_idx] if steps else {}

    cr = task.get("context_restore")
    if not cr or not cr.get("working_on"):
        cr = _build_instant_snapshot(task, task.get("notes", ""))
        save_context_restore(uid, task["id"], cr)
        task = get_task_by_id(uid, task["id"]) or task
        cr = task.get("context_restore", cr)

    working_on_text = cr.get("working_on") or f"{cur_step.get('phase', 'Step')} — {cur_step.get('title', '')}"
    done_items = cr.get("completed", [])
    done_str = ", ".join(done_items) if isinstance(done_items, list) and done_items else "Started assignment"
    tried_str = cr.get("tried") or f"Drafted notes for {cur_step.get('title', 'current step')}"
    stuck_str = cr.get("stuck_on") or "Paused mid-step"
    thought_str = cr.get("last_thought") or task.get("simplified_brief", "Connecting evidence to the main claim.")
    next_step_action = cr.get("next_step") or cur_step.get("first_action", "Continue with next action.")

    # 4-Box Cognitive Trail Bento Grid + Next Concrete Action
    html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:28px; padding:1.6rem 1.9rem; margin-bottom:1rem; box-shadow:0 12px 32px rgba(160,40,50,0.05);">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.85rem;">
    <div class="rs-serif" style="font-size:2.05rem; color:#2a1714; line-height:1.1;">{task.get('title')}</div>
    <span class="tag-status tag-active">Step {cur_idx + 1} of {len(steps)} · {cur_step.get('phase', 'Active')}</span>
  </div>

  <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:12px; margin-bottom:12px;">
    <div style="background:#eff6ff; border-radius:20px; padding:1.1rem 1.3rem;">
      <div class="rs-subhead" style="color:#1d4ed8; font-size:0.64rem;">1 · YOU WERE WORKING ON</div>
      <div class="rs-serif" style="font-size:1.38rem; color:#1e3a8a; margin-top:4px; line-height:1.18;">{working_on_text}</div>
    </div>

    <div style="background:#e8f5e9; border-radius:20px; padding:1.1rem 1.3rem;">
      <div class="rs-subhead" style="color:#15803d; font-size:0.64rem;">2 · YOU ALREADY COMPLETED</div>
      <div class="rs-serif" style="font-size:1.38rem; color:#14532d; margin-top:4px; line-height:1.18;">{done_str}</div>
    </div>

    <div style="background:#f3e8ff; border-radius:20px; padding:1.1rem 1.3rem;">
      <div class="rs-subhead" style="color:#6d28d9; font-size:0.64rem;">3 · WHAT YOU TRIED & LAST THOUGHT</div>
      <div style="font-size:0.92rem; font-weight:600; color:#4c1d95; margin-top:4px; line-height:1.4;">{tried_str}</div>
      <div style="font-size:0.83rem; color:#5b21b6; font-style:italic; margin-top:4px;">“{thought_str[:120]}”</div>
    </div>

    <div style="background:#fff8eb; border-radius:20px; padding:1.1rem 1.3rem;">
      <div class="rs-subhead" style="color:#b45309; font-size:0.64rem;">4 · WHERE YOU PAUSED / STUCK ON</div>
      <div class="rs-serif" style="font-size:1.38rem; color:#92400e; margin-top:4px; line-height:1.18;">{stuck_str}</div>
    </div>
  </div>

  <div style="background:#fff5f6; border:1.5px solid #fecdd3; border-left:5px solid #d7262b; border-radius:18px; padding:1.1rem 1.4rem;">
    <div class="rs-subhead" style="font-size:0.65rem;">5 · YOUR IMMEDIATE NEXT CONCRETE ACTION</div>
    <div class="rs-serif" style="font-size:1.65rem; color:#2a1714; margin-top:2px; line-height:1.15;">
      {next_step_action}
    </div>
  </div>
</div>
""")

    # Action Bar
    c_cont, c_edit, c_study = st.columns([1.6, 1.25, 1.25], gap="small")
    with c_cont:
        if st.button("Resume in Workspace →", type="primary", use_container_width=True):
            st.session_state["current_task_id"] = task["id"]
            st.session_state["session_mode"] = "workspace"
            st.session_state["show_context_updater"] = False
            log_task_metric(uid, "interrupted_sessions_resumed", 1)
            nav_to("active_session")
    with c_edit:
        if st.button("✎ Edit Snapshot", use_container_width=True):
            st.session_state["show_context_updater"] = not st.session_state.get("show_context_updater", False)
            st.rerun()
    with c_study:
        if st.button("📖 Learn Concepts", use_container_width=True):
            nav_to("resources")

    if st.session_state.get("show_context_updater"):
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        c_u1, c_u2 = st.columns(2, gap="medium")
        with c_u1:
            u_working = st.text_input("Working on:", value=working_on_text, key=f"cr_ed_w_{task['id']}")
            u_done = st.text_input("Completed (comma-separated):", value=done_str, key=f"cr_ed_d_{task['id']}")
            u_tried = st.text_input("What you tried:", value=tried_str, key=f"cr_ed_t_{task['id']}")
        with c_u2:
            u_stuck = st.text_input("Paused / Stuck on:", value=stuck_str, key=f"cr_ed_s_{task['id']}")
            u_thought = st.text_input("Last thought:", value=thought_str, key=f"cr_ed_th_{task['id']}")
            u_next = st.text_input("Next concrete action:", value=next_step_action, key=f"cr_ed_n_{task['id']}")

        b_sv1, b_sv2, _ = st.columns([1.4, 1.5, 1.5], gap="small")
        with b_sv1:
            if st.button("✓ Save Snapshot", type="primary", use_container_width=True):
                save_context_restore(
                    uid,
                    task["id"],
                    {
                        "working_on": u_working,
                        "completed": [x.strip() for x in u_done.split(",") if x.strip()],
                        "tried": u_tried,
                        "stuck_on": u_stuck,
                        "last_thought": u_thought,
                        "next_step": u_next,
                        "force_new_entry": True,
                    },
                )
                st.session_state["show_context_updater"] = False
                st.session_state["snapshot_saved_banner"] = True
                st.rerun()
        with b_sv2:
            if st.button("Save & Open Workspace →", use_container_width=True):
                save_context_restore(
                    uid,
                    task["id"],
                    {
                        "working_on": u_working,
                        "completed": [x.strip() for x in u_done.split(",") if x.strip()],
                        "tried": u_tried,
                        "stuck_on": u_stuck,
                        "last_thought": u_thought,
                        "next_step": u_next,
                        "force_new_entry": True,
                    },
                )
                st.session_state["show_context_updater"] = False
                st.session_state["session_mode"] = "workspace"
                nav_to("active_session")

    # Saved Context History Timeline (Expanded by default so the user always sees their saved snapshots!)
    history = task.get("context_history", [])
    if history:
        st.markdown("<div style='height:0.9rem;'></div>", unsafe_allow_html=True)
        html(f"<div class='rs-subhead' style='margin-bottom:0.45rem;'>SAVED SNAPSHOT TIMELINE ({len(history)} SAVED STATES)</div>")
        for h_idx, h in enumerate(history[:8]):
            disp_time = h.get("display_time") or h.get("saved_at", "Snapshot")[:16].replace("T", " ")
            comp = h.get("completed", [])
            comp_s = ", ".join(comp) if isinstance(comp, list) else str(comp)
            is_latest = h_idx == 0
            badge_lbl = "ACTIVE SNAPSHOT" if is_latest else f"SNAPSHOT #{len(history) - h_idx}"
            tc1, tc2 = st.columns([3.8, 1.1], gap="small")
            with tc1:
                html(f"""
<div style="background:#ffffff; border:1.5px solid {'#fecdd3' if is_latest else '#f2e2dc'}; border-left:4px solid {'#d7262b' if is_latest else '#9ca3af'}; border-radius:16px; padding:0.85rem 1.15rem; margin-bottom:0.45rem;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="font-weight:700; color:#2a1714; font-size:0.88rem;">{disp_time}</span>
    <span style="font-size:0.65rem; font-weight:700; color:{'#d7262b' if is_latest else '#6b524c'}; background:{'#fff1f2' if is_latest else '#fcf5ef'}; padding:2px 9px; border-radius:99px;">{badge_lbl}</span>
  </div>
  <div style="font-size:0.84rem; color:#5b4540; margin-top:4px; line-height:1.45;">
    <b>Working on:</b> {h.get('working_on', '')} · <b>Completed:</b> {comp_s}<br>
    <b>Paused on:</b> {h.get('stuck_on', '')} · <b>Next:</b> <span style="color:#d7262b; font-weight:700;">{h.get('next_step', '')}</span>
  </div>
</div>
""")
            with tc2:
                st.markdown("<div style='height:0.75rem;'></div>", unsafe_allow_html=True)
                if not is_latest:
                    if st.button("Restore This", key=f"rest_h_{task['id']}_{h_idx}", use_container_width=True):
                        restore_context_from_history(uid, task["id"], h_idx)
                        st.toast(f"Restored snapshot from {disp_time}", icon="🕰")
                        st.rerun()
                else:
                    html("<div style='font-size:0.76rem; font-weight:700; color:#15803d; text-align:center; padding-top:8px;'>✓ Current</div>")
