"""Landing / Welcome Page — Restart Academic Study Companion.

- Typography: Instrument Serif (headlines) + Albert Sans (subheadlines & body copy)
- Strictly unauthenticated welcome page: NO 'Continue where you left off' card shown before logging in.
- Shows the non-linear workflow: 01 Assignment -> 02 Study (Anytime) -> 03 Decompose -> 04 Start/Work -> 05 Pause -> 06 Context Restore -> 07 Continue.
"""

import streamlit as st

from utils.graphics import get_graphic_data_uri
from utils.icons import get_logo_svg
from utils.styles import html, inject_styles, nav_to

RED = "#d7262b"
PINK = "#f9d5da"
CREAM = "#fcf5ef"
INK = "#2a1714"
BLUE = "#c8daf4"


def _landing_css() -> None:
    st.markdown(
        f"""
<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}

.rs-serif {{
    font-family: 'Instrument Serif', Georgia, serif !important;
}}

.rs-sub {{
    font-family: 'Albert Sans', sans-serif !important;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    font-weight: 700;
}}

.st-key-hero_card {{
    background: {PINK};
    border-radius: 26px;
    padding: 2.6rem 2.4rem 2.3rem 2.4rem;
    min-height: 470px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}

.task-card {{
    background: #ffffff;
    border-radius: 22px;
    overflow: hidden;
    border: 1.5px solid #f2e2dc;
    transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 6px 18px rgba(160, 40, 50, 0.04);
}}

.task-card:hover {{
    transform: translateY(-6px);
    box-shadow: 0 20px 42px rgba(160, 40, 50, 0.12);
    border-color: #fca5a5;
}}

.task-card-img {{
    width: 100%;
    height: 175px;
    object-fit: cover;
    display: block;
    transition: transform 0.4s ease;
}}

.task-card:hover .task-card-img {{
    transform: scale(1.04);
}}

.badge-pill {{
    display: inline-block;
    background: #fff0f1;
    color: {RED};
    border: 1px solid #fed7da;
    border-radius: 999px;
    padding: 4px 12px;
    font-family: 'Albert Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}

.circle-btn {{
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: {RED};
    color: #ffffff;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 1rem;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _sparkle(color: str = RED, size: int = 22) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" '
        f'style="display:inline-block;vertical-align:middle;margin-left:4px;">'
        f'<path d="M12 0c.6 6.6 5.4 11.4 12 12-6.6.6-11.4 5.4-12 12-.6-6.6-5.4-11.4-12-12C6.6 11.4 11.4 6.6 12 0z"/></svg>'
    )


def render() -> None:
    inject_styles()
    _landing_css()

    hero_img = get_graphic_data_uri("hero_task_companion")
    decompose_img = get_graphic_data_uri("task_decomposer")
    start_img = get_graphic_data_uri("task_start_mode")
    shield_img = get_graphic_data_uri("task_interruption_shield")
    restore_img = get_graphic_data_uri("task_context_restore")

    # ------------------------------------------------------------------ TOP BAR
    html(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding:0.2rem 0 1.4rem 0;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="filter:drop-shadow(0 5px 14px rgba(215,38,43,0.28));">
      {get_logo_svg(46)}
    </div>
    <div>
      <div class="rs-serif" style="font-size:1.95rem;color:{INK};line-height:0.95;">Restart</div>
      <div class="rs-sub" style="font-size:0.62rem;color:#8a6f68;margin-top:3px;">ACADEMIC STUDY COMPANION</div>
    </div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;font-size:0.74rem;font-weight:700;color:{RED};background:#fff1f2;padding:6px 14px;border-radius:999px;border:1px solid #ffd5d8;letter-spacing:0.06em;text-transform:uppercase;">
    <span>Assignment → Study → Decompose → Work → Context Restore</span> { _sparkle(RED, 13) }
  </div>
</div>
""")

    # ------------------------------------------------------------------ HERO SECTION
    col_hero_left, col_hero_right = st.columns([1, 1.05], gap="large")

    with col_hero_left:
        with st.container(key="hero_card"):
            html(f"""
<div>
  <div class="badge-pill" style="margin-bottom:1rem;">Study Workspace & Continuity</div>
  <div class="rs-serif" style="font-size:4.2rem;line-height:0.96;color:{RED};">
    Start the <i>Work.</i> { _sparkle(RED, 28) }
  </div>
  <div class="rs-serif" style="font-size:2.35rem;line-height:1.1;color:{INK};margin-top:0.55rem;">
    Pick up <i>exactly</i> where you left off.
  </div>
  <div style="font-size:1.02rem;color:#5b4540;margin:1.1rem 0 1.6rem 0;line-height:1.6;">
    Your study companion for learning concepts, breaking overwhelming briefs into concrete actions, and restoring your exact thinking state when interrupted.
  </div>
</div>
""")
            c_btn1, c_btn2 = st.columns([1.25, 1])
            with c_btn1:
                if st.button("Get Started →", type="primary", use_container_width=True, key="hero_start_btn"):
                    st.session_state.auth_mode = "signup"
                    st.session_state.onboarding_step = 1
                    nav_to("onboarding")
            with c_btn2:
                if st.button("Log In", use_container_width=True, key="hero_login_btn"):
                    st.session_state.auth_mode = "login"
                    nav_to("onboarding")

            html("""
<div style="margin-top:1.2rem;padding-top:1rem;border-top:1px solid rgba(215,38,43,0.15);font-size:0.78rem;color:#785a54;letter-spacing:0.08em;text-transform:uppercase;font-weight:700;">
  01 Assignment · 02 Study Anytime · 03 Decompose · 04 Start · 05 Pause · 06 Restore · 07 Continue
</div>
""")

    with col_hero_right:
        html(f"""
<div style="position:relative;border-radius:26px;overflow:hidden;box-shadow:0 20px 50px rgba(160,40,50,0.12);border:2px solid #fed7aa;min-height:470px;background:#ffffff;">
  <img src="{hero_img}" alt="Restart Study Companion" style="width:100%;height:100%;min-height:470px;object-fit:cover;display:block;">
  <div style="position:absolute;top:16px;left:16px;background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);border:1.5px solid #fed7aa;border-radius:999px;padding:6px 14px;display:flex;align-items:center;gap:8px;">
    <span style="width:9px;height:9px;border-radius:50%;background:#22c55e;display:inline-block;"></span>
    <span class="rs-sub" style="font-size:0.68rem;color:{INK};">NON-LINEAR STUDY & TASK FLOW</span>
  </div>
  <div style="position:absolute;bottom:16px;right:16px;left:16px;background:rgba(255,255,255,0.94);backdrop-filter:blur(10px);border:1.5px solid #fecaca;border-radius:18px;padding:13px 16px;">
    <div class="rs-sub" style="font-size:0.66rem;color:{RED};">04 · ONE CONCRETE NEXT ACTION</div>
    <div class="rs-serif" style="font-size:1.25rem;color:{INK};margin-top:2px;">
      “Find one paper comparing Approach A and Approach B.”
    </div>
  </div>
</div>
""")

    # ------------------------------------------------------------------ 4 VISUAL PILLARS
    html(f"""
<div style="display:flex;align-items:flex-end;justify-content:space-between;margin:2.8rem 0 1.2rem 0;">
  <div>
    <div class="badge-pill" style="margin-bottom:0.35rem;">How Restart Works</div>
    <div class="rs-serif" style="font-size:2.6rem;color:{RED};line-height:1.05;">Starting, Sustaining & <i>Resuming</i> { _sparkle(RED, 20) }</div>
  </div>
</div>
""")

    c1, c2, c3, c4 = st.columns(4, gap="medium")

    with c1:
        html(f"""
<div class="task-card">
  <div style="position:relative;background:#fdf2f3;overflow:hidden;">
    <img src="{decompose_img}" class="task-card-img" alt="Assignment & Decompose">
  </div>
  <div style="padding:15px 16px 17px 16px;">
    <div class="rs-sub" style="font-size:0.66rem;color:{RED};">01 & 03 · DECOMPOSE</div>
    <div class="rs-serif" style="font-size:1.45rem;color:{INK};margin:3px 0 6px 0;">Understand → Submit</div>
    <div style="font-size:0.84rem;color:#6d5550;line-height:1.48;min-height:54px;">
      Break overwhelming briefs into Understand → Research → Compare → Draft → Review → Submit.
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid #f7e6e2;">
      <span class="rs-sub" style="font-size:0.66rem;color:#a84448;">Actionable plan</span>
      <span class="circle-btn">+</span>
    </div>
  </div>
</div>
""")

    with c2:
        html(f"""
<div class="task-card">
  <div style="position:relative;background:#f0fdf4;overflow:hidden;">
    <img src="{restore_img}" class="task-card-img" alt="Study Anytime">
  </div>
  <div style="padding:15px 16px 17px 16px;">
    <div class="rs-sub" style="font-size:0.66rem;color:#16a34a;">02 · STUDY ANYTIME</div>
    <div class="rs-serif" style="font-size:1.45rem;color:{INK};margin:3px 0 6px 0;">Read, Simplify & Quiz</div>
    <div style="font-size:0.84rem;color:#6d5550;line-height:1.48;min-height:54px;">
      Jump to Study before or during work: Simplify text, Read aloud, Flashcards, Quiz, Mind map, Explain.
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid #ddfae4;">
      <span class="rs-sub" style="font-size:0.66rem;color:#16a34a;">Non-linear space</span>
      <span class="circle-btn" style="background:#16a34a;">+</span>
    </div>
  </div>
</div>
""")

    with c3:
        html(f"""
<div class="task-card">
  <div style="position:relative;background:#edf4fe;overflow:hidden;">
    <img src="{start_img}" class="task-card-img" alt="Start & Work">
  </div>
  <div style="padding:15px 16px 17px 16px;">
    <div class="rs-sub" style="font-size:0.66rem;color:#2563eb;">04 · START / WORK</div>
    <div class="rs-serif" style="font-size:1.45rem;color:{INK};margin:3px 0 6px 0;">One Concrete Action</div>
    <div style="font-size:0.84rem;color:#6d5550;line-height:1.48;min-height:54px;">
      Start with one concrete next action rather than facing the entire assignment at once.
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid #e2ecfb;">
      <span class="rs-sub" style="font-size:0.66rem;color:#2563eb;">Zero freeze</span>
      <span class="circle-btn" style="background:#2563eb;">+</span>
    </div>
  </div>
</div>
""")

    with c4:
        html(f"""
<div class="task-card">
  <div style="position:relative;background:#fef2f2;overflow:hidden;">
    <img src="{shield_img}" class="task-card-img" alt="Pause & Context Restore">
  </div>
  <div style="padding:15px 16px 17px 16px;">
    <div class="rs-sub" style="font-size:0.66rem;color:#dc2626;">05–07 · CONTEXT RESTORE</div>
    <div class="rs-serif" style="font-size:1.45rem;color:{INK};margin:3px 0 6px 0;">Restore & Continue</div>
    <div style="font-size:0.84rem;color:#6d5550;line-height:1.48;min-height:54px;">
      Pause or switch tasks anytime. Return to what you completed, where you got stuck, and what's next.
    </div>
    <div style="display:flex;align-items:center;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid #fae2e0;">
      <span class="rs-sub" style="font-size:0.66rem;color:#dc2626;">1-click resume</span>
      <span class="circle-btn" style="background:#dc2626;">+</span>
    </div>
  </div>
</div>
""")
