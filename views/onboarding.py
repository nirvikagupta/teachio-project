"""Visual, editorial onboarding and auth experience for Restart.

Typography: Instrument Serif (headlines) + Albert Sans (subheadlines & body copy).
Persists authenticated user to active_session.json so refreshing or visiting ?p=context_restore never loses session state.
"""

import time
import streamlit as st

from utils.graphics import get_graphic_data_uri
from utils.icons import get_logo_svg
from utils.storage import create_user, list_users, save_profile, save_active_auth_session
from utils.styles import html, inject_styles, nav_to

RED = "#d7262b"
PINK = "#f9d5da"
CREAM = "#fcf5ef"
INK = "#2a1714"


def _onboarding_css() -> None:
    st.markdown(
        f"""
<style>
[data-testid="stSidebar"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}

.badge-pill {{
    display: inline-block;
    background: #fff0f1;
    color: {RED};
    border: 1px solid #fed7da;
    border-radius: 999px;
    padding: 4px 12px;
    font-family: 'Albert Sans', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}}
</style>
""",
        unsafe_allow_html=True,
    )


def _sparkle(color: str = RED, size: int = 20) -> str:
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="{color}" '
        f'style="display:inline-block;vertical-align:middle;margin-left:4px;">'
        f'<path d="M12 0c.6 6.6 5.4 11.4 12 12-6.6.6-11.4 5.4-12 12-.6-6.6-5.4-11.4-12-12C6.6 11.4 11.4 6.6 12 0z"/></svg>'
    )


