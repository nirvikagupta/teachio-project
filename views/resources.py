"""Study Space — Structured Pastel Bento Cards for Concept Lessons, Analogies, Cheat-Sheet, 3D Flashcards, Quiz, Concept Map, and Ask Tutor."""

import re
import streamlit as st
import streamlit.components.v1 as components
from utils.navigation import render_app_sidebar, render_assignment_journey_bar
from utils.styles import html, inject_styles, nav_to
from utils.storage import get_user_tasks, get_latest_resumable_task, save_user_task, save_active_auth_session
from utils.adhd_agents import (
    extract_and_teach_concepts,
    reshape_reading_text,
    generate_study_tool_content,
    decompose_assignment,
)


def _clean_title(text: str) -> str:
    return re.sub(r"^\d+\.\s*|\*\*", "", str(text or "")).strip()


def _format_card_html(raw_text: str, max_sentences: int = 3) -> str:
    """Cleans all Markdown syntax (#, ###, **, *, inline numbered lists) into concise, crisp HTML blocks."""
    if not raw_text:
        return ""
    txt = str(raw_text).strip()
    txt = re.sub(r"(?m)^\s*#{1,6}\s*$", "", txt)
    txt = re.sub(r"(?m)^\s*[-*_]{3,}\s*$", "", txt)
    txt = re.sub(r"(?m)^\s*#{1,6}\s+(.+)$", r"<b>\1</b>", txt)
    txt = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", txt)
    txt = re.sub(r"\*(.+?)\*", r"<i>\1</i>", txt)
    txt = re.sub(r"(?<!^)\s+(?=(?:\d+\.|\(\d+\)|•)\s)", "\n", txt)

    lines = [ln.strip() for ln in txt.split("\n") if ln.strip()]
    if not lines:
        return ""
    if len(lines) == 1:
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", lines[0]) if s.strip()]
        if max_sentences and len(sents) > max_sentences:
            sents = sents[:max_sentences]
        return f"<div style='line-height:1.58;'>{' '.join(sents)}</div>"

    out = []
    bullet_cnt = 0
    for ln in lines:
        clean_ln = re.sub(r"^[-•*]\s+", "", ln)
        if ln.startswith(("-", "•", "*")) or re.match(r"^(?:\d+\.|\(\d+\))\s", ln):
            bullet_cnt += 1
            if max_sentences and bullet_cnt > max_sentences + 1:
                break
            out.append(
                f"<div style='display:flex; gap:8px; align-items:flex-start; margin-bottom:5px; line-height:1.5;'>"
                f"<span style='color:#d7262b; font-weight:700;'>•</span>"
                f"<span>{clean_ln}</span></div>"
            )
        else:
            sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", ln) if s.strip()]
            if max_sentences and len(sents) > max_sentences:
                sents = sents[:max_sentences]
            out.append(f"<p style='margin:0 0 7px 0; line-height:1.58;'>{' '.join(sents)}</p>")
            if max_sentences and len(out) >= 2:
                break
    return "".join(out)


def _tts_speak(text_to_speak: str, rate: float = 1.0):
    clean_speech = re.sub(r"<[^>]+>|[*#_`]", "", text_to_speak or "")
    safe_txt = clean_speech.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("'", "\\'")[:1400]
    components.html(
        f"""
        <script>
        try {{
            const synth = window.parent.speechSynthesis || window.speechSynthesis;
            if (synth) {{
                synth.cancel();
                const u = new SpeechSynthesisUtterance("{safe_txt}");
                u.rate = {rate};
                synth.speak(u);
            }}
        }} catch (e) {{}}
        </script>
        """,
        height=0,
    )


def _tts_stop():
    components.html(
        """
        <script>
        try {
            const synth = window.parent.speechSynthesis || window.speechSynthesis;
            if (synth) synth.cancel();
        } catch (e) {}
        </script>
        """,
        height=0,
    )


