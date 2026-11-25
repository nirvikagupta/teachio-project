import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional, Dict, Any

_DEFAULT_GROQ_KEY = ""  # Never hardcode keys: set GROQ_API_KEY in env, .streamlit/secrets.toml, or Streamlit Cloud secrets
_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
]


def call_groq_chat(messages: list[dict], temperature: float = 0.3, max_tokens: int = 3000) -> str:
    """Calls Groq API with fast 120B/20B model failover and generous timeout."""
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        try:
            import streamlit as st
            api_key = str(st.secrets.get("GROQ_API_KEY", "")).strip()
        except Exception:
            api_key = ""
    if not api_key:
        api_key = _DEFAULT_GROQ_KEY
    if not api_key:
        raise ValueError("Missing Groq API Key.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    last_err = None

    for model_id in _GROQ_MODELS:
        payload = {
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "RestartApp/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=35) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                content = data["choices"][0]["message"].get("content", "")
                if content and content.strip():
                    return content
        except Exception as e:
            last_err = e
            continue

    raise RuntimeError(f"All Groq models failed: {last_err}")


def _clean_json(raw: str) -> Any:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        cleaned = cleaned[start : end + 1]
    return json.loads(cleaned)


def _strip_think(raw: str) -> str:
    return re.sub(r"<think>[\s\S]*?</think>", "", raw, flags=re.IGNORECASE).strip()


def _extract_sentences(text: str) -> list[str]:
    raw_sents = re.split(r"(?<=[.!?])\s+|\n+", (text or "").strip())
    return [s.strip() for s in raw_sents if len(s.strip()) > 12]


def _extract_key_terms(text: str, title: str = "") -> list[str]:
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{4,}\b", text or "")
    stop = {
        "write", "report", "assignment", "paper", "study", "using", "must", "should",
        "with", "from", "that", "this", "your", "have", "will", "into", "about",
        "between", "their", "which", "more", "least", "each", "both", "include",
        "discuss", "explain", "evaluate", "compare", "comparing", "word", "words",
        "select", "task", "weightage", "evaluation", "criteria", "completeness",
        "value", "insights", "presentation", "quality", "skills", "product", "system",
        "caters", "everyday", "humans", "said", "observe", "ways", "list", "point",
        "slides", "click", "pictures", "take", "snapshots", "clearly", "convey",
        "observations", "somebody", "else", "house", "selected", "make", "video",
        "explaining", "narrating", "some", "people", "feature", "intended", "iduda",
    }
    seen = []
    for w in words:
        lw = w.lower()
        if lw not in stop and lw not in [s.lower() for s in seen]:
            seen.append(w)
    return seen[:8] if seen else ["Inclusive Design", "Accessibility Barriers", "User Observation", "Interaction Design"]


def decompose_assignment(task_title: str, brief: str, subject: str = "General", due_date: str = "Friday, 11:59 PM") -> dict:
    """Break down dense academic tasks into the 6 canonical stages: Understand -> Research -> Compare -> Draft -> Review -> Submit."""
    sys_prompt = (
        "You are Restart's Academic Task Decomposer. "
        "Break the student's assignment brief into the 6 canonical academic stages: "
        "1) Understand, 2) Research, 3) Compare, 4) Draft, 5) Review, 6) Submit.\n"
        "Tailor every step specifically to the topic and requirements in the student's brief.\n"
        "For EVERY step (1 through 6), provide:\n"
        "- 'step_number' (1..6)\n"
        "- 'phase' (MUST be one of: 'Understand', 'Research', 'Compare', 'Draft', 'Review', 'Submit')\n"
        "- 'title' (clear action title tailored to this brief)\n"
        "- 'subtasks' (list of 2-3 specific sub-bullets)\n"
        "- 'est_minutes' (integer, e.g. 20)\n"
        "- 'difficulty' ('Low', 'Medium', or 'High')\n"
        "- 'depends_on' (string explaining prerequisite dependency, or '' if step 1)\n"
        "- 'first_action' (the immediate concrete next action to start)\n"
        "- 'two_minute_version' (an even smaller micro-action if the student clicks 'Make this smaller')\n"
        "- 'why_it_matters' (1 sentence explaining why the student is doing this step)\n"
        "- 'plain_explanation' (1-2 sentences explaining what this step means in simple language)\n"
        "- 'guidance' (brief tip on what completion looks like)\n"
        "Return ONLY valid JSON with keys:\n"
        "{\n"
        '  "title": "Clear assignment title",\n'
        '  "simplified_brief": "What you are being asked to do in 1-2 plain-language sentences",\n'
        '  "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"],\n'
        '  "steps": [ ... ]\n'
        "}"
    )

    user_msg = f"Assignment Title: {task_title}\nCourse: {subject}\nDue Date: {due_date}\nBrief:\n{brief}"

    try:
        raw = call_groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ])
        parsed = _clean_json(raw)
        if isinstance(parsed, dict) and parsed.get("steps"):
            return parsed
    except Exception:
        pass
    return _content_aware_decomposition(task_title, brief, subject)


