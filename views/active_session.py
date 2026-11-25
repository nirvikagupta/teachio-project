"""Workspace & Pause — Spacious Pastel Bento Platform Layout with Assignment Switcher & Instant Snapshot Capture."""

import streamlit as st
import streamlit.components.v1 as components
from utils.navigation import render_app_sidebar, render_assignment_journey_bar
from utils.styles import html, inject_styles, nav_to
from utils.storage import (
    get_task_by_id,
    get_user_tasks,
    save_user_task,
    save_context_restore,
    save_active_auth_session,
    log_task_metric,
    get_latest_resumable_task,
)
from utils.adhd_agents import (
    get_stuck_support,
    generate_context_summary,
    decompose_assignment,
)


def _build_instant_snapshot(task: dict, notes_text: str, stuck_on_override: str = "") -> dict:
    """Fast, zero-latency snapshot builder from live notes, checked subtasks, and current step."""
    steps = task.get("steps", [{}])
    cur_idx = min(task.get("current_step_idx", 0), max(0, len(steps) - 1))
    cur_step = steps[cur_idx] if steps else {}
    phase = cur_step.get("phase", f"Step {cur_idx + 1}")
    st_title = cur_step.get("title", "Current stage")

    completed_steps = [s.get("title") for s in steps if s.get("completed")]
    checked_map = cur_step.get("subtask_checks", {})
    subtasks = cur_step.get("subtasks", [])
    checked_subs = [subtasks[int(k)] for k, v in checked_map.items() if v and k.isdigit() and int(k) < len(subtasks)]
    unchecked_subs = [subtasks[i] for i in range(len(subtasks)) if not checked_map.get(str(i), False)]

    all_done = completed_steps + checked_subs
    if not all_done:
        all_done = [f"Started {phase}"]

    note_lines = [ln.strip() for ln in (notes_text or "").splitlines() if ln.strip()]
    last_line = note_lines[-1] if note_lines else task.get("simplified_brief", "Structuring key arguments.")
    tried_summary = f"Drafted {len((notes_text or '').split())} words in Workspace notes" if note_lines else f"Working through {phase} checklist"

    next_act = unchecked_subs[0] if unchecked_subs else cur_step.get("first_action", "Continue to next step.")
    stuck_val = stuck_on_override.strip() or (f"Finishing: {unchecked_subs[0]}" if unchecked_subs else "Ready for next step")

    return {
        "working_on": f"{phase} — {st_title}",
        "completed": all_done[:4],
        "tried": tried_summary,
        "stuck_on": stuck_val,
        "last_thought": last_line[:160],
        "next_step": next_act,
    }


