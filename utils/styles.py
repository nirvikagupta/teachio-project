import streamlit as st
from utils.storage import save_active_auth_session

RED = "#d7262b"
PINK = "#f9d5da"
CREAM = "#fcf5ef"
INK = "#2a1714"
BLUE = "#c8daf4"


def inject_styles():
    """Global MODOA editorial theme with Instrument Serif (headlines) and Albert Sans (subheadlines & body)."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Albert+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Instrument+Serif:ital@0;1&family=JetBrains+Mono:wght@500;600;700&display=swap');

        html, body, p, li, input, textarea, label {{
            font-family: 'Albert Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {INK};
        }}

        /* Preserve Streamlit's Material Symbols icon font so arrows never print 'keyb...' */
        [data-testid="stIconMaterial"],
        .material-symbols-rounded,
        span[translate="no"] {{
            font-family: 'Material Symbols Rounded' !important;
        }}

        h1, h2, h3, .page-title, .rs-serif {{
            font-family: 'Instrument Serif', Georgia, serif !important;
            font-weight: 400 !important;
            letter-spacing: -0.01em;
            color: {INK};
        }}

        /* Hide Deploy button, MainMenu, and footer while keeping the sidebar expand/collapse arrow working */
        #MainMenu,
        footer,
        .stDeployButton,
        [data-testid="stAppDeployButton"],
        [data-testid="stDeployButton"],
        [data-testid="stToolbarActions"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"] {{
            display: none !important;
        }}

        header[data-testid="stHeader"] {{
            background: transparent !important;
        }}

        /* Style the sidebar collapse/expand button cleanly without overriding its Material icon font */
        [data-testid="collapsedControl"],
        [data-testid="stExpandSidebarButton"] {{
            background: {CREAM} !important;
            border: 1.5px solid #ebd5ce !important;
            border-radius: 50% !important;
            box-shadow: 0 4px 12px rgba(160, 40, 50, 0.1) !important;
        }}

        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] div:not([data-testid="stIconMaterial"]),
        [data-testid="stSidebar"] button {{
            color: {INK};
            font-family: 'Albert Sans', sans-serif;
        }}

        /* Unified Landing Page Theme across the entire application */
        .stApp {{
            background-color: {PINK} !important;
            color: {INK};
        }}

        .block-container {{
            max-width: 1140px !important;
            background: {CREAM} !important;
            border-radius: 32px !important;
            padding: 1.8rem 2.5rem 2.8rem 2.5rem !important;
            margin-top: 1.3rem !important;
            margin-bottom: 2rem !important;
            box-shadow: 0 24px 70px rgba(160, 40, 50, 0.09) !important;
        }}

        /* Sidebar matching editorial cream & blush palette */
        [data-testid="stSidebar"] {{
            background: {CREAM} !important;
            border-right: 1.5px solid #f2d6d9 !important;
            box-shadow: none !important;
        }}

        [data-testid="stSidebar"] [data-testid="stIconMaterial"],
        [data-testid="stHeader"] [data-testid="stIconMaterial"] {{
            font-family: 'Material Symbols Rounded' !important;
        }}

        .restart-brand {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 0.4rem 0 1.1rem 0;
            border-bottom: 1.5px solid #f2dfd8;
            margin-bottom: 1rem;
        }}

        .brand-logo {{
            width: 38px;
            height: 38px;
            background: {RED};
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(215, 38, 43, 0.28);
        }}

        .brand-text {{
            font-family: 'Instrument Serif', Georgia, serif !important;
            font-size: 1.75rem;
            font-weight: 400;
            color: {INK} !important;
            line-height: 1;
        }}

        .brand-badge {{
            font-family: 'Albert Sans', sans-serif;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            background: #fff0f1;
            color: {RED} !important;
            padding: 2px 8px;
            border-radius: 99px;
            font-weight: 700;
            display: inline-block;
            margin-top: 3px;
        }}

        /* Pill Buttons matching Landing Page — single-line, equal height, never wrap words */
        .stButton > button {{
            border-radius: 999px !important;
            font-family: 'Albert Sans', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.86rem !important;
            height: 40px !important;
            min-height: 40px !important;
            padding: 0 1.05rem !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: all 0.18s ease !important;
            border: 1.5px solid #ebd5ce !important;
            background: #ffffff !important;
            color: {INK} !important;
            box-shadow: 0 3px 10px rgba(160, 40, 50, 0.04) !important;
        }}

        .stButton > button p {{
            white-space: nowrap !important;
            margin: 0 !important;
            line-height: 1 !important;
        }}

        .stButton > button:hover {{
            border-color: {RED} !important;
            color: {RED} !important;
            background: #fff5f6 !important;
            transform: translateY(-1px) !important;
        }}

        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"],
        [data-testid="stBaseButton-primary"] {{
            background: {RED} !important;
            color: #ffffff !important;
            border: none !important;
            box-shadow: 0 6px 18px rgba(215, 38, 43, 0.28) !important;
        }}

        .stButton > button[kind="primary"] *,
        [data-testid="stBaseButton-primary"] * {{
            color: #ffffff !important;
        }}

        .stButton > button[kind="primary"]:hover,
        [data-testid="stBaseButton-primary"]:hover {{
            background: #b51d22 !important;
            color: #ffffff !important;
        }}

        /* Page Headers: Instrument Serif headline + Albert Sans subheadline */
        .page-title {{
            font-family: 'Instrument Serif', Georgia, serif !important;
            font-size: 2.65rem;
            font-weight: 400;
            color: {INK};
            line-height: 1.12;
            margin-bottom: 0.25rem;
        }}

        .page-subtitle {{
            font-family: 'Albert Sans', sans-serif !important;
            font-size: 0.96rem;
            color: #6b524c;
            margin-bottom: 1.35rem;
            font-weight: 400;
            line-height: 1.55;
        }}

        .rs-subhead {{
            font-family: 'Albert Sans', sans-serif !important;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            color: {RED};
        }}

        .rs-mono {{
            font-family: 'Albert Sans', sans-serif !important;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        }}

        /* Editorial Cards */
        .warm-card {{
            background: #ffffff;
            border: 1.5px solid #f2e2dc;
            border-radius: 22px;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 10px 28px rgba(160, 40, 50, 0.05);
        }}

        /* Step Pill Card - distinct boxed container for every decomposed step */
        .step-pill {{
            background: #ffffff;
            border: 1.5px solid #f2e2dc;
            border-left: 5px solid {RED};
            border-radius: 20px;
            padding: 1.45rem 1.7rem;
            margin-bottom: 1.3rem;
            box-shadow: 0 10px 26px rgba(160, 40, 50, 0.06);
        }}

        .step-number {{
            font-family: 'Instrument Serif', Georgia, serif !important;
            font-size: 1.45rem;
            color: {INK};
        }}

        .first-action-box {{
            background: #fff5f6;
            border: 1px solid #fecdd3;
            border-radius: 14px;
            padding: 0.85rem 1.1rem;
            margin-top: 0.75rem;
            color: #881337;
            font-size: 0.92rem;
            line-height: 1.5;
        }}

        /* Hero Context Card */
        .cr-hero-card {{
            background: #ffffff;
            border: 2px solid #fecdd3;
            border-radius: 24px;
            padding: 1.8rem 2.1rem;
            margin-bottom: 1.4rem;
            box-shadow: 0 14px 36px rgba(215, 38, 43, 0.08);
        }}

        .context-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 14px;
            margin: 1.2rem 0;
        }}

        .context-box {{
            border-radius: 16px;
            padding: 1.05rem 1.2rem;
            display: flex;
            flex-direction: column;
            gap: 6px;
        }}

        .box-finished {{
            background: #f0fdf4;
            border: 1.5px solid #bbf7d0;
        }}

        .box-stuck {{
            background: #fffbeb;
            border: 1.5px solid #fde68a;
        }}

        .box-thought {{
            background: #faf5ff;
            border: 1.5px solid #e9d5ff;
        }}

        .box-title {{
            display: flex;
            align-items: center;
            gap: 6px;
            font-family: 'Albert Sans', sans-serif;
            font-size: 0.76rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        .box-body {{
            font-family: 'Albert Sans', sans-serif;
            font-size: 0.95rem;
            line-height: 1.5;
        }}

        .next-action-card {{
            background: #fff1f2;
            border: 1.5px solid #fecdd3;
            border-left: 5px solid {RED};
            border-radius: 16px;
            padding: 1.15rem 1.4rem;
            margin-top: 1rem;
            display: flex;
            align-items: center;
            gap: 14px;
        }}

        .next-action-icon {{
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: #ffe4e6;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
        }}

        .tag-status {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-family: 'Albert Sans', sans-serif;
            font-size: 0.72rem;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 99px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}
        .tag-active {{ background: #fff1f2; color: {RED}; border: 1px solid #fecdd3; }}
        .tag-paused {{ background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }}
        .tag-done {{ background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }}

        .adhd-progress-bg {{
            background: #f3e5e0;
            border-radius: 99px;
            height: 7px;
            width: 100%;
            overflow: hidden;
            margin: 0.55rem 0;
        }}
        .adhd-progress-fg {{
            height: 7px;
            border-radius: 99px;
            background: {RED};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def html(markup: str) -> None:
    """Render raw HTML safely in the main DOM so all injected CSS classes apply."""
    clean_lines = [line.strip() for line in markup.splitlines() if line.strip()]
    st.markdown("\n".join(clean_lines), unsafe_allow_html=True)


def nav_to(page: str) -> None:
    st.session_state.page = page
    uid = st.session_state.get("user_id")
    if uid:
        save_active_auth_session(
            user_id=uid,
            user_name=st.session_state.get("user_name"),
            profile_complete=bool(st.session_state.get("profile_complete", True)),
            current_task_id=st.session_state.get("current_task_id"),
        )
    if hasattr(st, "query_params"):
        st.query_params["p"] = page
    st.rerun()


def render_flow_bar(active_stage: int = 1) -> None:
    """Removed top numbered slideshow bar so every inside page feels like a clean, native web platform."""
    return