def get_stuck_support(task_title: str, current_step_title: str, obstacle: str, context: dict) -> dict:
    """Provide contextual scaffolding when a student clicks 'I am stuck' or uses the right-side companion."""
    sys_prompt = (
        "You are Restart's Contextual Study Companion. A student is working on an assignment step and needs immediate, concrete help.\n"
        "Give direct academic scaffolding tied to their exact assignment, current step, and notes.\n"
        "Return ONLY valid JSON with:\n"
        "{\n"
        '  "insight": "Clear, plain-language explanation or acknowledgment",\n'
        '  "micro_action": "One concrete action they can do in the next 2 minutes",\n'
        '  "example_or_structure": "A concrete sentence starter, outline, or template they can insert directly into their draft"\n'
        "}"
    )

    user_msg = (
        f"Assignment: {task_title}\n"
        f"Current Step: {current_step_title}\n"
        f"Request / Obstacle: {obstacle}\n"
        f"Completed Steps: {context.get('completed_steps', [])}\n"
        f"Current Notes/Draft:\n{context.get('notes', '')}\n"
    )

    try:
        raw = call_groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ])
        parsed = _clean_json(raw)
        if isinstance(parsed, dict) and "micro_action" in parsed:
            return parsed
    except Exception:
        pass
    return _fallback_stuck_support(obstacle, current_step_title, task_title)


def generate_context_summary(task: dict, completed_step_titles: list, notes: str, stuck_reason: str = "") -> dict:
    """AI dynamically captures cognitive continuity state from user's actual work."""
    steps = task.get("steps", [{}])
    cur_idx = min(task.get("current_step_idx", 0), max(0, len(steps) - 1))
    cur_step = steps[cur_idx] if steps else {}
    task_title = task.get("title", "Active Assignment")
    step_title = cur_step.get("title", "Current Stage")
    phase_title = cur_step.get("phase", "Current Stage")

    sys_prompt = (
        "You are Restart's Cognitive Continuity Engine. A student is pausing or leaving their study session.\n"
        "Analyze their active step and their written notes/draft to reconstruct their exact thinking state.\n"
        "Ground your response strictly in their assignment and notes.\n"
        "Return ONLY valid JSON with:\n"
        "{\n"
        '  "working_on": "Specific section/concept they were actively working on",\n'
        '  "completed": ["Completed item 1", "Completed item 2"],\n'
        '  "tried": "What approach or draft ideas they attempted in their notes",\n'
        '  "stuck_on": "Where they paused, hesitated, or what open question remains",\n'
        '  "last_thought": "Their last written thought or key takeaway",\n'
        '  "next_step": "The single concrete next action to resume seamlessly"\n'
        "}"
    )

    user_msg = (
        f"Assignment: {task_title}\n"
        f"Active Stage: {phase_title} — {step_title}\n"
        f"Completed Stages: {completed_step_titles}\n"
        f"Student's Workspace Notes:\n{notes}\n"
        f"Student's pause note: {stuck_reason}\n"
    )

    try:
        raw = call_groq_chat([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ], temperature=0.2)
        data = _clean_json(raw)
        if isinstance(data, dict) and "next_step" in data and "working_on" in data:
            return data
    except Exception:
        pass

    note_lines = [ln.strip() for ln in (notes or "").splitlines() if ln.strip()]
    last_line = note_lines[-1] if note_lines else f"Outlined core ideas for {step_title}"
    first_line = note_lines[0] if note_lines else f"Reviewed requirements for {task_title}"
    return {
        "working_on": f"{phase_title}: {step_title}",
        "completed": completed_step_titles if completed_step_titles else ([first_line[:60]] if note_lines else [f"Initiated {phase_title}"]),
        "tried": f"Drafted in notes: \"{last_line[:80]}\"" if note_lines else f"Reviewed objectives for {step_title}",
        "stuck_on": stuck_reason if stuck_reason else f"Connecting evidence to the next section of {step_title}",
        "last_thought": last_line,
        "next_step": cur_step.get("first_action", f"Continue drafting the next point for {step_title}."),
    }