def render():
    inject_styles()
    if not st.session_state.get("user_id"):
        nav_to("onboarding")
        return

    render_app_sidebar()
    uid = st.session_state.user_id

    all_tasks = get_user_tasks(uid)
    if not all_tasks:
        d_title = st.session_state.get("draft_title_text", "CV Assignment")
        d_brief = st.session_state.get("draft_brief_text") or (
            "Compare two approaches for measuring computer-vision model performance "
            "(Approach A: IoU overlap metrics vs. Approach B: Runtime efficiency)."
        )
        seeded = decompose_assignment(d_title, d_brief, "Coursework", "Friday")
        seeded["original_brief"] = d_brief
        seeded["current_step_idx"] = 0
        seeded["status"] = "active"
        tid = save_user_task(uid, seeded)
        st.session_state["current_task_id"] = tid
        all_tasks = get_user_tasks(uid)

    cur_tid = st.session_state.get("current_task_id")
    task_map = {t["id"]: t for t in all_tasks if t.get("id")}
    if cur_tid and cur_tid in task_map:
        active_task = task_map[cur_tid]
    else:
        active_task = get_latest_resumable_task(uid) or (all_tasks[0] if all_tasks else {})
        if active_task.get("id"):
            st.session_state["current_task_id"] = active_task["id"]

    if active_task.get("id"):
        st.session_state["current_task_id"] = active_task["id"]

    # Interactive 4-Step Journey Bar at the top
    render_assignment_journey_bar("concepts")

    task_key = active_task.get("id", "default")

    # Automatically extract and cache the academic concepts needed to do this assignment
    cache_key = f"extracted_concepts_{task_key}"
    cached_list = st.session_state.get(cache_key)
    if cached_list and any("Core Principle:" in c.get("name", "") or "Contrasting Mechanism:" in c.get("name", "") for c in cached_list):
        cached_list = None
        st.session_state.pop(cache_key, None)

    if not cached_list:
        if active_task.get("extracted_concepts"):
            st.session_state[cache_key] = active_task["extracted_concepts"]
        else:
            with st.spinner(f"AI is extracting the core academic concepts for '{active_task.get('title')}'..."):
                extracted = extract_and_teach_concepts(active_task).get("concepts", [])
                st.session_state[cache_key] = extracted
                if active_task.get("id") and extracted:
                    active_task["extracted_concepts"] = extracted
                    save_user_task(uid, active_task)
    concepts = st.session_state[cache_key]

    c_hdr, c_sw, c_to_work = st.columns([2.7, 1.5, 1.2], gap="medium")
    with c_hdr:
        html(f"""
<div style="margin-bottom: 0.35rem;">
  <span class="rs-subhead">CONCEPT TUTOR · {active_task.get('title', 'ASSIGNMENT').upper()}</span>
  <div class="page-title" style="margin:0; font-size:2.3rem;">Learn the <i>Concepts</i></div>
</div>
""")
    with c_sw:
        tid_list = list(task_map.keys())
        selected_tid = st.selectbox(
            "Assignment:",
            options=tid_list,
            format_func=lambda tid: task_map[tid].get("title", "Assignment"),
            index=tid_list.index(active_task["id"]) if active_task.get("id") in tid_list else 0,
            key="resources_header_task_picker",
        )
        if selected_tid != active_task.get("id"):
            st.session_state["current_task_id"] = selected_tid
            st.session_state["reading_layer_mode"] = "original"
            save_active_auth_session(uid, st.session_state.get("user_name", "Student"), True, selected_tid)
            st.rerun()
    with c_to_work:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("Workspace →", type="primary", use_container_width=True):
            st.session_state["current_task_id"] = active_task["id"]
            st.session_state["session_mode"] = "workspace"
            nav_to("active_session")

    # Extracted Concepts Pill Banner
    concept_badges = "".join(
        f"<span style='background:#fff1f2; color:#d7262b; border:1px solid #fecdd3; font-size:0.75rem; font-weight:700; padding:4px 12px; border-radius:99px;'>✦ {_clean_title(c.get('name', ''))}</span>"
        for c in concepts
    )
    html(f"""
<div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin:0.2rem 0 0.9rem 0;">
  <span style="font-size:0.73rem; font-weight:700; color:#785a54; text-transform:uppercase; letter-spacing:0.08em;">Concepts You Need:</span>
  {concept_badges}
</div>
""")

    tab_read, tab_cards, tab_quiz, tab_map, tab_explain = st.tabs([
        "📖 Concept Lessons",
        "🃏 Concept Flashcards",
        "❓ Concept Quiz",
        "🗺️ Concept Map",
        "💬 Ask Tutor",
    ])

    pastel_headers = [
        ("#fff5f6", "#fecdd3", "#d7262b"),
        ("#eff6ff", "#bfdbfe", "#1d4ed8"),
        ("#e8f5e9", "#bbf7d0", "#15803d"),
        ("#f3e8ff", "#e9d5ff", "#6d28d9"),
    ]

    # =========================================================================
    # 1. CONCEPT LESSONS (Structured Bento Cards for Full Lessons, Simple Analogies, and Cheat-Sheet!)
    # =========================================================================
    with tab_read:
        full_lessons_text = ". ".join(
            f"{c.get('name')}. {c.get('intuition')} {c.get('analogy_or_example')}"
            for c in concepts
        )
        current_view = st.session_state.get("reading_layer_mode", "original")

        b1, b2, b3, b4, b5 = st.columns(5)
        with b1:
            if st.button("Full Lessons", use_container_width=True, type="primary" if current_view == "original" else "secondary"):
                st.session_state["reading_layer_mode"] = "original"
                st.rerun()
        with b2:
            if st.button("✨ Simple Analogies", use_container_width=True, type="primary" if current_view == "simplify" else "secondary"):
                st.session_state["reading_layer_mode"] = "simplify"
                st.rerun()
        with b3:
            if st.button("📋 Cheat-Sheet", use_container_width=True, type="primary" if current_view == "summarize" else "secondary"):
                st.session_state["reading_layer_mode"] = "summarize"
                st.rerun()
        with b4:
            if st.button("🔊 Read Aloud", use_container_width=True):
                _tts_speak(full_lessons_text, 1.0)
        with b5:
            if st.button("⏹ Stop", use_container_width=True):
                _tts_stop()

        st.markdown("<div style='height:0.4rem;'></div>", unsafe_allow_html=True)

        # MODE A: FULL LESSONS (Concise, Bite-Sized 2-Column Pastel Bento Cards)
        if current_view == "original":
            cols = st.columns(2, gap="medium")
            for idx, c in enumerate(concepts):
                bg_c, brd_c, acc_c = pastel_headers[idx % len(pastel_headers)]
                clean_title = _clean_title(c.get("name", "Concept"))
                intuition_html = _format_card_html(c.get("intuition") or "", max_sentences=1)
                lesson_html = _format_card_html(c.get("lesson") or "", max_sentences=2)
                analogy_html = _format_card_html(c.get("analogy_or_example") or "", max_sentences=1)
                with cols[idx % 2]:
                    html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-radius:26px; padding:1.3rem 1.45rem; margin-bottom:0.9rem; box-shadow:0 8px 24px rgba(160,40,50,0.04);">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.35rem;">
    <span style="background:{bg_c}; color:{acc_c}; border:1px solid {brd_c}; font-size:0.66rem; font-weight:700; padding:3px 10px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
      0{idx+1} · {c.get('category', 'CORE CONCEPT')}
    </span>
  </div>
  <div class="rs-serif" style="font-size:1.58rem; color:#2a1714; line-height:1.15; margin-bottom:0.55rem;">
    {clean_title}
  </div>
  <div style="background:{bg_c}; border-radius:14px; padding:0.7rem 0.95rem; margin-bottom:0.65rem;">
    <div class="rs-subhead" style="color:{acc_c}; font-size:0.6rem; margin-bottom:2px;">CORE IDEA</div>
    <div style="font-size:0.89rem; font-weight:600; color:#2a1714;">{intuition_html}</div>
  </div>
  <div style="font-size:0.88rem; color:#2a1714; margin-bottom:0.65rem;">
    {lesson_html}
  </div>
  <div style="background:#fcf5ef; border-left:3.5px solid {acc_c}; border-radius:0 12px 12px 0; padding:0.65rem 0.9rem; font-size:0.84rem; color:#5b4540;">
    <div class="rs-subhead" style="color:{acc_c}; font-size:0.59rem; margin-bottom:2px;">EXAMPLE</div>
    {analogy_html}
  </div>
