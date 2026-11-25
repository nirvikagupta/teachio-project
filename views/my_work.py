"""My Work — Clean Pastel Bento Grid of Assignments."""

import streamlit as st
from utils.navigation import render_app_sidebar
from utils.styles import html, inject_styles, nav_to
from utils.storage import (
    get_user_tasks,
    delete_user_task,
    update_task_metadata,
)


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    c_hdr, c_add = st.columns([3.8, 1.3])
    with c_hdr:
        html("""
<div style="margin-bottom: 1rem;">
  <span class="rs-subhead">ALL PROJECTS</span>
  <div class="page-title" style="margin:0;">My <i>Work</i></div>
</div>
""")
    with c_add:
        st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
        if st.button("+ New Assignment", type="primary", use_container_width=True):
            st.session_state.pop("decomposed_task", None)
            st.session_state["add_task_mode"] = "input"
            nav_to("add_task")

    tasks = get_user_tasks(uid)
    if not tasks:
        html("""
<div style="background:#ffffff; border-radius:26px; padding:2.5rem; text-align:center; border:1.5px solid #f2e2dc;">
  <div class="rs-serif" style="font-size:1.85rem;">No assignments yet</div>
  <div style="font-size:0.92rem; color:#6b524c; margin-top:4px;">Click <b>+ New Assignment</b> to add your first brief.</div>
</div>
""")
        return

    pastel_cards = [
        ("#fff5f6", "#fecdd3", "#d7262b"),
        ("#eff6ff", "#bfdbfe", "#2563eb"),
        ("#e8f5e9", "#bbf7d0", "#16a34a"),
        ("#f3e8ff", "#e9d5ff", "#7c3aed"),
    ]

    grid_cols = st.columns(2, gap="large")
    for idx, t in enumerate(tasks):
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
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:26px; padding:1.5rem 1.7rem; margin-bottom:0.65rem; box-shadow:0 10px 26px rgba(160,40,50,0.04);">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span style="background:{bg}; color:{accent_c}; border:1px solid {border_c}; font-size:0.68rem; font-weight:700; padding:3px 11px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
      Due {t.get('due_date', 'Friday')}
    </span>
    <span style="font-size:0.8rem; font-weight:700; color:#6b524c;">{done_cnt}/{total_cnt} steps ({pct}%)</span>
  </div>

  <div class="rs-serif" style="font-size:1.85rem; color:#2a1714; margin:0.4rem 0 0.6rem 0;">
    {t.get('title')}
  </div>

  <div class="adhd-progress-bg"><div class="adhd-progress-fg" style="width:{pct}%; background:{accent_c};"></div></div>

  <div style="background:{bg}; border-radius:16px; padding:0.8rem 1rem; margin-top:0.85rem; font-size:0.88rem; color:#2a1714;">
    <b style="color:{accent_c};">Next:</b> {next_act}
  </div>
</div>
""")
            b1, b2, b3 = st.columns([1.4, 1.2, 1])
            with b1:
                if st.button("Resume →", key=f"mw_res_{t['id']}", type="primary", use_container_width=True):
                    st.session_state["current_task_id"] = t["id"]
                    st.session_state["session_mode"] = "workspace"
                    nav_to("active_session")
            with b2:
                if st.button("View Steps", key=f"mw_steps_{t['id']}", use_container_width=True):
                    st.session_state["current_task_id"] = t["id"]
                    st.session_state["decomposed_task"] = t
                    st.session_state["add_task_mode"] = "breakdown"
                    nav_to("add_task")
            with b3:
                if st.button("Delete", key=f"mw_del_{t['id']}", use_container_width=True):
                    delete_user_task(uid, t["id"])
                    st.rerun()
            st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)