def extract_and_teach_concepts(task: dict) -> dict:
    """Automatically extracts the underlying academic/domain concepts required to do the assignment
    and generates actual educational lessons teaching those concepts (NOT repeating the assignment instructions).
    """
    # If the task already has valid extracted concepts, reuse them immediately without burning API quota!
    existing = task.get("extracted_concepts")
    if isinstance(existing, list) and len(existing) >= 2:
        if not any("Core Principle:" in c.get("name", "") or "Contrasting Mechanism:" in c.get("name", "") for c in existing):
            return {"concepts": existing}

    title = task.get("title", "Academic Assignment")
    brief = task.get("original_brief", "") or task.get("simplified_brief", "")
    subject = task.get("subject", "Coursework")

    sys_prompt = (
        "You are an expert university professor and concept tutor. Read the student's assignment brief carefully.\n"
        "CRITICAL RULES:\n"
        "1. NEVER use the assignment title, course code (like 'IDUDA'), or rubric words ('Task', 'Select', 'Weightage', 'Completeness') as concept names!\n"
        "2. DO NOT just repeat the assignment instructions.\n"
        "3. Identify the 3 to 4 real underlying ACADEMIC / THEORETICAL CONCEPTS from the discipline that the student needs to understand to do this assignment well, and TEACH those concepts in depth.\n"
        "   (For example, if the brief asks to find mismatched interactions and permanent/temporary/situational disabilities in an everyday product, the concepts to teach are:\n"
        "   - 'Mismatched Interactions & Inclusive Design (Kat Holmes Framework)'\n"
        "   - 'The Persona Spectrum: Permanent, Temporary & Situational Disabilities'\n"
        "   - 'Affordances, Signifiers & Accessibility Barriers in Everyday Objects'\n"
        "   - 'Contextual Inquiry & Observational POV Testing')\n"
        "Return ONLY valid JSON with this structure:\n"
        "{\n"
        '  "concepts": [\n'
        "    {\n"
        '      "name": "1. Clear Academic Concept Name",\n'
        '      "category": "Core Theory / Framework / Method",\n'
        '      "intuition": "One-sentence plain-English intuition of what this concept actually means",\n'
        '      "lesson": "2-3 rich, educational paragraphs teaching the theory, how it works, and what to look for",\n'
        '      "analogy_or_example": "A concrete real-world example that makes the concept click immediately",\n'
        '      "key_takeaway": "1 actionable takeaway to apply when doing the assignment"\n'
        "    }\n"
        "  ]\n"
        "}"
    )

    try:
        raw = call_groq_chat(
            [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Course: {subject}\nAssignment: {title}\nBrief:\n{brief}"},
            ],
            temperature=0.3,
            max_tokens=2000,
        )
        data = _clean_json(raw)
        if isinstance(data, dict) and data.get("concepts"):
            return data
    except Exception:
        pass

    return _content_aware_concept_lessons(title, brief, subject)