</div>
""")

        # MODE B: SIMPLE ANALOGIES (2x2 Pastel Bento Analogy Cards — zero raw Markdown!)
        elif current_view == "simplify":
            cols = st.columns(2, gap="medium")
            for idx, c in enumerate(concepts):
                bg_c, brd_c, acc_c = pastel_headers[idx % len(pastel_headers)]
                clean_title = re.sub(r"^\d+\.\s*", "", c.get("name", "Concept"))
                intuition_html = _format_card_html(c.get("intuition") or "")
                analogy_html = _format_card_html(c.get("analogy_or_example") or "")
                with cols[idx % 2]:
                    html(f"""
<div style="background:{bg_c}; border:1.5px solid {brd_c}; border-radius:26px; padding:1.5rem 1.65rem; margin-bottom:1rem; min-height:230px; display:flex; flex-direction:column; justify-content:space-between;">
  <div>
    <span style="background:#ffffff; color:{acc_c}; border:1px solid {brd_c}; font-size:0.68rem; font-weight:700; padding:3px 11px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
      EVERYDAY ANALOGY 0{idx+1}
    </span>
    <div class="rs-serif" style="font-size:1.7rem; color:#2a1714; line-height:1.15; margin:0.55rem 0 0.7rem 0;">
      {clean_title}
    </div>
    <div style="background:#ffffff; border-radius:18px; padding:1rem 1.15rem; margin-bottom:0.75rem; font-size:0.95rem; color:#2a1714;">
      <div class="rs-subhead" style="color:{acc_c}; font-size:0.63rem; margin-bottom:4px;">THINK OF IT LIKE THIS</div>
      {analogy_html}
    </div>
  </div>
  <div style="font-size:0.88rem; color:#5b4540; padding:0 4px;">
    <b style="color:{acc_c};">In 1 sentence:</b> {intuition_html}
  </div>