def _render_live_timer_widget(timer_style: str, est_minutes: int = 20):
    """Renders a live, ticking HTML/JS Bento Timer matching the selected ADHD timer style."""
    mode_config = {
        "Flow Count-Up": {"mode": "up", "seconds": 0, "label": "FLOW STOPWATCH · COUNT UP", "bg": "#e8f5e9", "accent": "#15803d", "sub": "No alarm — protects hyperfocus"},
        "2-Min Micro-Sprint": {"mode": "down", "seconds": 120, "label": "2-MIN ACTIVATION SPRINT", "bg": "#fff5f6", "accent": "#d7262b", "sub": "Just 2 minutes to beat task freeze"},
        "15-Min Gentle Sprint": {"mode": "down", "seconds": 900, "label": "15-MIN GENTLE SPRINT", "bg": "#eff6ff", "accent": "#1d4ed8", "sub": "Short, structured focus block"},
        "25-Min Classic Focus": {"mode": "down", "seconds": 1500, "label": "25-MIN FOCUS BLOCK", "bg": "#fff8eb", "accent": "#b45309", "sub": "Classic block with soft visual bar"},
        "Step Estimate": {"mode": "down", "seconds": max(est_minutes, 5) * 60, "label": f"{est_minutes}-MIN STEP PACER", "bg": "#f3e8ff", "accent": "#6d28d9", "sub": "Paced to this step's estimate"},
        "Zen (Hide Numbers)": {"mode": "zen", "seconds": 0, "label": "ZEN FLOW MODE", "bg": "#e8f5e9", "accent": "#15803d", "sub": "No ticking clock anxiety"},
    }
    cfg = mode_config.get(timer_style, mode_config["Flow Count-Up"])

    components.html(
        f"""
        <!DOCTYPE html>
        <html>
        <head>
        <link href="https://fonts.googleapis.com/css2?family=Albert+Sans:wght@500;600;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
        <style>
          * {{ box-sizing: border-box; margin: 0; padding: 0; }}
          body {{ background: transparent; font-family: 'Albert Sans', sans-serif; color: #2a1714; }}
          .timer-card {{
            background: {cfg['bg']};
            border-radius: 22px;
            padding: 15px 18px;
            display: flex;
            flex-direction: column;
            gap: 10px;
          }}
          .top-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
          }}
          .label {{
            font-size: 10.5px;
            font-weight: 700;
            letter-spacing: 0.12em;
            color: {cfg['accent']};
            text-transform: uppercase;
          }}
          .status-dot {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 11px;
            font-weight: 700;
            color: {cfg['accent']};
            background: rgba(255,255,255,0.75);
            padding: 3px 10px;
            border-radius: 99px;
          }}
          .pulse {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: {cfg['accent']};
            animation: pulseAnim 2s infinite;
          }}
          @keyframes pulseAnim {{
            0% {{ transform: scale(0.95); opacity: 0.7; }}
            50% {{ transform: scale(1.2); opacity: 1; }}
            100% {{ transform: scale(0.95); opacity: 0.7; }}
          }}
          .mid-row {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
          }}
          .time-display {{
            font-family: 'Instrument Serif', Georgia, serif;
            font-size: 42px;
            line-height: 1;
            color: #2a1714;
          }}
          .zen-display {{
            font-family: 'Instrument Serif', Georgia, serif;
            font-size: 26px;
            line-height: 1.1;
            color: #2a1714;
            padding: 6px 0;
          }}
          .btn-row {{
            display: flex;
            gap: 6px;
          }}
          button {{
            font-family: 'Albert Sans', sans-serif;
            font-size: 12px;
            font-weight: 700;
            border-radius: 99px;
            padding: 5px 13px;
            cursor: pointer;
            border: 1.5px solid rgba(42,23,20,0.12);
            background: #ffffff;
            color: #2a1714;
            transition: all 0.15s ease;
          }}
          button:hover {{
            border-color: {cfg['accent']};
            color: {cfg['accent']};
          }}
          button.primary {{
            background: {cfg['accent']};
            color: #ffffff;
            border: none;
          }}
          .prog-bg {{
            width: 100%;
            height: 6px;
            background: rgba(255,255,255,0.8);
            border-radius: 99px;
            overflow: hidden;
          }}
          .prog-fg {{
            height: 100%;
            width: 0%;
            background: {cfg['accent']};
            border-radius: 99px;
            transition: width 0.4s ease;
          }}
          .sub {{
            font-size: 11.5px;
            color: #5b4540;
          }}
        </style>
        </head>
        <body>
          <div class="timer-card">
            <div class="top-row">
              <span class="label">{cfg['label']}</span>
              <span class="status-dot"><span class="pulse"></span><span id="stateTxt">In Flow</span></span>
            </div>
            <div class="mid-row">
              <div id="clock" class="{'zen-display' if cfg['mode'] == 'zen' else 'time-display'}">
                {'Calm Focus · Clock Hidden' if cfg['mode'] == 'zen' else '00:00'}
              </div>
              <div class="btn-row">
                <button id="toggleBtn" class="primary" onclick="toggleTimer()">Pause</button>
                <button onclick="resetTimer()">Reset</button>
              </div>
            </div>
            <div class="prog-bg"><div id="progBar" class="prog-fg"></div></div>
            <div class="sub" id="subTxt">{cfg['sub']}</div>
          </div>

          <script>
            const mode = "{cfg['mode']}";
            const initialSeconds = {cfg['seconds']};
            let currentSeconds = initialSeconds;
            let running = true;

            function fmt(sec) {{
              const m = Math.floor(Math.abs(sec) / 60);
              const s = Math.abs(sec) % 60;
              return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
            }}

            function render() {{
              const clockEl = document.getElementById('clock');
              const progEl = document.getElementById('progBar');
              if (mode === 'zen') {{
                const mins = Math.floor(currentSeconds / 60);
                clockEl.innerHTML = running ? '<i>Breathing in flow…</i>' : '<i>Paused (' + mins + 'm)</i>';
                progEl.style.width = ((currentSeconds % 60) / 60 * 100) + '%';
              }} else if (mode === 'up') {{
                clockEl.textContent = fmt(currentSeconds);
                const pct = Math.min(100, (currentSeconds / ({max(est_minutes, 5)} * 60)) * 100);
                progEl.style.width = pct + '%';
              }} else {{
                clockEl.textContent = fmt(currentSeconds);
                const pct = initialSeconds > 0 ? ((initialSeconds - currentSeconds) / initialSeconds) * 100 : 100;
                progEl.style.width = Math.min(100, Math.max(0, pct)) + '%';
              }}
            }}

            function tick() {{
              if (!running) return;
              if (mode === 'up' || mode === 'zen') {{
                currentSeconds++;
              }} else {{
                if (currentSeconds > 0) {{
                  currentSeconds--;
                }} else {{
                  running = false;
                  document.getElementById('stateTxt').textContent = 'Sprint Done!';
                  document.getElementById('toggleBtn').textContent = 'Keep Going (+2m)';
                  document.getElementById('subTxt').textContent = 'Nice work! Keep riding the momentum or take a break.';
                }}
              }}
              render();
            }}

            function toggleTimer() {{
              if (!running && mode === 'down' && currentSeconds === 0) {{
                currentSeconds = 120;
                running = true;
                document.getElementById('toggleBtn').textContent = 'Pause';
                document.getElementById('stateTxt').textContent = 'In Flow';
                render();
                return;
              }}
              running = !running;
              document.getElementById('toggleBtn').textContent = running ? 'Pause' : 'Resume';
              document.getElementById('stateTxt').textContent = running ? 'In Flow' : 'Paused';
              render();
            }}

            function resetTimer() {{
              currentSeconds = initialSeconds;
              running = true;
              document.getElementById('toggleBtn').textContent = 'Pause';
              document.getElementById('stateTxt').textContent = 'In Flow';
              render();
            }}

            render();
            setInterval(tick, 1000);
          </script>
        </body>
        </html>
        """,
        height=158,
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
        d_brief = st.session_state.get("draft_brief_text") or "Compare Approach A and Approach B using 3–5 sources."
        seeded = decompose_assignment(d_title, d_brief, "Coursework", "Friday")
        seeded["original_brief"] = d_brief
        seeded["current_step_idx"] = 0
        seeded["status"] = "active"
        tid = save_user_task(uid, seeded)
        st.session_state["current_task_id"] = tid
        all_tasks = get_user_tasks(uid)

    task_map = {t["id"]: t for t in all_tasks if t.get("id")}
    task_id = st.session_state.get("current_task_id")
    if task_id and task_id in task_map:
        task = task_map[task_id]
    else:
        task = get_latest_resumable_task(uid) or all_tasks[0]
        st.session_state["current_task_id"] = task["id"]

    # Interactive 4-Step Journey Bar at the top
    render_assignment_journey_bar("workspace")

    steps = task.get("steps", [])
    cur_idx = min(task.get("current_step_idx", 0), max(0, len(steps) - 1))
    cur_step = steps[cur_idx] if steps else {}
    phase_name = cur_step.get("phase") or f"Step {cur_idx + 1}"

    session_mode = st.session_state.get("session_mode", "workspace")

    # =========================================================================
    # VIEW 1: START MODE (Calm Centered Focus Card)
    # =========================================================================
    if session_mode == "start_mode":
        use_smaller = st.session_state.get(f"shrunk_step_{task['id']}_{cur_idx}", False)
        action_text = (
            cur_step.get("two_minute_version", "Open Google Scholar and search your topic keywords.")
            if use_smaller
            else cur_step.get("first_action", "Find one paper comparing Approach A and B.")
        )

        html(f"""
<div style="max-width: 640px; margin: 1.4rem auto 1.2rem auto;">
  <div style="background:#ffffff; border-radius:28px; padding:2.4rem 2.2rem; border:1.5px solid #f2e2dc; box-shadow:0 16px 40px rgba(160,40,50,0.06); text-align:center;">
    <span style="background:#fff1f2; color:#d7262b; font-size:0.72rem; font-weight:700; padding:5px 14px; border-radius:99px; letter-spacing:0.1em; text-transform:uppercase;">
      {task.get('title')} · STEP {cur_idx + 1} OF {len(steps)} · {phase_name}
    </span>
    <div class="rs-serif" style="font-size: 2.35rem; color: #2a1714; margin: 1rem 0 0.8rem 0; line-height:1.12;">
      {action_text}
    </div>
    <div style="font-size:0.94rem; color:#6b524c;">
      {cur_step.get('why_it_matters', 'Complete just this single concrete action to build momentum.')}
    </div>
  </div>
</div>
""")

        _, c1, c2, c3, _ = st.columns([0.8, 1.5, 1.3, 1.2, 0.8])
        with c1:
            if st.button("Open Workspace →", type="primary", use_container_width=True):
                st.session_state["session_mode"] = "workspace"
                st.rerun()
        with c2:
            if st.button("Shrink Step (2m)", use_container_width=True):
                st.session_state[f"shrunk_step_{task['id']}_{cur_idx}"] = True
                st.rerun()
        with c3:
            if st.button("Learn Concepts", use_container_width=True):
                nav_to("resources")
        return

    # =========================================================================
    # VIEW 2: PAUSE & SAVE SNAPSHOT (Instant, Responsive Cognitive Snapshot)
    # =========================================================================
    if session_mode == "pause_modal":
        html(f"""
<div style="margin-bottom: 0.9rem;">
  <span class="rs-subhead">SAVE COGNITIVE SNAPSHOT · {task.get('title', '').upper()}</span>
  <div class="page-title" style="margin:0;">Save Where You <i>Stopped</i></div>
</div>
""")

        prep_key = f"prepared_pause_context_{task['id']}"
        if prep_key not in st.session_state:
            st.session_state[prep_key] = _build_instant_snapshot(task, task.get("notes", ""))

        prep = st.session_state[prep_key]
        comp_default = ", ".join(prep.get("completed", [])) if isinstance(prep.get("completed"), list) else str(prep.get("completed", ""))

        c_p1, c_p2 = st.columns(2, gap="medium")
        with c_p1:
            f_working = st.text_input("1 · What you were working on", value=prep.get("working_on", cur_step.get("title", "")))
            f_completed = st.text_input("2 · What you completed (comma-separated)", value=comp_default)
            f_tried = st.text_input("3 · What you tried / drafted", value=prep.get("tried", ""))
        with c_p2:
            f_stuck = st.text_input("4 · Where you paused or got stuck", value=prep.get("stuck_on", ""))
            f_thought = st.text_input("5 · Your last thought / note", value=prep.get("last_thought", ""))
            f_next = st.text_input("6 · Next concrete action when you return", value=prep.get("next_step", cur_step.get("first_action", "")))

        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        c_save, c_ai, c_back, _ = st.columns([1.6, 1.3, 1.2, 1.2], gap="small")
        with c_save:
            if st.button("✓ Save Snapshot →", type="primary", use_container_width=True):
                snapshot = {
                    "working_on": f_working.strip() or f"{phase_name} — {cur_step.get('title', '')}",
                    "completed": [x.strip() for x in f_completed.split(",") if x.strip()] or [f"Started {phase_name}"],
                    "tried": f_tried.strip() or "Drafted workspace notes",
                    "stuck_on": f_stuck.strip() or "Paused mid-step",
                    "last_thought": f_thought.strip() or task.get("simplified_brief", ""),
                    "next_step": f_next.strip() or cur_step.get("first_action", ""),
                    "force_new_entry": True,
                }
                save_context_restore(uid, task["id"], snapshot)
                st.session_state.pop(prep_key, None)
                st.session_state["session_mode"] = "workspace"
                st.session_state["interrupted_task_id"] = task["id"]
                st.session_state["snapshot_saved_banner"] = True
                nav_to("context_restore")
        with c_ai:
            if st.button("✨ Auto-Fill with AI", use_container_width=True):
                with st.spinner("Reading your notes to summarize your state..."):
                    completed_steps = [s.get("title") for s in steps if s.get("completed")]
                    st.session_state[prep_key] = generate_context_summary(task, completed_steps, task.get("notes", ""))
                st.rerun()
        with c_back:
            if st.button("← Back to Work", use_container_width=True):
                st.session_state.pop(prep_key, None)
                st.session_state["session_mode"] = "workspace"
                st.rerun()
        return

    # =========================================================================
    # VIEW 3: ACTIVE WORKSPACE (With Inline Assignment Switcher & Step Bar)
    # =========================================================================
    c_top_l, c_top_sw, c_top_snap = st.columns([2.7, 1.5, 1.15], gap="medium")
    with c_top_l:
        html(f"""
<div style="margin-bottom:0.4rem;">
  <span class="rs-subhead">{task.get('title')} · STEP {cur_idx + 1} OF {len(steps)} ({phase_name.upper()})</span>
  <div class="page-title" style="margin:0; font-size:2.2rem;">{cur_step.get('title')}</div>
</div>
""")
    with c_top_sw:
        tid_list = list(task_map.keys())
        picked_ws_tid = st.selectbox(
            "Working on Assignment:",
            options=tid_list,
            format_func=lambda tid: task_map[tid].get("title", "Assignment"),
            index=tid_list.index(task["id"]) if task["id"] in tid_list else 0,
            key="ws_header_assignment_picker",
        )
        if picked_ws_tid != task["id"]:
            st.session_state["current_task_id"] = picked_ws_tid
            st.session_state["interrupted_task_id"] = picked_ws_tid
            st.session_state["decomposed_task"] = task_map[picked_ws_tid]
            save_active_auth_session(uid, st.session_state.get("user_name", "Student"), True, picked_ws_tid)
            st.rerun()
    with c_top_snap:
        st.markdown("<div style='height:1.65rem;'></div>", unsafe_allow_html=True)
        if st.button("📸 Save Snapshot", use_container_width=True, key="ws_top_quick_snap"):
            snap = _build_instant_snapshot(task, task.get("notes", ""))
            snap["force_new_entry"] = True
            save_context_restore(uid, task["id"], snap)
            st.toast(f"Snapshot saved for {task.get('title')}!", icon="✅")

    col_main, col_side = st.columns([2.15, 1.05], gap="large")

    with col_main:
        subtasks = cur_step.get("subtasks", [])
        html(f"""
<div style="background:#fff5f6; border:1.5px solid #fecdd3; border-radius:20px; padding:0.95rem 1.25rem; margin-bottom:0.7rem;">
  <div class="rs-subhead" style="font-size:0.63rem;">STEP {cur_idx + 1} FIRST ACTION</div>
  <div style="font-size:0.98rem; font-weight:700; color:#881337; margin-top:2px;">
    {cur_step.get('first_action')}
  </div>
</div>
""")
        if subtasks:
            html("<div class='rs-subhead' style='font-size:0.63rem; color:#785a54; margin-bottom:0.25rem;'>STEP CHECKLIST</div>")
            checked_map = cur_step.setdefault("subtask_checks", {})
            for s_idx, sub_item in enumerate(subtasks):
                k = str(s_idx)
                val = st.checkbox(sub_item, value=bool(checked_map.get(k, False)), key=f"ws_subchk_{task['id']}_{cur_idx}_{s_idx}")
                if val != bool(checked_map.get(k, False)):
                    checked_map[k] = val
                    save_user_task(uid, task)
                    auto_snap = _build_instant_snapshot(task, task.get("notes", ""))
                    save_context_restore(uid, task["id"], auto_snap)

        notes_key = f"workspace_notes_{task['id']}"
        notes_val = st.text_area(
            "Workspace Draft & Notes",
            value=task.get("notes", ""),
            height=255,
            key=notes_key,
            label_visibility="collapsed",
            placeholder=f"Write your notes, outline, or draft for '{task.get('title')}' here...",
        )
        word_cnt = len([w for w in (notes_val or "").split() if w.strip()])
        last_saved_lbl = task.get("context_restore", {}).get("display_time", "Auto-synced")
        html(f"""
<div style="display:flex; justify-content:space-between; align-items:center; font-size:0.78rem; color:#6b524c; margin:-4px 0 10px 4px;">
  <span>✓ Auto-synced to Context Snapshot ({last_saved_lbl})</span>
  <span><b>{word_cnt}</b> words drafted</span>
</div>
""")
        if notes_val != task.get("notes", ""):
            task["notes"] = notes_val
            save_user_task(uid, task)
            auto_snap = _build_instant_snapshot(task, notes_val)
            save_context_restore(uid, task["id"], auto_snap)

        b_done, b_save = st.columns([1.5, 1.3], gap="small")
        with b_done:
            if st.button("✓ Complete Step & Next →", type="primary", use_container_width=True):
                steps[cur_idx]["completed"] = True
                if cur_idx + 1 < len(steps):
                    task["current_step_idx"] = cur_idx + 1
                else:
                    task["status"] = "completed"
                save_user_task(uid, task)
                auto_snap = _build_instant_snapshot(task, notes_val)
                auto_snap["force_new_entry"] = True
                save_context_restore(uid, task["id"], auto_snap)
                log_task_metric(uid, "steps_completed", 1)
                st.rerun()
        with b_save:
            if st.button("Pause & Review Snapshot", use_container_width=True):
                st.session_state.pop(f"prepared_pause_context_{task['id']}", None)
                st.session_state["session_mode"] = "pause_modal"
                st.rerun()

    with col_side:
        # Pastel Bento Card 0: Multi-Style Focus Timer
        timer_style = st.selectbox(
            "Timer Style",
            [
                "Flow Count-Up",
                "2-Min Micro-Sprint",
                "15-Min Gentle Sprint",
                "25-Min Classic Focus",
                "Step Estimate",
                "Zen (Hide Numbers)",
            ],
            index=0,
            key="ws_timer_style_select",
        )
        _render_live_timer_widget(timer_style, int(cur_step.get("est_minutes", 20)))

        # Pastel Bento Card 1: AI Unblocker
        html("""
<div style="background:#f3e8ff; border-radius:22px; padding:1rem 1.25rem; margin-bottom:0.5rem;">
  <div class="rs-subhead" style="color:#6d28d9; font-size:0.63rem;">AI UNBLOCKER</div>
  <div class="rs-serif" style="font-size:1.35rem; color:#2a1714; margin-top:2px;">Feeling stuck?</div>
</div>
""")
        if st.button("Give Starter Template", use_container_width=True):
            completed_names = [s.get("title") for s in steps if s.get("completed")]
            st.session_state["companion_response"] = get_stuck_support(
                task_title=task.get("title", ""),
                current_step_title=cur_step.get("title", ""),
                obstacle="Make this simpler",
                context={"completed_steps": completed_names, "notes": notes_val},
            )

        comp_resp = st.session_state.get("companion_response")
        if comp_resp:
            html(f"""
<div style="background:#ffffff; border:1.5px solid #e9d5ff; border-radius:16px; padding:0.85rem 1rem; margin:0.45rem 0; font-size:0.84rem; color:#2a1714;">
  <b>2-min tip:</b> {comp_resp.get('micro_action', '')}
</div>
""")
            if st.button("Insert Into Notes", type="primary", use_container_width=True):
                tpl = comp_resp.get("example_or_structure", "")
                task["notes"] = (task.get("notes", "") + "\n\n" + tpl).strip()
                save_user_task(uid, task)
                st.session_state.pop("companion_response", None)
                st.rerun()

        # Pastel Bento Card 2: Compact Step Switcher + Edit Study Plan Button
        html("<div class='rs-subhead' style='margin:0.95rem 0 0.4rem 0; color:#785a54; font-size:0.64rem;'>STUDY PLAN STEPS</div>")
        for i, s in enumerate(steps):
            is_cur = i == cur_idx
            is_done = bool(s.get("completed", False))
            label = f"{'✓' if is_done else f'{i+1}.'} {s.get('phase', 'Stage')}"
            if st.button(label, key=f"side_st_{i}", type="primary" if is_cur else "secondary", use_container_width=True):
                task["current_step_idx"] = i
                save_user_task(uid, task)
                st.rerun()

        if st.button("✎ Edit Study Plan", key="ws_edit_plan_btn", use_container_width=True):
            st.session_state["decomposed_task"] = task
            st.session_state["plan_edit_mode"] = True
            nav_to("study_plan")