def _content_aware_concept_lessons(title: str, brief: str, subject: str) -> dict:
    low = f"{title} {brief}".lower()
    if "iou" in low or "computer-vision" in low or "computer vision" in low or "overlap" in low or "cv" in low:
        return {
            "concepts": [
                {
                    "name": "1. Intersection over Union (IoU) & Spatial Overlap",
                    "category": "Localization Metric",
                    "intuition": "IoU measures how accurately a model's predicted bounding box lines up with the real object.",
                    "lesson": (
                        "In computer vision object detection, a model predicts a rectangular bounding box around an object. "
                        "To know if that prediction is accurate, we compare the predicted box against the ground-truth box drawn by a human.\n\n"
                        "Intersection over Union (IoU) divides the Area of Overlap (where both boxes intersect) by the Area of Union "
                        "(the total space covered by both boxes combined). An IoU of 1.0 means perfect alignment, while 0.0 means no overlap at all. "
                        "Most benchmarks consider a detection 'correct' only when IoU is at least 0.50 or 0.75."
                    ),
                    "analogy_or_example": (
                        "Imagine placing a circular coaster over a water ring on a table. If the coaster covers the exact ring, overlap is 100% (IoU = 1.0). "
                        "If it's shifted halfway off, the shared area divided by the total footprint drops below 0.5."
                    ),
                    "key_takeaway": "Higher IoU = tighter, more precise object boundaries, but often requires heavier multi-stage computation.",
                },
                {
                    "name": "2. Inference Latency & Runtime Throughput (FPS)",
                    "category": "Systems Efficiency",
                    "intuition": "Runtime efficiency measures how fast a trained model can process a new image and output a result.",
                    "lesson": (
                        "While training happens once on powerful servers, inference happens every time the model runs on a live camera frame. "
                        "Latency is the time (in milliseconds) it takes to process one frame, and throughput is measured in Frames Per Second (FPS).\n\n"
                        "For real-time applications (like autonomous driving or assistive glasses for visually impaired users), a model needs at least "
                        "30 FPS (under 33ms per frame). If a model takes 500ms per image, its predictions arrive too late to be useful in the real world."
                    ),
                    "analogy_or_example": (
                        "A translator who gives a 100% poetic translation 10 minutes after a conversation ends has high accuracy but unusable latency. "
                        "A live interpreter who translates within 1 second keeps the conversation flowing."
                    ),
                    "key_takeaway": "Real-time edge systems prioritize low latency (high FPS) so feedback happens instantaneously.",
                },
                {
                    "name": "3. The Accuracy vs. Speed Trade-Off in Architectures",
                    "category": "Core Mechanism",
                    "intuition": "Two-stage detectors maximize spatial overlap (IoU), while single-stage detectors optimize runtime speed.",
                    "lesson": (
                        "Computer vision models generally fall into two architectural families:\n"
                        "• Two-Stage Detectors (e.g., Faster R-CNN): First propose candidate regions, then refine each bounding box carefully. "
                        "This achieves very high IoU and small-object accuracy, but runs slower.\n"
                        "• Single-Stage Detectors (e.g., YOLO, SSD): Predict bounding boxes and classes in a single forward pass across a grid. "
                        "By skipping the separate region-proposal stage, they run at 60+ FPS with slightly looser bounding-box overlap."
                    ),
                    "analogy_or_example": (
                        "Two-stage detection is like sketching a rough outline in pencil before tracing carefully in ink. "
                        "Single-stage detection is drawing directly in ink in one swift stroke."
                    ),
                    "key_takeaway": "Choosing an evaluation approach depends on the deployment constraint: medical imaging favors IoU precision; live video favors runtime FPS.",
                },
            ]
        }

    # Intelligent domain-concept fallback (never picks random words like 'Excludes' or 'Special')
    if any(k in low for k in ("disabilit", "excludes", "inaccessib", "mismatch", "situational", "special populations", "affordance", "inclusive")):
        return {
            "concepts": [
                {
                    "name": "1. Inclusive Design & Mismatched Interactions",
                    "category": "Core Design Theory",
                    "intuition": "Disability happens at the point of interaction when a product's design fails to match a human's capabilities.",
                    "lesson": (
                        "In Kat Holmes' Inclusive Design framework (and the Social Model of Disability), exclusion is not a personal health condition — "
                        "it is a mismatched human interaction between a user and an environment or object.\n\n"
                        "When designers build products around an 'average' user's eyesight, grip strength, hearing, or reach, anyone outside that narrow "
                        "norm experiences friction or total exclusion."
                    ),
                    "analogy_or_example": "A heavy door with a round brass knob excludes someone with arthritis or wet hands, whereas a lever handle or automatic sensor works effortlessly for everyone.",
                    "key_takeaway": "Look for features that assume two hands, perfect vision, fine motor precision, or quiet surroundings.",
                },
                {
                    "name": "2. The Persona Spectrum (Permanent, Temporary & Situational)",
                    "category": "Accessibility Framework",
                    "intuition": "Designing for permanent disabilities simultaneously solves temporary and situational barriers experienced by everyone.",
                    "lesson": (
                        "The Microsoft Inclusive Design Persona Spectrum groups accessibility barriers into three connected contexts:\n"
                        "• Permanent disability: e.g., having one arm, congenital blindness, or deafness.\n"
                        "• Temporary disability: e.g., a wrist in a cast after a fall, dilated pupils after an eye exam, or an ear infection.\n"
                        "• Situational limitation: e.g., a new parent holding an infant in one arm, bright outdoor glare on a phone screen, or a noisy train station."
                    ),
                    "analogy_or_example": "Closed captions were created for Deaf viewers (permanent), but help someone with an ear infection (temporary) or someone watching a video in a quiet library (situational).",
                    "key_takeaway": "For every barrier you observe in your chosen product, map how it affects permanent, temporary, and situational users.",
                },
                {
                    "name": "3. Affordances, Signifiers & Sensory Feedback Barriers",
                    "category": "Interaction Design (Don Norman)",
                    "intuition": "An accessible product communicates how it works across multiple senses (visual, tactile, auditory) and requires minimal physical effort.",
                    "lesson": (
                        "Don Norman distinguishes between affordances (what actions an object allows) and signifiers (the clues that tell you how to use it). "
                        "Exclusion occurs when signifiers rely on a single sensory channel — such as a flat touchscreen appliance with no tactile bumps for blind users, "
                        "or a microwave that only beeps with no visual alert for Deaf users."
                    ),
                    "analogy_or_example": "A flat glass induction stove with touch-only icons gives zero tactile feedback, making it dangerous or impossible to operate without sight.",
                    "key_takeaway": "Check whether your product provides multi-sensory feedback (visual + audio + tactile) and forgiving error recovery.",
                },
                {
                    "name": "4. Contextual Inquiry & Observational User Testing",
                    "category": "Research Methodology",
                    "intuition": "Watching another person use a product in a real household environment reveals hidden barriers that designers overlook.",
                    "lesson": (
                        "Contextual inquiry involves observing a user performing a real task in their natural setting while asking them to think aloud. "
                        "People often blame themselves ('I'm bad with technology') when they struggle, so observing their exact posture, grip, hesitation, "
                        "and workarounds uncovers design flaws that surveys miss."
                    ),
                    "analogy_or_example": "Watching a family member try to open a medicine bottle or navigate a smart TV remote reveals the exact moment their hand slips or an icon confuses them.",
                    "key_takeaway": "Capture photos/snapshots of the exact hand position, screen glare, or confusing button during use as visual evidence.",
                },
            ]
        }

    return {
        "concepts": [
            {
                "name": f"1. Foundational Theory & Mechanisms in {title}",
                "category": "Core Theory",
                "intuition": f"Understanding the underlying principles and cause-and-effect mechanisms behind {title}.",
                "lesson": (
                    f"Every academic investigation starts with a theoretical model that explains how the core components interact. "
                    f"Rather than looking at surface symptoms, identify the structural rules and constraints governing the system."
                ),
                "analogy_or_example": "Like understanding how an engine converts fuel into motion before diagnosing why a car loses speed uphill.",
                "key_takeaway": "Anchor your analysis in established disciplinary definitions and mechanisms.",
            },
            {
                "name": "2. Comparative Trade-Offs & System Constraints",
                "category": "Analytical Framework",
                "intuition": "No design or method optimizes every goal at once; improving one dimension creates trade-offs in another.",
                "lesson": (
                    "When evaluating any system, product, or methodology, identify the competing constraints (such as precision vs. speed, "
                    "simplicity vs. flexibility, or cost vs. accessibility) and analyze who benefits and who is underserved."
                ),
                "analogy_or_example": "A Swiss Army knife maximizes versatility, while a chef's knife maximizes cutting precision.",
                "key_takeaway": "Evaluate how the system performs across diverse real-world conditions.",
            },
            {
                "name": "3. Empirical Evidence & Observational Validation",
                "category": "Research Methodology",
                "intuition": "Strong academic claims connect theoretical concepts to concrete, observable evidence.",
                "lesson": (
                    "To prove a claim convincingly, pair each conceptual point with empirical evidence — such as quantitative metrics, "
                    "direct user observations, annotated photographs, or peer-reviewed studies."
                ),
                "analogy_or_example": "A courtroom argument relies on physical exhibits and eyewitness testimony, not just assertions.",
                "key_takeaway": "Back every observation with a concrete example and link it back to the core theory.",
            },
        ]
    }