</div>
""")

        # MODE C: CHEAT-SHEET (2x2 Pastel Bento Cheat-Sheet Cards — zero raw '#' or '###'!)
        else:
            cols = st.columns(2, gap="medium")
            for idx, c in enumerate(concepts):
                bg_c, brd_c, acc_c = pastel_headers[idx % len(pastel_headers)]
                clean_title = re.sub(r"^\d+\.\s*", "", c.get("name", "Concept"))
                intuition_html = _format_card_html(c.get("intuition") or "")
                takeaway_html = _format_card_html(c.get("key_takeaway") or "")
                with cols[idx % 2]:
                    html(f"""
<div style="background:#ffffff; border:1.5px solid #f2e2dc; border-top:5px solid {acc_c}; border-radius:24px; padding:1.45rem 1.6rem; margin-bottom:1rem; min-height:220px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 8px 22px rgba(160,40,50,0.04);">
  <div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="background:{bg_c}; color:{acc_c}; font-size:0.68rem; font-weight:700; padding:3px 10px; border-radius:99px; text-transform:uppercase; letter-spacing:0.08em;">
        CHEAT-SHEET 0{idx+1} · {c.get('category', 'CONCEPT')}
      </span>
    </div>
    <div class="rs-serif" style="font-size:1.65rem; color:#2a1714; line-height:1.15; margin:0.45rem 0 0.65rem 0;">
      {clean_title}
    </div>
    <div style="background:#fcf5ef; border-radius:14px; padding:0.8rem 1rem; margin-bottom:0.7rem; font-size:0.91rem; color:#2a1714;">
      <div class="rs-subhead" style="color:#785a54; font-size:0.62rem; margin-bottom:3px;">DEFINITION</div>
      {intuition_html}
    </div>
  </div>
  <div style="background:{bg_c}; border-radius:14px; padding:0.8rem 1rem; font-size:0.9rem; color:#2a1714;">
    <div class="rs-subhead" style="color:{acc_c}; font-size:0.62rem; margin-bottom:3px;">HOW TO APPLY IT</div>
    {takeaway_html}
  </div>
