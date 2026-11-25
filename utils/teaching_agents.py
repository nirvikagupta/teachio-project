"""Groq + Agno agents for mnemonics, advisor, librarian, and quiz."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from agno.agent import Agent
from agno.models.groq import Groq
from agno.run.agent import RunOutput

try:
    from agno.tools.serpapi import SerpApiTools
except ImportError:  # pragma: no cover - needs google-search-results
    SerpApiTools = None  # type: ignore

try:
    from composio_phidata import Action, ComposioToolSet
except Exception:  # pragma: no cover - optional at import time
    Action = None  # type: ignore
    ComposioToolSet = None  # type: ignore

_DEFAULT_GROQ_MODEL = "llama-3.1-8b-instant"

# ---------------------------------------------------------------------------
# API keys — paste your keys between the quotes below (local use only).
# File: teachio-project/utils/teaching_agents.py
# ---------------------------------------------------------------------------
HARDCODED_GROQ_API_KEY = ""  # Set GROQ_API_KEY via environment / Streamlit secrets instead
# Optional: Google Docs for Academic Advisor / Research Librarian
HARDCODED_COMPOSIO_API_KEY = ""
# Optional: web search for Research Librarian (install: pip install google-search-results)
HARDCODED_SERPAPI_API_KEY = ""
# Optional: override Groq model id (leave "" for default below)
HARDCODED_GROQ_MODEL = "llama-3.1-8b-instant"
# ---------------------------------------------------------------------------

# Characters from PDFs included in each agent prompt. Groq on-demand tiers enforce
# low per-request token limits; large excerpts trigger "Request too large" / TPM errors.
# If you still hit limits, lower this (e.g. 2048) or upgrade your Groq plan.
STUDY_MATERIAL_MAX_CHARS = 4096


def load_api_keys() -> tuple[str, str, str]:
    return (
        HARDCODED_GROQ_API_KEY.strip(),
        HARDCODED_COMPOSIO_API_KEY.strip(),
        HARDCODED_SERPAPI_API_KEY.strip(),
    )


def groq_model_id() -> str:
    return HARDCODED_GROQ_MODEL.strip() or _DEFAULT_GROQ_MODEL


def extract_google_doc_url(text: str) -> Optional[str]:
    m = re.search(
        r"https://docs\.google\.com/document/d/[a-zA-Z0-9_-]+[^\s\)\]\"']*",
        text,
    )
    return m.group(0) if m else None


def extract_json_object(text: str) -> Optional[dict]:
    text = (text or "").strip()
    for pat in (
        r"```(?:json)?\s*(\{[\s\S]*?\})\s*```",
        r"(\{[\s\S]*\})",
    ):
        for m in re.finditer(pat, text):
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None


def llm_api_error_payload(text: str) -> Optional[dict]:
    data = extract_json_object(text)
    if not isinstance(data, dict):
        return None
    err = data.get("error")
    if isinstance(err, dict) and (err.get("code") or err.get("message")):
        return data
    return None


def run_agent(agent: Agent, prompt: str) -> tuple[Optional[RunOutput], Optional[str]]:
    out: RunOutput = agent.run(prompt)
    err = llm_api_error_payload(out.content)
    if err:
        code = err.get("error", {}).get("code", "?")
        msg = (err.get("error", {}) or {}).get("message", "Unknown error")
        return None, f"Model API error {code}: {msg}"
    return out, None


@dataclass
class TeachingStack:
    groq_key: str
    composio_key: str
    serp_key: str
    google_docs_tool: Optional[object]
    mnemonics_agent: Agent
    academic_advisor_agent: Agent
    research_librarian_agent: Agent
    quiz_agent: Agent
    teachback_agent: Agent
    mindmap_agent: Agent
    recap_agent: Agent
    assignment_advisor_agent: Agent


def _groq_model(api_key: str) -> Groq:
    return Groq(id=groq_model_id(), api_key=api_key)


def build_teaching_stack() -> Optional[TeachingStack]:
    groq_key, composio_key, serp_key = load_api_keys()
    if not groq_key:
        return None

    google_docs_tool = None
    if composio_key and ComposioToolSet and Action:
        try:
            composio_toolset = ComposioToolSet(api_key=composio_key)
            google_docs_tool = composio_toolset.get_tools(
                actions=[Action.GOOGLEDOCS_CREATE_DOCUMENT]
            )[0]
        except Exception:
            google_docs_tool = None

    model = _groq_model(groq_key)

    mnemonics_agent = Agent(
        name="Mnemonics",
        role="Memory and Mnemonics Specialist",
        model=model,
        tools=[],
        instructions=[
            "You are an expert Memory and Mnemonics Specialist. Your goal is to create highly effective, memorable, and creative mnemonics for the provided learning material.",
            "Use various techniques: Acronyms, Acrostics, catchy Rhymes, or vivid visual imagery.",
            "Make them catchy, slightly absurd, or funny, as these stick best in memory.",
            "For each mnemonic, clearly explain how it maps to the core concepts.",
            "Focus on the top ~8 most important concepts from the material.",
            "Output strictly in Markdown. Use bold headings and bullet points for readability. Do not include introductory/concluding fluff.",
        ],
        debug_mode=False,
        markdown=True,
    )

    academic_advisor_agent = Agent(
        name="Academic Advisor",
        role="Learning Path Designer",
        model=model,
        tools=[google_docs_tool] if google_docs_tool else [],
        instructions=[
            "Concise learning roadmap from the student's materials: ordered subtopics + time per section.",
            "If Google Docs tool exists: one doc + link; else Markdown only.",
        ],
        debug_mode=False,
        markdown=True,
    )

    lib_tools: list = []
    if google_docs_tool:
        lib_tools.append(google_docs_tool)
    if serp_key and SerpApiTools:
        lib_tools.append(SerpApiTools(api_key=serp_key))

    research_librarian_agent = Agent(
        name="Research Librarian",
        role="Learning Resource Specialist",
        model=model,
        tools=lib_tools,
        instructions=[
            "Curate ~8 resources (docs, repos, courses, videos) aligned with the student's topic; "
            "use search sparingly (few queries) if search is available.",
            "If Google Docs tool exists: one doc + link; else Markdown only.",
        ],
        debug_mode=False,
        markdown=True,
    )

    quiz_agent = Agent(
        name="Teaching Assistant",
        role="Quiz Author",
        model=model,
        tools=[],
        instructions=[
            "Create exactly 10 multiple-choice questions from the study material provided.",
            "Cover several distinct subtopics; each question needs a short subtopic label "
            '(2–6 words, e.g. "Gradient descent") for feedback grouping.',
            "Each question: 4 option strings, exactly one correct; correct_index 0–3.",
            "Return ONLY valid JSON, no markdown fences, no prose:",
            '{"questions":[{"question":"...","options":["a","b","c","d"],"correct_index":0,"subtopic":"..."}]}',
        ],
        debug_mode=False,
        markdown=True,
    )

    teachback_agent = Agent(
        name="Active Learning Coach",
        role="Teach-back tutor and evaluator",
        model=model,
        tools=[],
        instructions=[
            "You run a teach-back loop to maximize active recall.",
            "You MUST follow the user's requested UX constraint: do not combine explanation + question in the same 'screen'.",
            "To support that, you will output structured JSON that the app can display in phases.",
            "Write explanations for an 8th-grade student: simple words, short sentences, and one clear idea at a time.",
            "Avoid jargon. If you must use a technical term, define it in a few simple words.",
            "",
            "When asked to GENERATE a round: return ONLY valid JSON (no markdown fences, no prose) with keys:",
            '{"subtopic":"...",'
            '"explanation":"(brief, 4-6 short sentences, 8th-grade level, grounded in provided study excerpt; no fluff)",'
            '"key_ideas":["3-5 short bullet-like ideas that must appear in a good student explanation"],'
            '"question":"One descriptive/free-response question that checks understanding of this subtopic"}',
            "",
            "When asked to EVALUATE: return ONLY valid JSON with keys:",
            '{"score":"X/5",'
            '"correct_ideas":["ideas from key_ideas the student covered"],'
            '"missed_ideas":["ideas from key_ideas the student missed"],'
            '"accuracy_feedback":"Positive, supportive tone. 1-3 sentences: what they got right + fix any misconceptions.",'
            '"clarity_feedback":"Positive, supportive tone. 1-2 sentences on structure/clarity.",'
            '"improvement_suggestion":"Positive tone. 1-2 concrete tips + a better 2-4 sentence model answer. Mention at least one thing they did well."}',
            "",
            "Keep scoring strict but the tone positive: 'You covered X well; next add Y'.",
            "If the excerpt doesn't support a claim, say so briefly in feedback.",
        ],
        debug_mode=False,
        markdown=False,
    )

    mindmap_agent = Agent(
        name="MindMap Builder",
        role="Knowledge Visualizer",
        model=model,
        tools=[],
        instructions=[
            "Extract key concepts from the study material and structure them as a mind map.",
            "Return ONLY valid JSON — no markdown fences, no prose, no explanation.",
            'Format: {"topic":"Root Topic","children":[{"topic":"Branch","children":[{"topic":"Leaf"}]}]}',
            "Max 3 levels deep. Each node must have a \"topic\" key (short, 2-6 words).",
            "Root should be the main subject. Branches = major themes. Leaves = specific concepts.",
            "Aim for 4-6 branches, 2-4 leaves each. Keep labels concise.",
        ],
        debug_mode=False,
        markdown=False,
    )

    recap_agent = Agent(
        name="Professor of Synthesis",
        role="Learning Reinforcement Expert",
        model=model,
        tools=[],
        instructions=[
            "You are an expert Learning Reinforcement specialist. Your goal is to help a student review chapters effectively.",
            "Analyze the material and output THREE distinct sections in Markdown:",
            "1. **🧠 Key Concepts & Definitions**: Identify the most critical terms and provide clear, simple definitions.",
            "2. **🔗 Knowledge Map**: Describe how these concepts relate to each other (e.g. 'Concept A causes B', 'X is a subset of Y').",
            "3. **✨ Personalized Recap**: Provide a concise summary of the material. CRITICAL: Use analogies and metaphors based on the student's specific interests provided in their profile (e.g. sports, gaming, cooking).",
            "Keep the entire response focused and avoid conversational filler. Use bold headings.",
        ],
        debug_mode=False,
        markdown=True,
    )

    assignment_advisor_agent = Agent(
        name="Assignment Advisor",
        role="Grading and Academic Improvement Specialist",
        model=model,
        tools=[],
        instructions=[
            "You are an expert Academic Evaluator. Your goal is to predict a grade for an assignment and provide a clear roadmap for improvement.",
            "You will be given: Assignment Instructions, a Rubric (optional), and the Student's Work.",
            "Identify exactly where the student might lose marks based on the rubric or common academic standards.",
            "Provide concrete, actionable steps to improve the assignment.",
            "Estimate potential grade improvement if all suggestions are followed.",
            "Maintain a constructive, encouraging, but strictly professional tone.",
            "Use clear Markdown formatting with sections: Predicted Grade, Breakdown of Lost Marks, Improvement Roadmap, and Estimated Grade Lift.",
        ],
        debug_mode=False,
        markdown=True,
    )

    return TeachingStack(
        groq_key=groq_key,
        composio_key=composio_key,
        serp_key=serp_key,
        google_docs_tool=google_docs_tool,
        mnemonics_agent=mnemonics_agent,
        academic_advisor_agent=academic_advisor_agent,
        research_librarian_agent=research_librarian_agent,
        quiz_agent=quiz_agent,
        teachback_agent=teachback_agent,
        mindmap_agent=mindmap_agent,
        recap_agent=recap_agent,
        assignment_advisor_agent=assignment_advisor_agent,
    )


def study_prompt_prefix(subject: str, unit: str, material_excerpt: str) -> str:
    return (
        f"Subject: {subject}\n"
        f"Unit / focus: {unit}\n\n"
        "Study material (from the student's uploaded PDFs; may be truncated):\n"
        "-----\n"
        f"{material_excerpt}\n"
        "-----\n"
        "Ground your work in this material when possible. If something is not in the excerpt, say so briefly.\n\n"
    )
def podcast_prompt(subject: str, unit: str, material: str, profile_summary: str) -> str:
    return (
        f"{profile_summary}\n\n"
        f"Subject: {subject}\nUnit: {unit}\n\n"
        f"Study material:\n{material}\n\n"
        "Write a natural conversational podcast script (400-700 words) tailored to this student. "
        "Use their interests as analogies. Start with 'Hey! Welcome back to your study pod...' "
        "End with a quick recap and encouragement. Output ONLY the plain script text, no markdown."
    )


def mindmap_prompt(subject: str, unit: str, material_excerpt: str) -> str:
    return (
        f"Subject: {subject}\nUnit: {unit}\n\n"
        f"Study material excerpt:\n-----\n{material_excerpt}\n-----\n\n"
        "Build a mind map JSON from this material. Return ONLY the JSON object, nothing else.\n"
        "Instructions:\n"
        "- Use the exact format: {\"topic\":\"Root Topic\",\"children\":[{\"topic\":\"Branch\",\"children\":[{\"topic\":\"Leaf\"}]}]}\n"
        "- Keep topics very concise (1-5 words max).\n"
        "- Aim for 4-8 main branches."
    )


def recap_prompt(subject: str, unit: str, material: str, profile_summary: str) -> str:
    return (
        f"{profile_summary}\n\n"
        f"Subject: {subject}\nUnit: {unit}\n\n"
        f"Study material excerpt:\n-----\n{material}\n-----\n\n"
        "Based on the ABOVE material and the student's profile, generate a 'Knowledge Snapshot' for review. "
        "Include: 1. Key Concepts & Definitions, 2. Knowledge Map (Relationships), and 3. Personalized Recap using profile analogies."
    )
def assignment_predictor_prompt(instructions: str, rubric: Optional[str], student_work: str) -> str:
    rubric_section = f"Grading Rubric:\n{rubric}\n\n" if rubric else "No specific rubric provided; use general academic standards.\n\n"
    return (
        "Assignment Analysis Request:\n\n"
        f"Instructions:\n{instructions}\n\n"
        f"{rubric_section}"
        f"Student's Current Work:\n{student_work}\n\n"
        "Please provide a comprehensive evaluation including:\n"
        "1. **Predicted Grade**: Give a realistic assessment.\n"
        "2. **Breakdown of Lost Marks**: Where and why marks are missing.\n"
        "3. **Improvement Roadmap**: Specific things to change/add.\n"
        "4. **Potential Grade Lift**: How much better can it get if improved?"
    )