def reshape_reading_text(text: str, mode: str, task_title: str = "") -> dict:
    """Transforms concept lessons into Simple Analogies (ELI12), Key Takeaways, or Plain Explanations."""
    clean_text = (text or "").strip()
    if not clean_text:
        return {"result": "No concept text provided.", "simpler_language": "No concept provided.", "why_it_matters": ""}

    if mode == "explain":
        sys_prompt = (
            "You are a university concept tutor. Explain the academic concept or question the student asked in plain, intuitive language.\n"
            "Teach the actual concept itself (how it works, its mechanism, and a concrete real-world analogy), NOT how to write their essay.\n"
            "Return ONLY valid JSON with:\n"
            "{\n"
            '  "simpler_language": "Clear, intuitive explanation of the concept and how it works",\n'
            '  "why_it_matters": "A concrete real-world example or analogy that makes the concept stick"\n'
            "}"
        )
        try:
            raw = call_groq_chat([
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"Topic context: {task_title}\nConcept question:\n{clean_text}"},
            ])
            data = _clean_json(raw)
            if isinstance(data, dict) and "simpler_language" in data:
                return data
        except Exception:
            pass
        terms = _extract_key_terms(clean_text, task_title)
        focus = ", ".join(terms[:3])
        return {
            "simpler_language": (
                f"In simple terms, '{clean_text}' revolves around how {focus} interact in practice: "
                f"understanding the cause-and-effect mechanism behind {terms[0] if terms else task_title} lets you predict when and why it succeeds or fails."
            ),
            "why_it_matters": (
                f"Real-world analogy: Think of {terms[0] if terms else 'this mechanism'} like a thermostat feedback loop — "
                f"it continuously measures the gap between the target state and current reality, adjusting output accordingly."
            ),
        }

    prompts = {
        "simplify": "Rewrite these academic concept lessons using simple everyday analogies (Explain Like I'm 12) so any student can grasp the intuition immediately.",
        "summarize": "Extract a crisp Cheat-Sheet of Key Conceptual Takeaways & Definitions from these concept lessons.",
    }
    sys_msg = prompts.get(mode, prompts["simplify"])
    try:
        out = call_groq_chat([
            {"role": "system", "content": sys_msg},
            {"role": "user", "content": f"Assignment Topic: {task_title}\n\nConcept Lessons:\n{clean_text}"},
        ])
        cleaned_out = _strip_think(out)
        if cleaned_out:
            return {"result": cleaned_out}
    except Exception:
        pass

    sents = _extract_sentences(clean_text)
    terms = _extract_key_terms(clean_text, task_title)
    if mode == "summarize":
        bullets = "\n\n".join(f"• **Key Takeaway {i+1}:** {s}" for i, s in enumerate(sents[:4]))
        return {"result": bullets or f"• **Core Concepts for {task_title}:** {', '.join(terms[:5])}"}

    bullets = "\n\n".join(f"• **In Simple Terms:** {s}" for s in sents[:5])
    return {"result": f"**Everyday Intuition ({task_title}):**\n\n{bullets or clean_text}"}


