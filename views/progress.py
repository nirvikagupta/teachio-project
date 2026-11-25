"""Progress Page — Guilt-Free Pastel Bento Dashboard."""

import streamlit as st
from utils.navigation import render_app_sidebar
from utils.styles import html, inject_styles, nav_to
from utils.storage import get_user_tasks, get_adhd_metrics


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    html("""
<div style="margin-bottom: 1.1rem;">
  <span class="rs-subhead">GUILT-FREE CONTINUITY</span>
  <div class="page-title" style="margin:0;">Your <i>Progress</i></div>
</div>
""")

    tasks = get_user_tasks(uid)
    metrics = get_adhd_metrics(uid)

    total_pauses = sum(len(t.get("context_history", [])) or (1 if t.get("context_restore") else 0) for t in tasks)
    total_done = sum(sum(1 for s in t.get("steps", []) if s.get("completed")) for t in tasks)
    total_restored = max(int(metrics.get("interrupted_sessions_resumed", 1)), len([t for t in tasks if t.get("context_restore")]))

    # 3 Pastel Bento Metric Cards
    html(f"""
<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:16px; margin-bottom:1.6rem;">
  <div style="background:#e8f5e9; border-radius:26px; padding:1.5rem 1.6rem;">
    <div class="rs-subhead" style="color:#15803d; font-size:0.66rem;">STEPS COMPLETED</div>
    <div class="rs-serif" style="font-size:3rem; color:#14532d; line-height:1; margin:0.4rem 0 0.2rem 0;">{total_done}</div>
    <div style="font-size:0.86rem; color:#166534;">Bite-sized milestones finished</div>
  </div>
  <div style="background:#eff6ff; border-radius:26px; padding:1.5rem 1.6rem;">
    <div class="rs-subhead" style="color:#1d4ed8; font-size:0.66rem;">CONTEXT SNAPSHOTS</div>
    <div class="rs-serif" style="font-size:3rem; color:#1e3a8a; line-height:1; margin:0.4rem 0 0.2rem 0;">{total_pauses}</div>
    <div style="font-size:0.86rem; color:#1e40af;">Thinking states preserved</div>
  </div>
  <div style="background:#f3e8ff; border-radius:26px; padding:1.5rem 1.6rem;">
    <div class="rs-subhead" style="color:#6d28d9; font-size:0.66rem;">SEAMLESS RESUMES</div>
    <div class="rs-serif" style="font-size:3rem; color:#4c1d95; line-height:1; margin:0.4rem 0 0.2rem 0;">{total_restored}</div>
    <div style="font-size:0.86rem; color:#5b21b6;">Sessions resumed in 1 click</div>
  </div>
</div>
""")

    if not tasks:
        return

    grid_cols = st.columns(2, gap="large")
    for idx, t in enumerate(tasks):
        steps = t.get("steps", [])
        done_steps = [s.get("title") for s in steps if s.get("completed")]
        done_cnt = len(done_steps)
        total_cnt = max(len(steps), 1)
        pct = int((done_cnt / total_cnt) * 100)
        cur_idx = min(t.get("current_step_idx", 0), max(0, len(steps) - 1))
        cur_step = steps[cur_idx] if steps else {}
        cr = t.get("context_restore", {})
        next_act = cr.get("next_step") or cur_step.get("first_action", "Continue next step")

        with grid_cols[idx % 2]:
            html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:26px; padding:1.5rem 1.7rem; margin-bottom:0.8rem;">
  <div style="display:flex; justify-content:space-between; align-items:center;">
    <span class="rs-subhead" style="font-size:0.66rem;">{t.get('subject', 'COURSEWORK')}</span>
    <span class="tag-status tag-active">{done_cnt}/{total_cnt} steps ({pct}%)</span>
  </div>
  <div class="rs-serif" style="font-size:1.85rem; margin:0.3rem 0 0.6rem 0;">{t.get('title')}</div>
  <div class="adhd-progress-bg"><div class="adhd-progress-fg" style="width:{pct}%;"></div></div>
  <div style="background:#fff5f6; border-radius:16px; padding:0.85rem 1rem; margin-top:0.9rem; font-size:0.88rem; color:#881337;">
    <b>Next up:</b> {next_act}
  </div>
</div>
""")
