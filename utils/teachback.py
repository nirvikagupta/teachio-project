from __future__ import annotations

from typing import Any, Optional

from utils.teaching_agents import extract_json_object, run_agent, study_prompt_prefix


def generate_teachback_round(
    *,
    teachback_agent: Any,
    subject: str,
    unit: str,
    material: str,
    focus_hint: str = "",
) -> Optional[dict]:
    prompt = (
        study_prompt_prefix(subject, unit, material)
        + (f"Focus hint: {focus_hint}\n\n" if focus_hint else "")
        + "TASK: GENERATE\n"
        + "Generate ONE teach-back round.\n"
        + "Return only the JSON object described in your instructions.\n"
    )
    out, err = run_agent(teachback_agent, prompt)
    if err or not out:
        return None
    data = extract_json_object(out.content or "")
    if not isinstance(data, dict):
        return None
    if not data.get("explanation") or not data.get("question") or not isinstance(data.get("key_ideas"), list):
        return None
    return data


def evaluate_teachback_answer(
    *,
    teachback_agent: Any,
    subject: str,
    unit: str,
    material: str,
    subtopic: str,
    question: str,
    key_ideas: list[str],
    student_answer: str,
) -> Optional[dict]:
    prompt = (
        study_prompt_prefix(subject, unit, material)
        + "TASK: EVALUATE\n"
        + f"Subtopic: {subtopic}\n"
        + f"Question: {question}\n"
        + "Key ideas (the rubric):\n"
        + "\n".join([f"- {k}" for k in key_ideas])
        + "\n\n"
        + "Student answer:\n"
        + "-----\n"
        + (student_answer or "")
        + "\n-----\n\n"
        + "Return only the JSON object described in your instructions.\n"
    )
    out, err = run_agent(teachback_agent, prompt)
    if err or not out:
        return None
    data = extract_json_object(out.content or "")
    if not isinstance(data, dict):
        return None
    if not data.get("score"):
        return None
    return data