def generate_study_tool_content(task: dict, tool_type: str) -> dict:
    """Generates Flashcards, Quiz, and Mind Map that test and teach the EXTRACTED ACADEMIC CONCEPTS (not the assignment instructions)."""
    concepts_data = extract_and_teach_concepts(task)
    concepts = concepts_data.get("concepts", [])
    title = task.get("title", "Academic Topic")
    concepts_summary = "\n\n".join(
        f"Concept: {c.get('name')}\nCategory: {c.get('category')}\nIntuition: {c.get('intuition')}\nLesson: {c.get('lesson')}\nExample: {c.get('analogy_or_example')}\nTakeaway: {c.get('key_takeaway')}"
        for c in concepts
    )

    if tool_type == "flashcards":
        sys_prompt = (
            "Create 4 educational flashcards that teach the underlying academic/technical CONCEPTS below.\n"
            "CRITICAL FORMATTING RULES:\n"
            "- 'front': A short, clear conceptual question (max 15 words).\n"
            "- 'back': A concise, scannable answer (max 35 words). Use 2-3 short bullet points separated by '\\n'. Do NOT write a long wall of text.\n"
            "Return ONLY valid JSON: {\"cards\": [{\"front\": \"Short conceptual question?\", \"back\": \"• Point 1\\n• Point 2\"}]}"
        )
        try:
            raw = call_groq_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Topic: {title}\n\n{concepts_summary}"}])
            data = _clean_json(raw)
            if isinstance(data, dict) and data.get("cards"):
                return data
        except Exception:
            pass

        cards = []
        for c in concepts[:4]:
            c_name = c.get("name", "Core Concept").split(". ")[-1]
            cards.append({
                "front": f"What is {c_name} and how does its mechanism work?",
                "back": f"{c.get('intuition', '')} {c.get('key_takeaway', '')}".strip(),
            })
        if len(cards) < 4 and concepts:
            c0 = concepts[0]
            cards.append({
                "front": f"Give a real-world analogy or example of {c0.get('name', '').split('. ')[-1]}.",
                "back": c0.get("analogy_or_example", c0.get("intuition", "")),
            })
        return {"cards": cards}

    if tool_type == "quiz":
        sys_prompt = (
            "Create a 3-question multiple-choice quiz testing the student's conceptual understanding of the academic concepts below.\n"
            "DO NOT ask about essay word counts or assignment instructions — test the actual domain concepts!\n"
            "Return ONLY valid JSON: {\"questions\": [{\"question\": \"...\", \"options\": [\"A\", \"B\", \"C\", \"D\"], \"answer\": 0, \"explanation\": \"...\"}]}"
        )
        try:
            raw = call_groq_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Topic: {title}\n\n{concepts_summary}"}])
            data = _clean_json(raw)
            if isinstance(data, dict) and data.get("questions"):
                return data
        except Exception:
            pass

        questions = []
        for idx, c in enumerate(concepts[:3]):
            c_name = c.get("name", f"Concept {idx+1}").split(". ")[-1]
            correct_opt = c.get("intuition") or c.get("key_takeaway") or f"It defines the core mechanism of {c_name}."
            questions.append({
                "question": f"Which statement best describes the core mechanism of {c_name}?",
                "options": [
                    correct_opt,
                    f"{c_name} has no measurable effect on system outcomes or trade-offs",
                    f"{c_name} eliminates the need for empirical evaluation criteria",
                    f"{c_name} only applies when all variables remain completely static",
                ],
                "answer": 0,
                "explanation": f"{c.get('key_takeaway', correct_opt)} ({c.get('analogy_or_example', '')})",
            })
        return {"questions": questions}

    # Mind map of the domain concepts
    sys_prompt = (
        "Create a 3-node conceptual Mind Map showing how these academic concepts work and connect (Concept -> Mechanism/Relationships -> Real-World Example).\n"
        "Return ONLY valid JSON: {\"nodes\": [{\"concept\": \"...\", \"relationships\": [\"...\", \"...\"], \"example\": \"...\"}]}"
    )
    try:
        raw = call_groq_chat([{"role": "system", "content": sys_prompt}, {"role": "user", "content": f"Topic: {title}\n\n{concepts_summary}"}])
        data = _clean_json(raw)
        if isinstance(data, dict) and data.get("nodes"):
            return data
    except Exception:
        pass

    return {
        "nodes": [
            {
                "concept": c.get("name", "Core Concept"),
                "relationships": [c.get("category", "Mechanism"), c.get("key_takeaway", "Core principle")],
                "example": c.get("analogy_or_example", ""),
            }
            for c in concepts
        ]
    }


