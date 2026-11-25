import asyncio

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import streamlit as st
from utils.session import init_session

init_session()

query_params = st.query_params if hasattr(st, "query_params") else st.experimental_get_query_params()
if "p" in query_params:
    st.session_state.page = query_params["p"]

page = st.session_state.get("page", "dashboard")
is_logged_in = bool(st.session_state.get("user_id"))
is_profile_complete = bool(st.session_state.get("profile_complete", False))

# Strict routing guards:
if not is_logged_in:
    if page not in ("dashboard", "onboarding"):
        page = "dashboard"
        st.session_state.page = "dashboard"
elif not is_profile_complete:
    page = "onboarding"
    st.session_state.page = "onboarding"
elif is_profile_complete and page in ("dashboard",):
    page = "home"
    st.session_state.page = "home"

st.set_page_config(
    page_title="Restart — Academic Study Companion",
    page_icon="assets/logo.svg",
    layout="wide",
    initial_sidebar_state="collapsed" if page in ("dashboard", "onboarding") else "expanded",
)

if page == "dashboard":
    from views.dashboard import render
    render()
elif page == "onboarding":
    from views.onboarding import render
    render()
elif page in ("home", "my_work", "progress"):
    from views.home import render
    render()
elif page == "add_task":
    from views.add_task import render
    render()
elif page == "study_plan":
    from views.study_plan import render
    render()
elif page == "active_session":
    from views.active_session import render
    render()
elif page == "resources":
    from views.resources import render
    render()
elif page == "context_restore":
    from views.context_restore import render
    render()
elif page == "profile":
    from views.profile import render
    render()
else:
    from views.home import render
    render()
