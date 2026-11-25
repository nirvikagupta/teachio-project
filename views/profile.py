"""Settings — Clean Pastel Bento Preferences."""

import json
import streamlit as st
from utils.styles import html, inject_styles, nav_to
from utils.storage import save_profile, get_profile, list_users, save_active_auth_session, export_frontend_state, import_frontend_account_bundle
from utils.navigation import render_app_sidebar


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("dashboard")
        return

    uid = st.session_state.user_id
    render_app_sidebar()
    existing = get_profile(uid)

    html("""
<div style="margin-bottom: 1.1rem;">
  <span class="rs-subhead">PERSONALIZATION</span>
  <div class="page-title" style="margin:0;">Workspace <i>Settings</i></div>
</div>
""")

    col1, col2 = st.columns(2, gap="large")

    with col1:
        html("""
<div style="background:#fff5f6; border-radius:22px; padding:1.1rem 1.35rem; margin-bottom:0.8rem;">
  <div class="rs-subhead" style="font-size:0.65rem;">PROFILE & GUIDANCE</div>
  <div class="rs-serif" style="font-size:1.5rem;">Your Study Style</div>
</div>
""")
        user_name = st.text_input("Display Name", value=st.session_state.get("user_name", "Priya"))
        guidance_level = st.radio(
            "Step Granularity",
            ["Minimal", "Moderate", "Step-by-step (2-min micro-actions)"],
            index=2,
        )
        auto_context_save = st.toggle("Auto-save thinking state when pausing", value=existing.get("auto_context_save", True))

    with col2:
        html("""
<div style="background:#eff6ff; border-radius:22px; padding:1.1rem 1.35rem; margin-bottom:0.8rem;">
  <div class="rs-subhead" style="color:#1d4ed8; font-size:0.65rem;">READING & ACCESSIBILITY</div>
  <div class="rs-serif" style="font-size:1.5rem;">Visual Comfort</div>
</div>
""")
        pref_font_size = st.select_slider("Reading Font Size", options=["16px", "18px", "20px", "22px"], value=existing.get("pref_font_size", "18px"))
        pref_read_aloud = st.toggle("Enable Read-Aloud (Text-to-Speech)", value=existing.get("pref_read_aloud", True))
        acc_density = st.toggle("Reduced Visual Density (Calm Bento Layout)", value=existing.get("acc_density", True))

    st.markdown("<div style='height:0.8rem;'></div>", unsafe_allow_html=True)
    if st.button("Save Settings →", type="primary"):
        st.session_state.user_name = user_name.strip() or st.session_state.get("user_name", "Student")
        save_profile(
            uid,
            {
                **existing,
                "guidance_level": guidance_level,
                "auto_context_save": auto_context_save,
                "pref_font_size": pref_font_size,
                "pref_read_aloud": pref_read_aloud,
                "acc_density": acc_density,
            },
        )
        st.success("Settings saved!")

    st.markdown("<hr style='border:none; border-top:1.5px solid #f2dfd8; margin:1.4rem 0 1rem 0;'>", unsafe_allow_html=True)
    c_acc1, c_acc2 = st.columns(2, gap="large")
    with c_acc1:
        html("""
<div style="background:#e8f5e9; border-radius:22px; padding:1rem 1.35rem; margin-bottom:0.7rem;">
  <div class="rs-subhead" style="color:#15803d; font-size:0.64rem;">SAVED BROWSER ACCOUNTS</div>
  <div class="rs-serif" style="font-size:1.45rem;">1-Click Account Switcher</div>
</div>
""")
        all_users = list_users()
        u_cols = st.columns(2, gap="small")
        for idx, (u_id, u_info) in enumerate(all_users.items()):
            u_name = u_info.get("name", "Student")
            is_cur_user = u_id == uid
            with u_cols[idx % 2]:
                if st.button(
                    f"{'✓ ' if is_cur_user else '👤 '}{u_name}",
                    key=f"prof_sw_{u_id}",
                    type="primary" if is_cur_user else "secondary",
                    use_container_width=True,
                ):
                    st.session_state.user_id = u_id
                    st.session_state.user_name = u_name
                    st.session_state.profile_complete = True
                    save_active_auth_session(u_id, u_name, True)
                    st.rerun()

    with c_acc2:
        html("""
<div style="background:#f3e8ff; border-radius:22px; padding:1rem 1.35rem; margin-bottom:0.7rem;">
  <div class="rs-subhead" style="color:#6d28d9; font-size:0.64rem;">FRONTEND BROWSER STORAGE & BACKUP</div>
  <div class="rs-serif" style="font-size:1.45rem;">Account & Snapshot Vault</div>
</div>
""")
        html("<div style='font-size:0.86rem; color:#5b4540; margin-bottom:0.6rem;'>✓ All created accounts, assignments, and snapshots are automatically saved in your browser's <code>localStorage</code> and local vault.</div>")
        vault_json = json.dumps(export_frontend_state(uid), indent=2, ensure_ascii=False)
        st.download_button(
            "⬇ Export Account & Assignments JSON",
            data=vault_json,
            file_name=f"restart_account_{st.session_state.get('user_name', 'student').lower()}.json",
            mime="application/json",
            use_container_width=True,
        )