def _content_aware_decomposition(title: str, brief: str, subject: str) -> dict:
    clean_title = title.strip() or "Academic Assignment"
    sents = _extract_sentences(brief)
    terms = _extract_key_terms(brief, clean_title)
    t_a = terms[0] if terms else "Concept A"
    t_b = terms[1] if len(terms) > 1 else "Concept B"
    summary = " ".join(sents[:2]) if sents else f"Complete the research, analysis, and written deliverable for '{clean_title}'."

    reqs = sents[:4] if len(sents) >= 2 else [
        f"Understand the core prompt and scope for {clean_title}",
        f"Research and extract evidence covering {', '.join(terms[:3])}",
        f"Compare and analyze key findings",
        "Draft, review citations, and submit final deliverable",
    ]

    return {
        "title": clean_title,
        "simplified_brief": summary,
        "requirements": reqs,
        "steps": [
            {
                "step_number": 1,
                "phase": "Understand",
                "title": f"Understand the prompt & key concepts ({t_a}, {t_b})",
                "subtasks": [
                    f"Read the core objective: {sents[0][:90] + '...' if sents else clean_title}",
                    f"List the main concepts to cover: {', '.join(terms[:4])}",
                ],
                "est_minutes": 15,
                "difficulty": "Low",
                "depends_on": "",
                "first_action": f"Write 2 bullet points in your notes defining how {t_a} and {t_b} relate to {clean_title}.",
                "two_minute_version": f"Type '{t_a}' and '{t_b}' as headings at the top of your workspace notes.",
                "why_it_matters": "Clarifying the core terms first prevents wasted reading later.",
                "plain_explanation": f"You are making a quick checklist of what '{clean_title}' is asking before you search for sources.",
                "guidance": "List the main question and 2 evaluation criteria.",
            },
            {
                "step_number": 2,
                "phase": "Research",
                "title": f"Find sources & evidence on {t_a} and {t_b}",
                "subtasks": [
                    f"Find relevant sources addressing {', '.join(terms[:3])}",
                    "Extract 1–2 concrete findings, quotes, or metrics from each source",
                ],
                "est_minutes": 25,
                "difficulty": "Medium",
                "depends_on": "Complete '01 Understand' before searching for sources.",
                "first_action": f"Find one paper or source analyzing {t_a} and {t_b} for {clean_title}.",
                "two_minute_version": f"Open Google Scholar and search: \"{clean_title} {t_a} {t_b}\"",
                "why_it_matters": "Gives you the concrete evidence you'll cite in your draft.",
                "plain_explanation": "Skim abstracts and conclusions to pull 1–2 concrete facts per source.",
                "guidance": "Paste the source title and one key finding into your workspace notes.",
            },
            {
                "step_number": 3,
                "phase": "Compare",
                "title": f"Compare findings & trade-offs ({t_a} vs. {t_b})",
                "subtasks": [
                    f"Outline the core mechanism and strengths of {t_a}",
                    f"Outline the core mechanism and trade-offs of {t_b}",
                    "Synthesize how they compare against your assignment criteria",
                ],
                "est_minutes": 30,
                "difficulty": "Medium",
                "depends_on": "Complete '02 Research' before '03 Compare'.",
                "first_action": f"Draft 3 bullet points comparing {t_a} and {t_b} using your collected notes.",
                "two_minute_version": f"Write one sentence starting with: 'The key difference between {t_a} and {t_b} is...'",
                "why_it_matters": "This comparison forms the analytical backbone of your assignment.",
                "plain_explanation": "Put your findings side by side so you can see where each approach succeeds or struggles.",
                "guidance": "Focus on specific evidence rather than generalities.",
            },
            {
                "step_number": 4,
                "phase": "Draft",
                "title": f"Draft the core analysis paragraphs for {clean_title}",
                "subtasks": [
                    "Turn your comparison bullet points into structured paragraphs",
                    "Integrate supporting evidence from your sources",
                    "Write the conclusion answering the core assignment prompt",
                ],
                "est_minutes": 35,
                "difficulty": "Medium",
                "depends_on": "Complete '03 Compare' before drafting full paragraphs.",
                "first_action": "Turn your first comparison bullet point into a complete 3-sentence paragraph.",
                "two_minute_version": f"Write the opening topic sentence for your {clean_title} analysis section.",
                "why_it_matters": "Transforms your structured notes into the actual submission draft.",
                "plain_explanation": "Connect the bullet points you already wrote into smooth sentences with citations.",
                "guidance": "Let the first draft be rough; polishing comes in Stage 05 (Review).",
            },
            {
                "step_number": 5,
                "phase": "Review",
                "title": "Review argument clarity, rubric & citations",
                "subtasks": [
                    "Verify every requirement from the brief is addressed",
                    "Check citation formatting and transition clarity",
                ],
                "est_minutes": 15,
                "difficulty": "Low",
                "depends_on": "Complete '04 Draft' before reviewing.",
                "first_action": "Read your draft paragraphs out loud to check clarity and flow.",
                "two_minute_version": "Verify that every source mentioned in your text appears in your reference list.",
                "why_it_matters": "Catches missing requirements or unclear transitions before submission.",
                "plain_explanation": "Do a calm quality check against the original prompt.",
                "guidance": "Check word count and rubric points.",
            },
            {
                "step_number": 6,
                "phase": "Submit",
                "title": "Final export & submission check",
                "subtasks": [
                    "Export final document to PDF/DOCX",
                    "Upload to course portal before deadline",
                ],
                "est_minutes": 10,
                "difficulty": "Low",
                "depends_on": "Complete '05 Review' before final submission.",
                "first_action": "Export your completed draft and verify the file opens cleanly.",
                "two_minute_version": "Save your final draft with the required course filename.",
                "why_it_matters": "Completes the assignment loop cleanly and on time.",
                "plain_explanation": "Final check and upload.",
                "guidance": "Double-check filename and submit.",
            },
        ],
    }