def render():
    inject_styles()
    _onboarding_css()

    start_img = get_graphic_data_uri("task_start_mode")
    companion_img = get_graphic_data_uri("hero_task_companion")

    auth_mode = st.session_state.get("auth_mode", "signup")

    html(f"""
<div style="display:flex;align-items:center;justify-content:space-between;padding-bottom:1.2rem;border-bottom:1.5px solid #f2dfd8;margin-bottom:1.5rem;">
  <div style="display:flex;align-items:center;gap:11px;">
    <div style="filter:drop-shadow(0 4px 12px rgba(215,38,43,0.26));">
      {get_logo_svg(42)}
    </div>
    <div>
      <div class="rs-serif" style="font-size:1.85rem;color:{INK};line-height:0.95;">Restart</div>
      <div class="rs-subhead" style="font-size:0.58rem;color:#8a6f68;margin-top:2px;">ACADEMIC STUDY COMPANION</div>
    </div>
  </div>
</div>
""")

    c_status, col_back = st.columns([4.8, 1.4])
    with c_status:
        if st.session_state.get("user_id") and st.session_state.get("profile_complete"):
            name = st.session_state.get("user_name", "Student")
            st.info(f"Currently logged in as **{name}**.")
    with col_back:
        if st.session_state.get("user_id") and st.session_state.get("profile_complete"):
            if st.button("To Workspace →", type="primary", use_container_width=True, key="onboard_to_home"):
                nav_to("home")
        else:
            if st.button("← Back", use_container_width=True, key="onboard_back_btn"):
                nav_to("dashboard")

    if auth_mode == "signup":
        step = st.session_state.get("onboarding_step", 1)

        if step == 1:
            col_visual, col_form = st.columns([1, 1.15], gap="large")

            with col_visual:
                html(f"""
<div style="border-radius:24px;overflow:hidden;box-shadow:0 16px 40px rgba(160,40,50,0.1);border:2px solid #fed7aa;background:#ffffff;position:relative;">
  <img src="{start_img}" alt="Start Mode 3D" style="width:100%;height:380px;object-fit:cover;display:block;">
  <div style="position:absolute;bottom:16px;left:16px;right:16px;background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);border-radius:16px;padding:12px 16px;border:1px solid #fecaca;">
    <div class="rs-subhead">01 → 07 STUDY & CONTINUITY FLOW</div>
    <div style="font-size:0.92rem;font-weight:600;color:{INK};margin-top:2px;">Zero pressure. Start without the freeze.</div>
  </div>
</div>
""")

            with col_form:
                html(f"""
<div style="padding:0.4rem 0 1.2rem 0;">
  <div class="badge-pill" style="margin-bottom:0.8rem;">Step 1 of 3 · Fast Onboarding</div>
  <div class="rs-serif" style="font-size:3.1rem;line-height:1.02;color:{RED};">
    Welcome to <i>Restart</i> { _sparkle(RED, 22) }
  </div>
  <div style="font-size:1.02rem;color:#6b524c;margin:0.8rem 0 1.4rem 0;line-height:1.55;">
    Learn concepts your way, decompose assignments into concrete steps, and restore your exact thinking state anytime.
  </div>
</div>
""")
                name = st.text_input(
                    "What should we call you?",
                    placeholder="e.g. Priya, Nirvika, Alex...",
                    key="onboard_name_input",
                )
                st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

                if st.button("Get Started →", type="primary", use_container_width=True):
                    name_clean = name.strip()
                    if not name_clean:
                        st.error("Please enter your name to continue.")
                        return
                    uid = create_user(name_clean)
                    st.session_state.user_id = uid
                    st.session_state.user_name = name_clean
                    st.session_state.profile_complete = False
                    st.session_state.onboarding_step = 2
                    save_active_auth_session(uid, name_clean, profile_complete=False)
                    st.rerun()

                st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
                if st.button("I already have an account (Log In)", use_container_width=True):
                    st.session_state.auth_mode = "login"
                    st.rerun()

        elif step == 2:
            html(f"""
<div style="text-align:center;max-width:640px;margin:0 auto 1.6rem auto;">
  <div class="badge-pill" style="margin-bottom:0.6rem;">Step 2 of 3 · Personal Challenges</div>
  <div class="rs-serif" style="font-size:2.8rem;color:{RED};line-height:1.08;">
    What gets in the way when you <i>study?</i> { _sparkle(RED, 20) }
  </div>
  <div style="font-size:0.96rem;color:#6b524c;margin-top:0.4rem;">
    Select any that apply. Restart tunes your workspace around these exact friction points.
  </div>
</div>
""")
            challenges = [
                ("⚡ Task Paralysis", "Don't know where to start or freeze on page 1"),
                ("📚 Dense Briefs", "Overwhelming assignment instructions feel impossible to process"),
                ("🌀 Distraction", "Attention drifts midway through a study session"),
                ("📉 Memory Reset", "Lose my train of thought and waste time re-reading"),
                ("⏳ Time Blindness", "Underestimate how long milestones will take"),
                ("⏸️ Break Friction", "Struggle to resume after stepping away"),
            ]

            selected_challenges = []
            c1, c2 = st.columns(2, gap="medium")
            for idx, (label, desc) in enumerate(challenges):
                col = c1 if idx % 2 == 0 else c2
                with col:
                    checked = st.checkbox(
                        f"**{label}** — {desc}",
                        value=True if idx in (0, 1, 3) else False,
                        key=f"ch_{idx}",
                    )
                    if checked:
                        selected_challenges.append(label)

            st.markdown("<div style='height:1.5rem;'></div>", unsafe_allow_html=True)
            _, c_next, _ = st.columns([1, 1.4, 1])
            with c_next:
                if st.button("Next: Support Preferences →", type="primary", use_container_width=True):
                    st.session_state["onboard_challenges"] = selected_challenges
                    st.session_state.onboarding_step = 3
                    st.rerun()

        elif step == 3:
            html(f"""
<div style="text-align:center;max-width:640px;margin:0 auto 1.6rem auto;">
  <div class="badge-pill" style="margin-bottom:0.6rem;">Step 3 of 3 · Support Preferences</div>
  <div class="rs-serif" style="font-size:2.8rem;color:{RED};line-height:1.08;">
    How should Restart <i>support</i> you? { _sparkle(RED, 20) }
  </div>
  <div style="font-size:0.96rem;color:#6b524c;margin-top:0.4rem;">
    You stay in control — no rigid timers or forced linear study paths.
  </div>
</div>
""")

            col_a, col_b = st.columns(2, gap="medium")
            with col_a:
                html(f"""
<div class="warm-card" style="padding:16px;margin-bottom:10px;">
  <b style="color:{INK};font-size:1.02rem;">🌱 Gentle Agency Prompts</b>
  <div style="font-size:0.86rem;color:#6b524c;margin-top:4px;">Ask before switching tasks without punitive timers.</div>
</div>
""")
                gentle_prompts = st.toggle("Enable Gentle Prompts", value=True)

                html(f"""
<div class="warm-card" style="padding:16px;margin-bottom:10px;margin-top:14px;">
  <b style="color:{INK};font-size:1.02rem;">🧠 Automatic Context Restore</b>
  <div style="font-size:0.86rem;color:#6b524c;margin-top:4px;">Save thinking state (completed, tried, stuck on, next action).</div>
</div>
""")
                context_recovery = st.toggle("Enable Context Restore", value=True)

            with col_b:
                html(f"""
<div class="warm-card" style="padding:16px;margin-bottom:10px;">
  <b style="color:{INK};font-size:1.02rem;">👣 One Concrete Next Action</b>
  <div style="font-size:0.86rem;color:#6b524c;margin-top:4px;">Start Mode shows one 2-minute step instead of the whole list.</div>
</div>
""")
                small_steps = st.toggle("Enable One Next Action First", value=True)

                html(f"""
<div class="warm-card" style="padding:16px;margin-bottom:10px;margin-top:14px;">
  <b style="color:{INK};font-size:1.02rem;">📖 Non-Linear Study Space</b>
  <div style="font-size:0.86rem;color:#6b524c;margin-top:4px;">Jump to Simplify, Read Aloud, Flashcards, or Explain anytime.</div>
</div>
""")
                flexible_focus = st.toggle("Enable Flexible Study Space", value=True)

            st.markdown("<div style='height:1.6rem;'></div>", unsafe_allow_html=True)
            _, c_enter, _ = st.columns([1, 1.4, 1])
            with c_enter:
                if st.button("Enter Restart →", type="primary", use_container_width=True):
                    uid = st.session_state.user_id
                    profile = {
                        "challenges": st.session_state.get("onboard_challenges", []),
                        "gentle_prompts": gentle_prompts,
                        "small_steps": small_steps,
                        "context_recovery": context_recovery,
                        "flexible_focus": flexible_focus,
                        "ai_control": True,
                    }
                    save_profile(uid, profile)
                    st.session_state.profile_complete = True
                    save_active_auth_session(uid, st.session_state.get("user_name", "Student"), profile_complete=True)
                    nav_to("home")

    else:
        col_img, col_login = st.columns([1, 1.15], gap="large")

        with col_img:
            html(f"""
<div style="border-radius:24px;overflow:hidden;box-shadow:0 16px 40px rgba(160,40,50,0.1);border:2px solid #fed7aa;background:#ffffff;position:relative;">
  <img src="{companion_img}" alt="Restart Study Companion" style="width:100%;height:380px;object-fit:cover;display:block;">
  <div style="position:absolute;bottom:16px;left:16px;right:16px;background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);border-radius:16px;padding:12px 16px;border:1px solid #fed7aa;">
    <div class="rs-subhead">06 · CONTEXT RESTORE READY</div>
    <div style="font-size:0.92rem;font-weight:600;color:{INK};margin-top:2px;">Your saved assignments and thinking states await.</div>
  </div>
</div>
""")

        with col_login:
            html(f"""
<div style="padding:0.4rem 0 1.2rem 0;">
  <div class="badge-pill" style="margin-bottom:0.8rem;">Welcome Back</div>
  <div class="rs-serif" style="font-size:3.1rem;line-height:1.02;color:{RED};">
    Resume <i>Learning</i> { _sparkle(RED, 22) }
  </div>
  <div style="font-size:1.02rem;color:#6b524c;margin:0.8rem 0 1.4rem 0;line-height:1.55;">
    Log in to access your assignments, study space, and 1-click context restores.
  </div>
</div>
""")
            all_users = list_users()

            if all_users:
                html(f"""
<div style="margin-bottom:0.9rem;">
  <div class="rs-subhead" style="font-size:0.65rem; margin-bottom:0.45rem;">SAVED ACCOUNTS IN YOUR BROWSER (1-CLICK LOGIN)</div>
</div>
""")
                u_cols = st.columns(2, gap="small")
                for idx, (uid, u) in enumerate(all_users.items()):
                    name_display = u.get("name", "Student")
                    with u_cols[idx % 2]:
                        if st.button(f"👤 {name_display}", key=f"quick_{uid}", use_container_width=True):
                            st.session_state.user_id = uid
                            st.session_state.user_name = name_display
                            st.session_state.profile_complete = True
                            save_active_auth_session(uid, name_display, profile_complete=True)
                            nav_to("home")
                st.markdown("<div style='height:0.6rem;'></div>", unsafe_allow_html=True)

            login_query = st.text_input(
                "Or enter your Name / Student ID:",
                placeholder="e.g. Priya, Nirvika, or u_68A44696",
                key="login_name_or_id",
            )
            st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

            if st.button("Log In →", type="primary", use_container_width=True):
                query_clean = login_query.strip().lower()
                if not query_clean:
                    st.error("Please enter your name or click a Saved Account above.")
                    return

                matched_uid = None
                matched_user = None
                for uid, u in all_users.items():
                    if uid.lower() == query_clean or u.get("name", "").strip().lower() == query_clean:
                        matched_uid = uid
                        matched_user = u
                        break

                if matched_user:
                    st.session_state.user_id = matched_uid
                    st.session_state.user_name = matched_user.get("name", "Student")
                    st.session_state.profile_complete = True
                    save_active_auth_session(matched_uid, matched_user.get("name", "Student"), profile_complete=True)
                    st.success(f"Welcome back, {matched_user.get('name')}!")
                    time.sleep(0.2)
                    nav_to("home")
                else:
                    # Automatically create and save the account so the user is never blocked!
                    new_uid = create_user(login_query.strip())
                    st.session_state.user_id = new_uid
                    st.session_state.user_name = login_query.strip()
                    st.session_state.profile_complete = True
                    save_active_auth_session(new_uid, login_query.strip(), profile_complete=True)
                    nav_to("home")

            st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
            if st.button("Create a New Account →", use_container_width=True):
                st.session_state.auth_mode = "signup"
                st.session_state.onboarding_step = 1
                st.rerun()