</div>
""")

    # =========================================================================
    # 2. CONCEPT FLASHCARDS (Interactive 3D Flippable Cards with Clean Formatting)
    # =========================================================================
    with tab_cards:
        fc_key = f"study_cards_{task_key}"
        c_fc_top1, c_fc_top2 = st.columns([3.8, 1.2])
        with c_fc_top1:
            html("<div style='font-size:0.9rem; color:#6b524c; margin-bottom:0.4rem;'>Click any card below to flip between the <b>Concept Question</b> and the <b>Answer</b>.</div>")
        with c_fc_top2:
            if st.button("↻ New Cards", key=f"regen_fc_{task_key}", use_container_width=True):
                st.session_state.pop(fc_key, None)
                active_task.pop("study_cards", None)
                save_user_task(uid, active_task)
                st.rerun()

        if fc_key not in st.session_state:
            saved_fc = active_task.get("study_cards")
            if saved_fc and not any("Core Principle:" in str(c) for c in saved_fc):
                st.session_state[fc_key] = saved_fc
            else:
                gen_fc = generate_study_tool_content(active_task, "flashcards").get("cards", [])
                st.session_state[fc_key] = gen_fc
                if active_task.get("id") and gen_fc:
                    active_task["study_cards"] = gen_fc
                    save_user_task(uid, active_task)
        cards = st.session_state.get(fc_key, [])

        html("""
<style>
.fc-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 18px;
    margin: 0.6rem 0 1.2rem 0;
}
.fc-label {
    display: block;
    perspective: 1200px;
    cursor: pointer;
    user-select: none;
    height: 275px;
}
.fc-checkbox {
    display: none;
}
.fc-inner {
    position: relative;
    width: 100%;
    height: 100%;
    transition: transform 0.55s cubic-bezier(0.22, 1, 0.36, 1);
    transform-style: preserve-3d;
}
.fc-checkbox:checked + .fc-inner {
    transform: rotateY(180deg);
}
.fc-face {
    position: absolute;
    inset: 0;
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;
    border-radius: 26px;
    padding: 1.5rem 1.7rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 10px 26px rgba(160, 40, 50, 0.06);
    overflow-y: auto;
}
.fc-front:hover {
    transform: translateY(-3px);
    box-shadow: 0 14px 32px rgba(160, 40, 50, 0.11);
}
.fc-back {
    transform: rotateY(180deg);
    background: #ffffff;
}
</style>
""")

        cards_html_items = []
        for idx, card in enumerate(cards):
            bg, brd, acc = pastel_headers[idx % len(pastel_headers)]
            front_q = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", card.get("front", ""))
            back_a = _format_card_html(card.get("back", ""))
            cards_html_items.append(f"""
<label class="fc-label">
  <input type="checkbox" class="fc-checkbox">
  <div class="fc-inner">
    <div class="fc-face fc-front" style="background:{bg}; border:1.5px solid {brd};">
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="background:#ffffff; color:{acc}; border:1px solid {brd}; font-size:0.68rem; font-weight:700; padding:3px 11px; border-radius:99px; letter-spacing:0.1em; text-transform:uppercase;">
          CONCEPT CARD 0{idx+1}
        </span>
        <span style="font-size:0.75rem; font-weight:700; color:{acc}; opacity:0.85;">
          ↻ Click to flip
        </span>
      </div>
      <div class="rs-serif" style="font-size:1.65rem; color:#2a1714; line-height:1.22; margin:auto 0;">
        {front_q}
      </div>
      <div style="font-size:0.76rem; color:#6b524c; font-weight:600;">
        Tap anywhere on card to reveal answer →
      </div>
    </div>

    <div class="fc-face fc-back" style="border:2px solid {acc};">
      <div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; padding-bottom:0.5rem; border-bottom:1px solid {brd};">
          <span style="background:{bg}; color:{acc}; font-size:0.68rem; font-weight:700; padding:3px 11px; border-radius:99px; letter-spacing:0.1em; text-transform:uppercase;">
            ANSWER 0{idx+1}
          </span>
          <span style="font-size:0.75rem; font-weight:700; color:{acc};">
            ↻ Flip back
          </span>
        </div>
        <div style="font-size:0.92rem; color:#2a1714;">
          {back_a}
        </div>
      </div>
    </div>
  </div>
