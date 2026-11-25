import streamlit as st
from utils.storage import load_active_auth_session, load_user


def init_session():
    if "user_id" not in st.session_state or not st.session_state.get("user_id"):
        saved = load_active_auth_session()
        saved_uid = saved.get("user_id")
        if saved_uid and load_user(saved_uid):
            st.session_state["user_id"] = saved_uid
            st.session_state["user_name"] = saved.get("user_name") or load_user(saved_uid).get("name", "Student")
            st.session_state["profile_complete"] = bool(saved.get("profile_complete", True))
            if saved.get("current_task_id") and not st.session_state.get("current_task_id"):
                st.session_state["current_task_id"] = saved.get("current_task_id")
        else:
            st.session_state["user_id"] = None

    if "page" not in st.session_state:
        st.session_state["page"] = "dashboard"