def _fallback_stuck_support(obstacle: str, step_title: str, task_title: str = "") -> dict:
    lookup = {
        "I don't understand the task": {
            "insight": f"In simple terms: '{step_title}' is asking you to identify the main building blocks for '{task_title}' before writing full paragraphs.",
            "micro_action": "Write 2 plain bullet points answering: 1) What concept is being examined? 2) What evidence supports it?",
            "example_or_structure": f"Starter template for {task_title}:\n• Core concept / approach: [...]\n• Main strength / finding: [...]\n• Limitation / trade-off: [...]",
        },
        "Help me understand this": {
            "insight": f"'{step_title}' breaks '{task_title}' into concrete evidence rather than trying to write everything at once.",
            "micro_action": "Look at your notes and write one sentence summarizing your main takeaway so far.",
            "example_or_structure": "Why this matters: Completing this stage gives you the exact evidence you'll plug into your draft paragraphs.",
        },
        "Make this simpler": {
            "insight": "Let's strip away the academic jargon and shrink this stage to a 2-minute micro-action.",
            "micro_action": "Don't write a full paragraph yet. Just jot down 3 rough bullet fragments in your notes.",
            "example_or_structure": "Micro-template:\n1. Key Point A: [1 finding]\n2. Key Point B: [1 finding]\n3. Main takeaway: [1 sentence]",
        },
        "What's my next step?": {
            "insight": f"You are currently on '{step_title}'. Focus only on the single next micro-action.",
            "micro_action": "Add 2 bullet points to your notes for this stage, then click '✓ Complete Stage & Next →'.",
            "example_or_structure": "Next up: Turn your bullet points into a short analytical paragraph.",
        },
    }
    return lookup.get(obstacle, lookup["Make this simpler"])
