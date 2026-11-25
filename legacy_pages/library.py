import streamlit as st
from utils.navigation import render_app_sidebar
from utils.styles import inject_styles, nav_to
from utils.storage import (
    get_user_library,
    create_subject,
    create_unit,
    save_pdf_to_unit,
    save_text_to_unit,
    delete_subject,
    delete_unit,
    delete_pdf,
    delete_text,
)

SUBJECT_ICONS = {
    "maths": "🔢", "math": "🔢", "mathematics": "🔢",
    "physics": "⚛️", "chemistry": "🧪", "biology": "🧬",
    "science": "🔬", "english": "📖", "hindi": "🪔",
    "history": "🏛️", "geography": "🌍", "economics": "📊",
    "computer": "💻", "cs": "💻", "music": "🎵",
    "art": "🎨", "default": "📁",
}

def subject_icon(name: str) -> str:
    key = name.lower().strip()
    for k, v in SUBJECT_ICONS.items():
        if k in key:
            return v
    return SUBJECT_ICONS["default"]

def render():
    inject_styles()

    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return
    render_app_sidebar()

    uid = st.session_state.user_id
    name = st.session_state.get("user_name", "Student")
    view = st.session_state.get("lib_view", "subjects")
    active_subject = st.session_state.get("lib_subject", None)
    active_unit = st.session_state.get("lib_unit", None)

    # Always-visible top bar
    t_left, t_right = st.columns([6, 1])
    with t_right:
        if st.button("Home", use_container_width=True):
            st.session_state.lib_view = "subjects"
            nav_to("home")

    # ============================================================
    #  VIEW: SUBJECTS
    # ============================================================
    if view == "subjects":
        st.markdown('<div class="page-title">Library</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="page-subtitle">Your organized roadmap of subjects and topics.</div>', unsafe_allow_html=True)

        library = get_user_library(uid)

        if library:
            st.markdown("### 📚 Your Subjects")
            cols = st.columns(3)
            for i, (subj_name, subj_data) in enumerate(library.items()):
                with cols[i % 3]:
                    icon = subject_icon(subj_name)
                    st.markdown(f"""
                        <div style="background: #ffffff; border: 2px solid #000000; border-radius: 12px; padding: 1.5rem; text-align: center; margin-bottom: 0.5rem;">
                            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">{icon}</div>
                            <div style="font-weight: 700; font-size: 1.1rem; color: #000000;">{subj_name}</div>
                            <div style="font-size: 0.85rem; color: #000000; margin-top: 0.3rem;">{len(subj_data.get('units', {}))} Units</div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    b1, b2 = st.columns([4, 1])
                    with b1:
                        if st.button("Manage Subject →", key=f"open_s_{subj_name}", use_container_width=True):
                            st.session_state.lib_subject = subj_name
                            st.session_state.lib_view = "units"
                            st.rerun()
                    with b2:
                        if st.button("🗑️", key=f"del_s_{subj_name}"):
                            delete_subject(uid, subj_name)
                            st.rerun()
        
        st.markdown("---")
        st.markdown("### ➕ New Subject")
        nc1, nc2 = st.columns([4, 1])
        with nc1:
            new_subj = st.text_input("Subject Name", placeholder="e.g. Physics, History...", label_visibility="collapsed")
        with nc2:
            if st.button("Add Subject", type="primary", use_container_width=True):
                if new_subj.strip():
                    create_subject(uid, new_subj.strip().title())
                    st.rerun()

    # ============================================================
    #  VIEW: UNITS
    # ============================================================
    elif view == "units":
        if st.button("← Back to Library"):
            st.session_state.lib_view = "subjects"
            st.rerun()
            
        st.markdown(f'<div class="page-title">{active_subject}</div>', unsafe_allow_html=True)
        st.markdown('<div class="page-subtitle">Select a topic or create a new one.</div>', unsafe_allow_html=True)

        library = get_user_library(uid)
        units = library.get(active_subject, {}).get("units", {})

        if units:
            cols = st.columns(2)
            for i, (unit_name, unit_data) in enumerate(units.items()):
                with cols[i % 2]:
                    st.markdown(f"""
                        <div style="background: #ffffff; border: 2px solid #000000; border-radius: 12px; padding: 1.2rem; margin-bottom: 0.5rem;">
                            <div style="font-weight: 700; font-size: 1rem; color: #000000;">{unit_name}</div>
                            <div style="font-size: 0.8rem; color: #000000; margin-top: 0.2rem;">
                                {len(unit_data.get('pdfs', []))} PDFs &middot; {len(unit_data.get('texts', []))} Text Materials
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    u1, u2 = st.columns([4, 1])
                    with u1:
                        if st.button("Open Topic →", key=f"open_u_{unit_name}", use_container_width=True):
                            st.session_state.lib_unit = unit_name
                            st.session_state.lib_view = "materials"
                            st.rerun()
                    with u2:
                        if st.button("🗑️", key=f"del_u_{unit_name}"):
                            delete_unit(uid, active_subject, unit_name)
                            st.rerun()
        
        st.markdown("---")
        st.markdown("### ➕ New Unit / Topic")
        uc1, uc2 = st.columns([4, 1])
        with uc1:
            new_unit = st.text_input("Unit Name", placeholder="e.g. Thermodynamics, World War I...", label_visibility="collapsed")
        with uc2:
            if st.button("Add Unit", type="primary", use_container_width=True):
                if new_unit.strip():
                    create_unit(uid, active_subject, new_unit.strip().title())
                    st.rerun()

    # ============================================================
    #  VIEW: MATERIALS
    # ============================================================
    elif view == "materials":
        if st.button("← Back to Topics"):
            st.session_state.lib_view = "units"
            st.rerun()

        st.markdown(f'<div class="page-title">{active_unit}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="page-subtitle">{active_subject} &middot; Manage your study materials.</div>', unsafe_allow_html=True)

        library = get_user_library(uid)
        unit_data = library.get(active_subject, {}).get("units", {}).get(active_unit, {})
        pdfs = unit_data.get("pdfs", [])
        texts = unit_data.get("texts", [])

        # Material summary and key actions
        if pdfs or texts:
            st.markdown("""
                <div style="background: #eef1ff; border-radius: 8px; padding: 1rem; margin-bottom: 1.5rem;">
                    <div style="font-weight: 600; color: #000000; margin-bottom: 0.5rem;">Ready to study?</div>
                </div>
            """, unsafe_allow_html=True)
            ac1, ac2 = st.columns(2)
            with ac1:
                if st.button("✨ Generate Study Aids", type="primary", use_container_width=True):
                    st.session_state.subject_name = active_subject
                    st.session_state.pre_select_unit = active_unit
                    st.session_state.page = "subject"
                    st.rerun()
            with ac2:
                if st.button("📝 Take Quiz", type="secondary", use_container_width=True):
                    st.session_state.page = "quizzes"
                    st.rerun()
        
        st.markdown("### 📁 Materials")
        
        # Display PDFs
        for pdf in pdfs:
            mc1, mc2 = st.columns([8, 1])
            with mc1:
                st.markdown(f"📄 **PDF:** {pdf['original_name']}")
            with mc2:
                if st.button("🗑️", key=f"del_pdf_{pdf['saved_name']}"):
                    delete_pdf(uid, active_subject, active_unit, pdf['saved_name'])
                    st.rerun()
                    
        # Display Texts
        for text in texts:
            mc1, mc2 = st.columns([8, 1])
            with mc1:
                st.markdown(f"✍️ **Text:** {text['title']}")
            with mc2:
                if st.button("🗑️", key=f"del_txt_{text['id']}"):
                    delete_text(uid, active_subject, active_unit, text['id'])
                    st.rerun()

        st.markdown("---")
        t1, t2 = st.tabs(["📤 Upload PDF", "✍️ Add Text Material"])
        
        with t1:
            uploaded = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True, label_visibility="collapsed")
            if uploaded:
                if st.button(f"Save {len(uploaded)} PDFs", type="primary"):
                    for f in uploaded:
                        save_pdf_to_unit(uid, active_subject, active_unit, f.name, f.read())
                    st.success("PDFs saved!")
                    st.rerun()
                    
        with t2:
            t_title = st.text_input("Material Title", placeholder="e.g. Chapter Summary, My Notes...")
            t_content = st.text_area("Content", placeholder="Paste your notes here...", height=200)
            if st.button("Save Text Material", type="primary"):
                if t_title and t_content:
                    save_text_to_unit(uid, active_subject, active_unit, t_title, t_content)
                    st.success("Text material saved!")
                    st.rerun()
