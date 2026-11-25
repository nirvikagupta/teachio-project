import json
import streamlit as st
import streamlit.components.v1 as components
from utils.icons import get_logo_svg
from utils.storage import (
    clear_active_auth_session,
    get_user_tasks,
    get_latest_resumable_task,
    save_active_auth_session,
    export_frontend_state,
)


def _logout():
    clear_active_auth_session()
    st.session_state.user_id = None
    st.session_state.user_name = None
    st.session_state.profile_complete = False
    st.session_state.onboarding_step = 1
    st.session_state.auth_mode = "login"
    st.session_state.page = "dashboard"
    if hasattr(st, "query_params"):
        st.query_params.clear()
    st.rerun()


def sync_to_browser_storage(uid: str):
    """Automatically mirrors all created accounts, active user session, and assignments into the browser's frontend localStorage."""
    try:
        payload = export_frontend_state(uid)
        json_str = json.dumps(payload, ensure_ascii=False)
        components.html(
            f"""
            <script>
            try {{
                const state = {json_str};
                window.localStorage.setItem('restart_frontend_vault_v1', JSON.stringify(state));
                if (state.users) {{
                    window.localStorage.setItem('restart_accounts_v1', JSON.stringify(state.users));
                }}
                if (state.active_session && state.active_session.user_id) {{
                    window.localStorage.setItem('restart_active_user_v1', JSON.stringify(state.active_session));
                }}
            }} catch (e) {{}}
            </script>
            """,
            height=0,
        )
    except Exception:
        pass


def render_assignment_journey_bar(active_stage: str):
    """Renders a clean, interactive 4-step journey bar across the top of assignment pages so the flow is 100% intuitive."""
    uid = st.session_state.get("user_id")
    all_tasks = get_user_tasks(uid) if uid else []
    cur_tid = st.session_state.get("current_task_id")
    task_map = {t["id"]: t for t in all_tasks if t.get("id")}
    active_task = task_map.get(cur_tid) or (all_tasks[0] if all_tasks else None)

    stages = [
        ("plan", "1 · Study Plan", "study_plan"),
        ("concepts", "2 · Learn Concepts", "resources"),
        ("workspace", "3 · Workspace", "active_session"),
        ("restore", "4 · Context Snapshot", "context_restore"),
    ]

    cols = st.columns(4, gap="small")
    for idx, (stage_key, label, target_page) in enumerate(stages):
        is_current = active_stage == stage_key
        with cols[idx]:
            if st.button(
                label,
                key=f"journey_bar_{active_stage}_{stage_key}",
                type="primary" if is_current else "secondary",
                use_container_width=True,
            ):
                if active_task and active_task.get("id"):
                    st.session_state["current_task_id"] = active_task["id"]
                    st.session_state["interrupted_task_id"] = active_task["id"]
                    st.session_state["decomposed_task"] = active_task
                if stage_key == "workspace":
                    st.session_state["session_mode"] = "workspace"
                st.session_state.page = target_page
                if hasattr(st, "query_params"):
                    st.query_params["p"] = target_page
                st.rerun()
    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)


def render_app_sidebar():
    """Renders the sidebar with a global Active Assignment switcher, clear 4-step journey navigation, and frontend browser sync."""
    current = st.session_state.get("page", "home")
    if current in ("my_work", "progress"):
        current = "home"
    uid = st.session_state.get("user_id")
    user_name = st.session_state.get("user_name", "Student")

    all_tasks = get_user_tasks(uid) if uid else []
    task_map = {t["id"]: t for t in all_tasks if t.get("id")}
    cur_tid = st.session_state.get("current_task_id")
    if not cur_tid or cur_tid not in task_map:
        latest = get_latest_resumable_task(uid) if uid else None
        if latest and latest.get("id"):
            cur_tid = latest["id"]
            st.session_state["current_task_id"] = cur_tid
        elif all_tasks and all_tasks[0].get("id"):
            cur_tid = all_tasks[0]["id"]
            st.session_state["current_task_id"] = cur_tid

    with st.sidebar:
        st.markdown(
            f"""
            <div class="restart-brand">
                <div style="filter: drop-shadow(0 5px 12px rgba(215, 38, 43, 0.25));">
                    {get_logo_svg(44)}
                </div>
                <div>
                    <div class="brand-text">Restart</div>
                    <div class="brand-badge">✓ {user_name} · Saved</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # GLOBAL ACTIVE ASSIGNMENT SWITCHER (Always available in sidebar!)
        if all_tasks:
            st.markdown(
                "<div style='font-size:0.66rem; font-weight:700; color:#d7262b; text-transform:uppercase; letter-spacing:0.12em; margin:0.1rem 0 0.25rem 0;'>Active Assignment</div>",
                unsafe_allow_html=True,
            )
            tid_list = list(task_map.keys())
            sel_idx = tid_list.index(cur_tid) if cur_tid in tid_list else 0
            picked_tid = st.selectbox(
                "Active Assignment",
                options=tid_list,
                format_func=lambda tid: task_map[tid].get("title", "Assignment"),
                index=sel_idx,
                key="global_sidebar_task_picker",
                label_visibility="collapsed",
            )
            if picked_tid != cur_tid:
                st.session_state["current_task_id"] = picked_tid
                st.session_state["interrupted_task_id"] = picked_tid
                st.session_state["decomposed_task"] = task_map[picked_tid]
                save_active_auth_session(uid, user_name, True, picked_tid)
                st.rerun()

            st.markdown("<div style='height:0.35rem;'></div>", unsafe_allow_html=True)

        nav_items = [
            ("home", "🏠 All Assignments"),
            ("add_task", "➕ New Assignment"),
            ("study_plan", "🗓️ Study Plan"),
            ("resources", "📖 Learn Concepts"),
            ("active_session", "✍️ Workspace"),
            ("context_restore", "🧠 Context Snapshot"),
            ("profile", "⚙️ Settings"),
        ]

        for page_key, label in nav_items:
            is_active = current == page_key
            if st.button(
                label,
                key=f"nav_btn_{page_key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                if page_key == "active_session":
                    st.session_state["session_mode"] = "workspace"
                    st.session_state.pop("prepared_pause_context", None)
                st.session_state.page = page_key
                if hasattr(st, "query_params"):
                    st.query_params["p"] = page_key
                st.rerun()

        st.markdown("<hr style='border:none; border-top:1.5px solid #f2dfd8; margin:0.9rem 0 0.7rem 0;'>", unsafe_allow_html=True)

        if st.button("Switch Account / Log Out", key="nav_btn_switch", use_container_width=True):
            _logout()

    if uid:
        sync_to_browser_storage(uid)
