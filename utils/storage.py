import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
LIBRARY_FILE = DATA_DIR / "library.json"


# ---------- helpers ----------

def _read(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _write(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- user / profile ----------

def generate_user_id() -> str:
    return "u_" + uuid.uuid4().hex[:8].upper()


def list_users() -> dict:
    return _read(USERS_FILE)


def user_exists(name: str) -> Optional[str]:
    """Return user_id if a user with this name already exists, else None."""
    users = list_users()
    for uid, data in users.items():
        if data.get("name", "").lower() == name.lower():
            return uid
    return None


def create_user(name: str) -> str:
    clean_name = name.strip()
    existing_uid = user_exists(clean_name)
    if existing_uid:
        return existing_uid
    users = _read(USERS_FILE)
    uid = generate_user_id()
    users[uid] = {
        "name": clean_name,
        "created_at": datetime.now().isoformat(),
        "profile": {},
    }
    _write(USERS_FILE, users)
    return uid


def load_user(user_id: str) -> Optional[dict]:
    users = _read(USERS_FILE)
    return users.get(user_id)


def save_profile(user_id: str, profile: dict):
    users = _read(USERS_FILE)
    if user_id not in users:
        return
    users[user_id]["profile"] = profile
    users[user_id]["profile_complete"] = True
    _write(USERS_FILE, users)


def get_profile(user_id: str) -> dict:
    user = load_user(user_id)
    if user:
        return user.get("profile", {})
    return {}


def mark_popup_shown(user_id: str):
    users = _read(USERS_FILE)
    if user_id in users:
        users[user_id]["popup_shown"] = True
        _write(USERS_FILE, users)


def is_popup_shown(user_id: str) -> bool:
    user = load_user(user_id)
    return user.get("popup_shown", False) if user else False


def save_quiz_feedback(
    user_id: str,
    subject: str,
    unit: str,
    score_correct: int,
    score_total: int,
    by_subtopic: dict[str, dict[str, int]],
) -> None:
    users = _read(USERS_FILE)
    if user_id not in users:
        return

    user = users[user_id]
    quiz_feedback = user.setdefault("quiz_feedback", {})
    subject_feedback = quiz_feedback.setdefault(
        subject,
        {"attempts": [], "weak_subtopics": {}},
    )

    subject_feedback["attempts"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "unit": unit,
            "score_correct": score_correct,
            "score_total": score_total,
            "subtopic_breakdown": by_subtopic,
        }
    )

    weak_map = subject_feedback.setdefault("weak_subtopics", {})
    for subtopic, stats in by_subtopic.items():
        total = int(stats.get("total", 0))
        correct = int(stats.get("correct", 0))
        missed = max(total - correct, 0)
        if missed <= 0:
            continue
        weak_map[subtopic] = int(weak_map.get(subtopic, 0)) + missed

    _write(USERS_FILE, users)


def get_quiz_history(user_id: str) -> list[dict]:
    """Return all quiz attempts across all subjects, sorted newest first."""
    user = load_user(user_id)
    if not user:
        return []
    quiz_feedback = user.get("quiz_feedback", {})
    all_attempts = []
    for subject, subject_data in quiz_feedback.items():
        for attempt in subject_data.get("attempts", []):
            all_attempts.append({
                "subject": subject,
                "unit": attempt.get("unit", ""),
                "timestamp": attempt.get("timestamp", ""),
                "score_correct": attempt.get("score_correct", 0),
                "score_total": attempt.get("score_total", 0),
                "subtopic_breakdown": attempt.get("subtopic_breakdown", {}),
            })
    all_attempts.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_attempts


def get_overall_stats(user_id: str) -> dict:
    """Return aggregated stats across all quiz attempts."""
    history = get_quiz_history(user_id)
    if not history:
        return {"total_quizzes": 0, "total_questions": 0, "total_correct": 0, "avg_score": 0, "subjects_practiced": 0}
    total_q = sum(a["score_total"] for a in history)
    total_c = sum(a["score_correct"] for a in history)
    subjects = set(a["subject"] for a in history)
    return {
        "total_quizzes": len(history),
        "total_questions": total_q,
        "total_correct": total_c,
        "avg_score": round(100 * total_c / total_q) if total_q else 0,
        "subjects_practiced": len(subjects),
    }


def get_weak_subtopics(user_id: str, subject: str, limit: int = 4) -> list[str]:
    user = load_user(user_id)
    if not user:
        return []
    weak_map = (
        user.get("quiz_feedback", {})
        .get(subject, {})
        .get("weak_subtopics", {})
    )
    if not isinstance(weak_map, dict) or not weak_map:
        return []
    ranked = sorted(
        weak_map.items(),
        key=lambda x: (-int(x[1]), str(x[0]).lower()),
    )
    return [str(name) for name, _ in ranked[:limit]]


# ---------- library (subjects / units / pdfs) ----------

def _lib() -> dict:
    return _read(LIBRARY_FILE)


def _save_lib(data: dict):
    _write(LIBRARY_FILE, data)


def get_user_library(user_id: str) -> dict:
    lib = _lib()
    return lib.get(user_id, {})


def create_subject(user_id: str, subject_name: str) -> bool:
    """Returns False if already exists."""
    lib = _lib()
    user_lib = lib.setdefault(user_id, {})
    key = subject_name.strip()
    if key in user_lib:
        return False
    user_lib[key] = {"units": {}, "created_at": datetime.now().isoformat()}
    _save_lib(lib)
    return True


def create_unit(user_id: str, subject: str, unit_name: str) -> bool:
    lib = _lib()
    user_lib = lib.get(user_id, {})
    if subject not in user_lib:
        return False
    units = user_lib[subject].setdefault("units", {})
    if unit_name in units:
        return False
    units[unit_name] = {
        "pdfs": [],
        "texts": [],
        "created_at": datetime.now().isoformat(),
        # SM-2 Spaced Repetition Fields
        "repetition": 0,
        "interval": 0,
        "ease": 2.5,
        "next_review_date": datetime.now().isoformat(),
    }
    _save_lib(lib)
    return True


def update_unit_repetition(user_id: str, subject: str, unit: str, quality: int):
    """
    Update SM-2 algorithm variables for a unit based on review quality (0-5).
    0 = Blank, 3 = Hard, 4 = Good, 5 = Perfect.
    """
    from datetime import timedelta
    lib = _lib()
    user_lib = lib.get(user_id, {})
    unit_data = user_lib.get(subject, {}).get("units", {}).get(unit)
    
    if not unit_data:
        return

    rep = unit_data.get("repetition", 0)
    interval = unit_data.get("interval", 0)
    ease = unit_data.get("ease", 2.5)

    if quality >= 3:
        if rep == 0:
            interval = 1
        elif rep == 1:
            interval = 6
        else:
            interval = int(round(interval * ease))
        rep += 1
    else:
        rep = 0
        interval = 1

    ease = ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ease = max(1.3, ease)

    next_review = datetime.now() + timedelta(days=interval)

    unit_data["repetition"] = rep
    unit_data["interval"] = interval
    unit_data["ease"] = ease
    unit_data["next_review_date"] = next_review.isoformat()

    _save_lib(lib)


def get_revision_schedule(user_id: str) -> dict:
    """Returns a dict with 'due' and 'upcoming' review units, sorted by date."""
    lib = _lib()
    user_lib = lib.get(user_id, {})
    due_units = []
    upcoming_units = []
    now = datetime.now()

    for subject_name, subj_data in user_lib.items():
        for unit_name, unit_data in subj_data.get("units", {}).items():
            next_review_str = unit_data.get("next_review_date")
            if not next_review_str:
                unit_data["next_review_date"] = now.isoformat()
                next_review_str = unit_data["next_review_date"]
                _save_lib(lib)

            next_review = datetime.fromisoformat(next_review_str)
            item = {
                "subject": subject_name,
                "unit": unit_name,
                "interval": unit_data.get("interval", 0),
                "repetition": unit_data.get("repetition", 0),
                "date": next_review
            }
            if next_review <= now:
                due_units.append(item)
            else:
                upcoming_units.append(item)

    upcoming_units.sort(key=lambda x: x["date"])
    return {"due": due_units, "upcoming": upcoming_units}


def get_full_study_plan(user_id: str, days_ahead: int = 30) -> list:
    """
    Returns a comprehensive day-by-day study plan, including projected future SM-2 reviews.
    """
    from datetime import timedelta, date as _date
    from collections import defaultdict

    lib = _lib()
    user_lib = lib.get(user_id, {})
    now = datetime.now()
    today = _date.today()
    plan = []

    # Slot counter to spread 'due' chapters
    slots: dict = defaultdict(int)
    MAX_INITIAL_PER_DAY = 3

    # All units in library
    units_to_schedule = []
    for subj_name, subj_data in user_lib.items():
        for unit_name, unit_data in subj_data.get("units", {}).items():
            units_to_schedule.append({
                "subject": subj_name,
                "unit": unit_name,
                "data": unit_data
            })

    for item in units_to_schedule:
        u_data = item["data"]
        subj = item["subject"]
        unit = item["unit"]

        # Current state
        rep = u_data.get("repetition", 0)
        interval = u_data.get("interval", 0)
        ease = u_data.get("ease", 2.5)
        next_review_str = u_data.get("next_review_date")

        if next_review_str:
            next_date = datetime.fromisoformat(next_review_str).date()
        else:
            next_date = today

        # 1. Schedule the IMMEDIATE next session
        if next_date <= today:
            status = "due"
            # Spread 'due' items so we don't overwhelm day 1
            entry_date = today
            while slots[entry_date] >= MAX_INITIAL_PER_DAY:
                entry_date += timedelta(days=1)
            plan.append({"date": entry_date, "subject": subj, "unit": unit, "status": "due" if entry_date == today else "suggested"})
            slots[entry_date] += 1
            current_date = entry_date
        else:
            plan.append({"date": next_date, "subject": subj, "unit": unit, "status": "scheduled"})
            slots[next_date] += 1
            current_date = next_date

        # 2. Project 4 FUTURE sessions (assuming 'Good' (4) reviews)
        proj_rep = rep + 1
        proj_interval = interval
        proj_ease = ease
        proj_date = current_date

        for _ in range(4):
            # SM-2 Projection logic (assuming quality=4)
            if proj_rep == 1:
                proj_interval = 1
            elif proj_rep == 2:
                proj_interval = 6
            else:
                proj_interval = int(round(proj_interval * proj_ease))

            proj_rep += 1
            # Ease adjustment for quality 4
            proj_ease = proj_ease + (0.1 - (5 - 4) * (0.08 + (5 - 4) * 0.02))
            proj_ease = max(1.3, proj_ease)

            proj_date += timedelta(days=max(1, proj_interval))

            if (proj_date - today).days > days_ahead:
                break

            plan.append({
                "date": proj_date,
                "subject": subj,
                "unit": unit,
                "status": "projected"
            })

    plan.sort(key=lambda x: (x["date"], x["subject"], x["unit"]))
    return plan



def save_pdf_to_unit(user_id: str, subject: str, unit: str, filename: str, pdf_bytes: bytes) -> str:
    """Saves PDF to disk and records it. Returns the saved file path."""
    unit_dir = DATA_DIR / "uploads" / user_id / subject / unit
    unit_dir.mkdir(parents=True, exist_ok=True)

    # avoid name collisions
    stem = Path(filename).stem
    suffix = Path(filename).suffix or ".pdf"
    safe_name = f"{stem}_{uuid.uuid4().hex[:6]}{suffix}"
    dest = unit_dir / safe_name
    dest.write_bytes(pdf_bytes)

    lib = _lib()
    user_lib = lib.setdefault(user_id, {})
    subject_data = user_lib.setdefault(subject, {"units": {}, "created_at": datetime.now().isoformat()})
    unit_data = subject_data["units"].setdefault(unit, {"pdfs": [], "created_at": datetime.now().isoformat()})
    unit_data["pdfs"].append({
        "original_name": filename,
        "saved_name": safe_name,
        "path": str(dest),
        "uploaded_at": datetime.now().isoformat(),
    })
    _save_lib(lib)
    return str(dest)


def save_text_to_unit(user_id: str, subject: str, unit: str, title: str, content: str):
    lib = _lib()
    user_lib = lib.setdefault(user_id, {})
    subject_data = user_lib.setdefault(subject, {"units": {}, "created_at": datetime.now().isoformat()})
    unit_data = subject_data["units"].setdefault(unit, {"pdfs": [], "texts": [], "created_at": datetime.now().isoformat()})
    
    if "texts" not in unit_data:
        unit_data["texts"] = []
        
    unit_data["texts"].append({
        "title": title,
        "content": content,
        "added_at": datetime.now().isoformat(),
        "id": uuid.uuid4().hex[:8]
    })
    _save_lib(lib)


def delete_text(user_id: str, subject: str, unit: str, text_id: str):
    lib = _lib()
    texts = lib.get(user_id, {}).get(subject, {}).get("units", {}).get(unit, {}).get("texts", [])
    updated = [t for t in texts if t.get("id") != text_id]
    lib[user_id][subject]["units"][unit]["texts"] = updated
    _save_lib(lib)


def delete_subject(user_id: str, subject: str):
    lib = _lib()
    lib.get(user_id, {}).pop(subject, None)
    _save_lib(lib)


def delete_unit(user_id: str, subject: str, unit: str):
    lib = _lib()
    lib.get(user_id, {}).get(subject, {}).get("units", {}).pop(unit, None)
    _save_lib(lib)


def _resolve_pdf_path(stored_path: str, saved_name: str) -> Optional[Path]:
    """Resolve a stored PDF path. Falls back to searching under DATA_DIR if the
    stored absolute path no longer exists (e.g. moved to a different machine)."""
    p = Path(stored_path)
    if p.exists():
        return p
    # Search for the saved filename anywhere under DATA_DIR/uploads
    matches = list(DATA_DIR.rglob(saved_name))
    if matches:
        return matches[0]
    return None


def get_unit_pdf_paths(user_id: str, subject: str, unit: str) -> list[Path]:
    """Absolute paths to PDF files for a unit (for text extraction)."""
    unit_data = (
        get_user_library(user_id)
        .get(subject, {})
        .get("units", {})
        .get(unit, {})
    )
    pdfs = unit_data.get("pdfs", [])
    out: list[Path] = []
    for p in pdfs:
        resolved = _resolve_pdf_path(p.get("path", ""), p.get("saved_name", ""))
        if resolved:
            out.append(resolved)
    return out


def get_subject_pdf_paths(user_id: str, subject: str) -> list[Path]:
    """Absolute paths to all PDFs across all units in a subject."""
    units = get_user_library(user_id).get(subject, {}).get("units", {})
    out: list[Path] = []
    for unit_data in units.values():
        for p in unit_data.get("pdfs", []):
            resolved = _resolve_pdf_path(p.get("path", ""), p.get("saved_name", ""))
            if resolved:
                out.append(resolved)
    return out


def delete_pdf(user_id: str, subject: str, unit: str, saved_name: str):
    lib = _lib()
    pdfs = lib.get(user_id, {}).get(subject, {}).get("units", {}).get(unit, {}).get("pdfs", [])
    updated = [p for p in pdfs if p["saved_name"] != saved_name]
    lib[user_id][subject]["units"][unit]["pdfs"] = updated
    _save_lib(lib)
    # also remove file
    for entry in pdfs:
        if entry["saved_name"] == saved_name:
            try:
                Path(entry["path"]).unlink(missing_ok=True)
            except Exception:
                pass
def build_profile_summary(user_id: str) -> str:
    profile = get_profile(user_id)
    if not profile:
        return "Student profile not available."
    interests = ", ".join(profile.get("interests") or [])
    return (
        f"Student profile: Age {profile.get('age', 'unknown')}, "
        f"{profile.get('grade', 'unknown grade')}, "
        f"learning style: {profile.get('learning_style', 'unknown')}, "
        f"interests: {interests or 'not specified'}, "
        f"goal: {profile.get('goal', 'not specified')}."
    )
# ===========================================================================
# RESTART: ADHD Tasks, Context Restore, and Executive Analytics
# ===========================================================================

TASKS_FILE = DATA_DIR / "tasks.json"
ACTIVE_SESSION_FILE = DATA_DIR / "active_session.json"


def save_active_auth_session(
    user_id: Optional[str],
    user_name: Optional[str] = None,
    profile_complete: bool = True,
    current_task_id: Optional[str] = None,
):
    if not user_id:
        _write(ACTIVE_SESSION_FILE, {})
        return
    cur = _read(ACTIVE_SESSION_FILE)
    data = {
        "user_id": user_id,
        "user_name": user_name or cur.get("user_name", "Student"),
        "profile_complete": profile_complete,
        "current_task_id": current_task_id or cur.get("current_task_id"),
        "updated_at": datetime.now().isoformat(),
    }
    _write(ACTIVE_SESSION_FILE, data)


def load_active_auth_session() -> dict:
    return _read(ACTIVE_SESSION_FILE)


def clear_active_auth_session():
    _write(ACTIVE_SESSION_FILE, {})

def _read_tasks() -> dict:
    return _read(TASKS_FILE)

def _save_tasks(data: dict):
    _write(TASKS_FILE, data)

def get_user_tasks(user_id: str) -> list[dict]:
    all_tasks = _read_tasks()
    user_task_dict = all_tasks.get(user_id, {})
    if not user_task_dict:
        return []
    # Deduplicate by normalized title, keeping the most recently active version
    ordered = sorted(
        user_task_dict.values(),
        key=lambda t: t.get("last_active", t.get("created_at", "")),
        reverse=True,
    )
    seen_titles = set()
    deduped = []
    removed_ids = []
    for t in ordered:
        norm_title = (t.get("title") or "").strip().lower()
        if norm_title and norm_title in seen_titles:
            if t.get("id"):
                removed_ids.append(t["id"])
            continue
        seen_titles.add(norm_title)
        deduped.append(t)
    if removed_ids:
        for rid in removed_ids:
            all_tasks[user_id].pop(rid, None)
        _save_tasks(all_tasks)
    return deduped


def get_task_by_id(user_id: str, task_id: str) -> Optional[dict]:
    all_tasks = _read_tasks()
    return all_tasks.get(user_id, {}).get(task_id)


def save_user_task(user_id: str, task: dict):
    all_tasks = _read_tasks()
    if user_id not in all_tasks:
        all_tasks[user_id] = {}
    norm_title = (task.get("title") or "").strip().lower()
    if "id" not in task and norm_title:
        for existing_id, existing_task in all_tasks[user_id].items():
            if (existing_task.get("title") or "").strip().lower() == norm_title:
                task["id"] = existing_id
                break
    if "id" not in task:
        task["id"] = "t_" + uuid.uuid4().hex[:8]
    if "created_at" not in task:
        task["created_at"] = datetime.now().isoformat()
    task["last_active"] = datetime.now().isoformat()
    all_tasks[user_id][task["id"]] = task
    _save_tasks(all_tasks)
    return task["id"]

def update_task_progress(user_id: str, task_id: str, step_index: int, status: str = "active"):
    task = get_task_by_id(user_id, task_id)
    if not task:
        return
    task["current_step_idx"] = step_index
    task["status"] = status
    task["last_active"] = datetime.now().isoformat()
    save_user_task(user_id, task)

def save_context_restore(user_id: str, task_id: str, context_data: dict):
    """Save cognitive state (what I was doing, tried, stuck on, next action) and append to context_history."""
    task = get_task_by_id(user_id, task_id)
    if not task:
        return
    now = datetime.now()
    context_data["saved_at"] = now.isoformat()
    context_data["display_time"] = now.strftime("%a %b %d · %I:%M:%S %p")
    task["context_restore"] = dict(context_data)
    history = task.setdefault("context_history", [])
    # If the very latest snapshot is from the exact same second and same text, update it; otherwise insert a new entry
    if history and history[0].get("working_on") == context_data.get("working_on") and history[0].get("tried") == context_data.get("tried") and history[0].get("stuck_on") == context_data.get("stuck_on") and history[0].get("next_step") == context_data.get("next_step") and not context_data.get("force_new_entry"):
        history[0] = dict(context_data)
    else:
        context_data.pop("force_new_entry", None)
        history.insert(0, dict(context_data))
    task["context_history"] = history[:25]
    task["last_active"] = now.isoformat()
    save_user_task(user_id, task)


def export_frontend_state(user_id: Optional[str] = None) -> dict:
    """Builds a self-contained JSON payload of accounts, active session, and tasks for browser localStorage persistence."""
    users = _read(USERS_FILE)
    tasks = _read_tasks()
    active = load_active_auth_session()
    return {
        "active_session": active,
        "users": users,
        "user_tasks": tasks.get(user_id, {}) if user_id else tasks,
        "synced_at": datetime.now().isoformat(),
    }


def import_frontend_account_bundle(bundle: dict) -> Optional[str]:
    """Restores an account + tasks bundle from browser localStorage or JSON backup."""
    if not isinstance(bundle, dict):
        return None
    users = _read(USERS_FILE)
    all_tasks = _read_tasks()
    for uid, udata in (bundle.get("users") or {}).items():
        if uid not in users and isinstance(udata, dict):
            users[uid] = udata
    _write(USERS_FILE, users)
    user_tasks = bundle.get("user_tasks") or {}
    active_uid = (bundle.get("active_session") or {}).get("user_id")
    if active_uid and isinstance(user_tasks, dict):
        dest = all_tasks.setdefault(active_uid, {})
        for tid, tdata in user_tasks.items():
            if isinstance(tdata, dict) and tid not in dest:
                dest[tid] = tdata
        _save_tasks(all_tasks)
    return active_uid


def delete_user_task(user_id: str, task_id: str):
    all_tasks = _read_tasks()
    if user_id in all_tasks and task_id in all_tasks[user_id]:
        all_tasks[user_id].pop(task_id, None)
        _save_tasks(all_tasks)


def update_task_metadata(user_id: str, task_id: str, title: Optional[str] = None, due_date: Optional[str] = None, status: Optional[str] = None):
    task = get_task_by_id(user_id, task_id)
    if not task:
        return
    if title is not None and title.strip():
        task["title"] = title.strip()
    if due_date is not None:
        task["due_date"] = due_date.strip()
    if status is not None:
        task["status"] = status
    save_user_task(user_id, task)


def restore_context_from_history(user_id: str, task_id: str, history_idx: int):
    task = get_task_by_id(user_id, task_id)
    if not task:
        return
    history = task.get("context_history", [])
    if 0 <= history_idx < len(history):
        task["context_restore"] = dict(history[history_idx])
        save_user_task(user_id, task)

def get_latest_resumable_task(user_id: str) -> Optional[dict]:
    tasks = get_user_tasks(user_id)
    active = [t for t in tasks if t.get("status") in ("active", "paused", "in_progress")]
    if not active:
        return None
    active.sort(key=lambda t: t.get("last_active", t.get("created_at", "")), reverse=True)
    return active[0]

def log_task_metric(user_id: str, metric_name: str, value: Any = 1):
    users = _read(USERS_FILE)
    if user_id not in users:
        return
    metrics = users[user_id].setdefault("adhd_metrics", {
        "tasks_started": 0,
        "tasks_resumed": 0,
        "steps_completed": 0,
        "interrupted_sessions_resumed": 0,
        "first_action_times": [250, 180, 210]  # in seconds
    })
    if metric_name in metrics:
        if isinstance(metrics[metric_name], int):
            metrics[metric_name] += value
        elif isinstance(metrics[metric_name], list):
            metrics[metric_name].append(value)
    else:
        metrics[metric_name] = value
    _write(USERS_FILE, users)

def get_adhd_metrics(user_id: str) -> dict:
    users = _read(USERS_FILE)
    u = users.get(user_id, {})
    return u.get("adhd_metrics", {
        "tasks_started": 18,
        "tasks_resumed": 12,
        "steps_completed": 47,
        "interrupted_sessions_resumed": 9,
        "first_action_times": [240, 190, 215, 260]
    })