</label>
""")

        html(f"<div class='fc-grid'>{''.join(cards_html_items)}</div>")

    # =========================================================================
    # 3. CONCEPT QUIZ (Clean Pastel Bento Question Cards)
    # =========================================================================
    with tab_quiz:
        qz_key = f"study_quiz_{task_key}"
        if st.session_state.get(qz_key) and any("Core Principle:" in str(q) or "Contrasting Mechanism:" in str(q) for q in st.session_state[qz_key]):
            st.session_state.pop(qz_key, None)
        if qz_key not in st.session_state:
            saved_qz = active_task.get("study_quiz")
            if saved_qz and not any("Core Principle:" in str(q) or "Contrasting Mechanism:" in str(q) for q in saved_qz):
                st.session_state[qz_key] = saved_qz
            else:
                gen_qz = generate_study_tool_content(active_task, "quiz").get("questions", [])
                st.session_state[qz_key] = gen_qz
                if active_task.get("id") and gen_qz:
                    active_task["study_quiz"] = gen_qz
                    save_user_task(uid, active_task)
        questions = st.session_state.get(qz_key, [])
        for q_idx, q in enumerate(questions):
            bg_c, brd_c, acc_c = pastel_headers[q_idx % len(pastel_headers)]
            clean_q = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", q.get("question", ""))
            html(f"""
<div style="background:{bg_c}; border:1.5px solid {brd_c}; border-radius:22px; padding:1.2rem 1.5rem; margin:0.8rem 0 0.5rem 0;">
  <span style="background:#ffffff; color:{acc_c}; font-size:0.66rem; font-weight:700; padding:3px 10px; border-radius:99px; letter-spacing:0.08em; text-transform:uppercase;">
    CONCEPT CHECK 0{q_idx+1}
  </span>
  <div class="rs-serif" style="font-size:1.5rem; color:#2a1714; margin-top:6px; line-height:1.2;">{clean_q}</div>
</div>
""")
            opts = [re.sub(r"\*\*(.+?)\*\*", r"\1", str(o)) for o in q.get("options", [])]
            ans_idx = int(q.get("answer", 0))
            user_pick = st.radio("Answer:", opts, key=f"qz_pick_{task_key}_{q_idx}", label_visibility="collapsed")
            if st.button(f"Check Answer #{q_idx+1}", key=f"qz_chk_{task_key}_{q_idx}"):
                clean_exp = re.sub(r"\*\*(.+?)\*\*", r"\1", q.get("explanation", ""))
                if opts and user_pick == opts[min(ans_idx, len(opts) - 1)]:
                    st.success(f"✓ Correct! {clean_exp}")
                else:
                    st.info(f"Key takeaway: {clean_exp}")

    # =========================================================================
    # 4. CONCEPT MAP (2x2 Pastel Bento Concept Map Grid)
    # =========================================================================
    with tab_map:
        mm_key = f"study_mindmap_{task_key}"
        if st.session_state.get(mm_key) and any("Core Principle:" in str(n) or "Contrasting Mechanism:" in str(n) for n in st.session_state[mm_key]):
            st.session_state.pop(mm_key, None)
        if mm_key not in st.session_state:
            saved_mm = active_task.get("study_mindmap")
            if saved_mm and not any("Core Principle:" in str(n) or "Contrasting Mechanism:" in str(n) for n in saved_mm):
                st.session_state[mm_key] = saved_mm
            else:
                gen_mm = generate_study_tool_content(active_task, "mind_map").get("nodes", [])
                st.session_state[mm_key] = gen_mm
                if active_task.get("id") and gen_mm:
                    active_task["study_mindmap"] = gen_mm
                    save_user_task(uid, active_task)

        nodes = st.session_state.get(mm_key, [])
        mm_cols = st.columns(2, gap="medium")
        for idx, node in enumerate(nodes):
            bg_c, brd_c, acc_c = pastel_headers[idx % len(pastel_headers)]
            clean_concept = _clean_title(node.get("concept", "Concept"))
            rel_pills = "".join(
                f"<span style='background:#ffffff; color:{acc_c}; border:1px solid {brd_c}; font-size:0.75rem; font-weight:600; padding:4px 10px; border-radius:99px;'>→ {_clean_title(r)}</span>"
                for r in node.get("relationships", [])
            )
            example_html = _format_card_html(node.get("example", ""))
            with mm_cols[idx % 2]:
                html(f"""
<div style="background:{bg_c}; border:1.5px solid {brd_c}; border-radius:26px; padding:1.45rem 1.6rem; margin-bottom:1rem; min-height:215px; display:flex; flex-direction:column; justify-content:space-between;">
  <div>
    <span style="background:#ffffff; color:{acc_c}; font-size:0.66rem; font-weight:700; padding:3px 10px; border-radius:99px; letter-spacing:0.08em; text-transform:uppercase;">
      CONCEPT NODE 0{idx+1}
    </span>
    <div class="rs-serif" style="font-size:1.65rem; color:#2a1714; margin:0.45rem 0 0.6rem 0; line-height:1.15;">
      {clean_concept}
    </div>
    <div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:0.8rem;">
      {rel_pills}
    </div>
  </div>
  <div style="background:#ffffff; border-radius:16px; padding:0.85rem 1.05rem; font-size:0.89rem; color:#2a1714;">
    <div class="rs-subhead" style="color:{acc_c}; font-size:0.62rem; margin-bottom:3px;">CONCRETE APPLICATION</div>
    {example_html}
  </div>
</div>
""")

    # =========================================================================
    # 5. ASK CONCEPT TUTOR (2 Side-by-Side Pastel Bento Cards)
    # =========================================================================
    with tab_explain:
        first_concept_name = _clean_title(concepts[0].get("name", "this concept")) if concepts else "the main concept"
        default_q = f"How does {first_concept_name} work in simple terms?"
        q_input = st.text_input(
            "Ask about any concept, formula, or mechanism:",
            value=default_q,
        )
        if st.button("Teach Me This Concept →", type="primary"):
            st.session_state["reading_explain_overlay"] = reshape_reading_text(q_input, "explain", active_task.get("title", ""))
        overlay = st.session_state.get("reading_explain_overlay")
        if overlay:
            exp_html = _format_card_html(overlay.get("simpler_language", ""))
            ana_html = _format_card_html(overlay.get("why_it_matters", ""))
            html(f"""
<div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:0.9rem;">
  <div style="background:#fff5f6; border:1.5px solid #fecdd3; border-radius:24px; padding:1.4rem 1.6rem;">
    <div class="rs-subhead" style="font-size:0.66rem; margin-bottom:6px;">💡 CONCEPT EXPLANATION</div>
    <div style="font-size:0.96rem; color:#2a1714;">{exp_html}</div>
  </div>
  <div style="background:#eff6ff; border:1.5px solid #bfdbfe; border-radius:24px; padding:1.4rem 1.6rem;">
    <div class="rs-subhead" style="color:#1d4ed8; font-size:0.66rem; margin-bottom:6px;">🌍 REAL-WORLD ANALOGY</div>
    <div style="font-size:0.96rem; color:#1e3a8a;">{ana_html}</div>
  </div>
</div>
""")
