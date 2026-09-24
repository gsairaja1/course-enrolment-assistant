from pathlib import Path
import re

from transformers import AutoTokenizer, AutoModelForCausalLM


# ============================================================
# 1. PATHS AND MODEL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
HANDBOOK_DIR = BASE_DIR / "data" / "handbook"

MODEL_NAME = "HuggingFaceTB/SmolLM2-1.7B-Instruct"


# ============================================================
# 2. LOAD AI MODEL
# ============================================================

# Load the model only when it is first needed.
# This avoids loading the 1.7B model during Streamlit import/startup.
tokenizer = None
model = None

# Latest AI draft and validation error, exposed to app.py for UI display.
last_ai_response = ""
last_ai_validation_error = ""


def load_reply_model():
    """Load the reply model once, on first use."""

    global tokenizer, model

    if tokenizer is not None and model is not None:
        return

    print("Loading reply model...")

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME
    )

    model.eval()

    print("Reply model loaded.")


# ============================================================
# 3. HANDBOOK HELPERS
# ============================================================

def load_handbook(filename):
    """Load one handbook Markdown file."""

    path = HANDBOOK_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Handbook file not found: {filename}"
        )

    return path.read_text(
        encoding="utf-8"
    )


def build_handbook_text(handbook_files):
    """Combine the supplied handbook pages into one text block."""

    parts = []

    for filename in handbook_files or []:

        try:
            text = load_handbook(filename)
        except FileNotFoundError:
            continue

        parts.append(
            f"--- {filename} ---\n{text}"
        )

    return "\n\n".join(parts)


# ============================================================
# 4. TEXT VALIDATION HELPERS
# ============================================================

def extract_numbers_and_codes(text):

    numbers = re.findall(
        r"\b\d+(?:\.\d+)?\b",
        text
    )

    course_codes = re.findall(
        r"\b[A-Z]{2,4}\d{3}\b",
        text
    )

    return numbers, course_codes


def check_reasons(reply, reasons):
    """
    Every verified Python reason must appear exactly.
    This prevents the AI from changing the facts.
    """

    reply_lower = reply.lower()

    for reason in reasons or []:

        if reason.lower() not in reply_lower:

            return False, (
                f"reason missing: {reason}"
            )

    return True, ""


def check_handbook_pages(reply, handbook_files):

    reply_lower = reply.lower()

    for filename in handbook_files or []:

        if filename.lower() not in reply_lower:

            return False, (
                f"handbook page {filename} is missing"
            )

    return True, ""


def check_numbers_and_codes(
    reply,
    allowed_text
):

    reply_numbers, reply_codes = (
        extract_numbers_and_codes(reply)
    )

    allowed_numbers, allowed_codes = (
        extract_numbers_and_codes(allowed_text)
    )

    for number in reply_numbers:

        if number not in allowed_numbers:

            return False, (
                f"number {number} was not supplied"
            )

    for code in reply_codes:

        if code not in allowed_codes:

            return False, (
                f"course code {code} was not supplied"
            )

    return True, ""



def check_waiver_safety(reply):

    reply_lower = reply.lower()

    if "waiver" not in reply_lower:
        return True, ""

    approval_phrases = [
        "course leader",
        "course leader approves",
        "approved by the course leader",
        "course leader decides",
        "department",
        "named member of staff"
    ]

    if not any(
        phrase in reply_lower
        for phrase in approval_phrases
    ):

        return False, (
            "waiver mentioned without approval authority"
        )

    forbidden_phrases = [
        "enrolment is approved",
        "enrollment is approved",
        "you are approved",
        "course is approved",
        "approved for enrolment",
        "approved for enrollment",
        "enrolment has been approved",
        "enrollment has been approved",
        "you may now enrol",
        "you may now enroll"
    ]

    for phrase in forbidden_phrases:

        if phrase in reply_lower:

            return False, (
                "reply incorrectly says enrolment is approved"
            )

    return True, ""


def check_alternative(
    reply,
    alternatives
):

    if not alternatives:
        return True, ""

    reply_lower = reply.lower()

    for code, title in alternatives:

        if code.lower() in reply_lower:
            return True, ""

        if title.lower() in reply_lower:
            return True, ""

    return False, (
        "eligible alternative course is missing"
    )


def needs_alternative(reasons):

    reason_text = " ".join(
        reasons or []
    ).lower()

    return (
        "full" in reason_text
        or "prerequisite" in reason_text
    )


def normalize_alternatives(alternatives):
    """
    Convert alternatives to:
        [("CS101", "Programming Foundations"), ...]

    Supports both:
        {"course_code": "CS101", "title": "Programming Foundations"}
    and:
        ("CS101", "Programming Foundations")
    """

    normalized = []

    for alternative in alternatives or []:

        if isinstance(alternative, dict):

            code = str(
                alternative.get("course_code", "")
            ).strip()

            title = str(
                alternative.get("title", "")
            ).strip()

            if code and title:
                normalized.append((code, title))

        elif (
            isinstance(alternative, (tuple, list))
            and len(alternative) >= 2
        ):

            code = str(alternative[0]).strip()
            title = str(alternative[1]).strip()

            if code and title:
                normalized.append((code, title))

    return normalized


# ============================================================
# 5. SAFE FALLBACK
# ============================================================

def fallback_reply(
    reasons,
    handbook_files,
    alternatives,
    handbook_text=None
):
    """
    Deterministic answer used when the local AI output
    fails validation.

    This is intentionally based only on verified Python data.
    """

    reasons = reasons or []
    handbook_files = handbook_files or []
    alternatives = normalize_alternatives(
        alternatives
    )

    if reasons:

        reason_lines = "\n".join(
            f"- {reason}"
            for reason in reasons
        )

        reply = (
            "You are not currently eligible to enrol "
            "for the following reason(s):\n"
            f"{reason_lines}"
        )

    else:

        reply = (
            "There are no blocking reasons for enrolment."
        )

    if handbook_files:

        page_lines = "\n".join(
            f"- {page}"
            for page in handbook_files
        )

        reply += (
            "\n\nRelevant handbook page(s):\n"
            f"{page_lines}"
        )

    # Keep the final student reply concise.
    # Retrieved handbook text is displayed separately by app.py.

    if (
        reasons
        and needs_alternative(reasons)
        and alternatives
    ):

        code, title = alternatives[0]

        reply += (
            "\n\nYou could instead consider "
            f"{code} - {title}."
        )

    if "waivers.md" in handbook_files:

        reply += (
            "\n\nA waiver may be possible. "
            "The course leader decides whether "
            "a waiver can be approved. "
            "It does not automatically approve enrolment."
        )

    return reply


# ============================================================
# 6. CLEAN AI RESPONSE
# ============================================================

def clean_ai_response(response):

    response = (
        response or ""
    ).strip()

    if (
        response.startswith('"')
        and response.endswith('"')
    ):

        response = response[1:-1].strip()

    bad_sections = [
        "IMPORTANT ARCHITECTURE:",
        "RULES:",
        "PREVIOUS RESPONSE FAILED VALIDATION.",
        "REASONS FOUND BY PYTHON:",
        "HANDBOOK PAGES:",
        "HANDBOOK TEXT:"
    ]

    for section in bad_sections:

        if section in response:

            response = response.split(
                section,
                1
            )[0].strip()

    return response


# ============================================================
# 7. ASK AI
# ============================================================

def ask_ai(
    reasons,
    handbook_text,
    handbook_files,
    alternatives
):
    """
    Generate one AI response.

    We deliberately do only ONE AI attempt.
    If it fails validation, generate_reply() immediately
    uses the safe deterministic response instead of making
    another slow model call.
    """
    load_reply_model()


    reasons = reasons or []
    handbook_files = handbook_files or []
    alternatives = normalize_alternatives(
        alternatives
    )

    reasons_text = "\n".join(
        f"- {reason}"
        for reason in reasons
    )

    pages_text = "\n".join(
        f"- {filename}"
        for filename in handbook_files
    )

    alternative_text = ""

    if alternatives:

        alternative_lines = [
            f"- {code} - {title}"
            for code, title in alternatives
        ]

        alternative_text = (
            "\n".join(alternative_lines)
        )

    system_message = """
You are a student support assistant.

Python has already made the enrolment decision.
Do NOT make a new decision.

Write only a short student-facing reply.

STRICT RULES:
- Copy every Python reason EXACTLY as written.
- Each Python reason must appear as a complete line in the final reply.
- Do not paraphrase, rewrite, shorten, or reinterpret any Python reason.
- Never replace a course code inside a reason with a course name or another word.
- Mention every supplied handbook filename EXACTLY.
- Use the handbook content only as supporting guidance.
- Do not invent facts, numbers, dates, or course codes.
- If an alternative is supplied, mention the exact alternative.
- If waivers.md is supplied, explain that the course leader decides whether a waiver is approved.
- Never say enrolment is approved.
- Keep the reply concise.
"""

    user_message = (
        "PYTHON VERIFIED REASONS:\n"
        f"{reasons_text if reasons_text else 'No blocking reason.'}"
        "\n\n"
        "HANDBOOK FILES:\n"
        f"{pages_text if pages_text else 'None'}"
        "\n\n"
        "RETRIEVED HANDBOOK CONTENT:\n"
        f"{handbook_text if handbook_text else 'None'}"
        "\n\n"
        "PYTHON VERIFIED ALTERNATIVES:\n"
        f"{alternative_text if alternative_text else 'None'}"
        "\n\n"
        "Write only the final student-facing reply."
    )

    messages = [
        {
            "role": "system",
            "content": system_message
        },
        {
            "role": "user",
            "content": user_message
        }
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        prompt,
        return_tensors="pt"
    )

    print("AI is writing the reply...")

    outputs = model.generate(
        **inputs,
        max_new_tokens=120,
        do_sample=False
    )

    new_tokens = outputs[0][
        inputs["input_ids"].shape[1]:
    ]

    response = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    ).strip()

    response = clean_ai_response(
        response
    )

    print("AI finished writing the reply.")

    return response


# ============================================================
# 8. VALIDATE FINAL REPLY
# ============================================================

def validate_reply(
    reply,
    reasons,
    handbook_files,
    handbook_text,
    alternatives
):

    alternatives = normalize_alternatives(
        alternatives
    )

    valid, error = check_reasons(
        reply,
        reasons
    )

    if not valid:
        return False, error

    valid, error = check_handbook_pages(
        reply,
        handbook_files
    )

    if not valid:
        return False, error

    allowed_text = (
        "\n".join(reasons or [])
        + "\n"
        + (handbook_text or "")
    )

    for code, title in alternatives or []:

        allowed_text += (
            f"\n{code}\n{title}"
        )

    valid, error = check_numbers_and_codes(
        reply,
        allowed_text
    )

    if not valid:
        return False, error

    valid, error = check_waiver_safety(
        reply
    )

    if not valid:
        return False, error

    if needs_alternative(reasons):

        if alternatives:

            valid, error = check_alternative(
                reply,
                alternatives
            )

            if not valid:
                return False, error

    return True, ""


# ============================================================
# 9. MAIN GENERATE FUNCTION
# ============================================================

def generate_reply(
    reasons,
    handbook=None,
    pages=None,
    alternatives=None,
    handbook_content=None,
    handbook_files=None
):
    """
    Generate and validate the final reply.

    Compatible with both:
        handbook=...
        pages=...

    and:
        handbook_content=...
        handbook_files=...

    Returns:
        (reply, source)

    source is either:
        "AI"
        "SAFE"
    """

    global last_ai_response, last_ai_validation_error

    # Reset debug values for this request.
    last_ai_response = ""
    last_ai_validation_error = ""

    # Correct alias handling.
    if handbook is None:
        handbook = handbook_content

    if pages is None:
        pages = handbook_files

    reasons = reasons or []
    pages = pages or []
    alternatives = normalize_alternatives(
        alternatives
    )

    # Use retrieved RAG content when app.py supplies it.
    # Only load local handbook files if no content was supplied.
    if handbook is None:

        handbook_text = build_handbook_text(
            pages
        )

    elif isinstance(handbook, dict):

        # search.py returns a dictionary by filename.
        handbook_text = "\n\n".join(
            f"--- {filename} ---\n{text}"
            for filename, text in handbook.items()
        )

    else:

        handbook_text = str(handbook)

    print()
    print("AI ATTEMPT")

    reply = ask_ai(
        reasons=reasons,
        handbook_text=handbook_text,
        handbook_files=pages,
        alternatives=alternatives
    )

    # Keep the raw model output so app.py can show it in the UI.
    last_ai_response = reply

    print()
    print("AI RESPONSE:")
    print(reply)

    valid, error = validate_reply(
        reply=reply,
        reasons=reasons,
        handbook_files=pages,
        handbook_text=handbook_text,
        alternatives=alternatives
    )

    if valid:

        print()
        print("AI RESPONSE PASSED VALIDATION.")

        return reply, "AI"

    # No second expensive generation.
    # Use the deterministic safe answer immediately.
    last_ai_validation_error = error

    print()
    print(
        f"AI RESPONSE FAILED VALIDATION: {error}"
    )

    print(
        "Using safe verified response."
    )

    safe_reply = fallback_reply(
        reasons,
        pages,
        alternatives,
        handbook_text=handbook_text
    )

    return safe_reply, "SAFE"


# ============================================================
# 10. TASK 9 TEST CASES
# ============================================================

TESTS = {

    "R1": {
        "student_id": "S-104",
        "course": "CS201",
        "reasons": [
            "CS101 prerequisite not completed"
        ],
        "handbook": [
            "prerequisites.md",
            "advice.md"
        ],
        "alternatives": [
            ("MA150", "Statistics")
        ]
    },

    "R2": {
        "student_id": "S-101",
        "course": "CS310",
        "reasons": [
            "course is full, 25 of 25"
        ],
        "handbook": [
            "capacity.md",
            "advice.md"
        ],
        "alternatives": [
            ("CS101", "Programming Foundations"),
            ("CS201", "Algorithms"),
            ("CS301", "Machine Learning"),
            ("DS220", "Data Visualisation")
        ]
    },

    "R3": {
        "student_id": "S-103",
        "course": "CS202",
        "reasons": [
            "clashes with MA150 Wed 14:00"
        ],
        "handbook": [
            "timetable.md"
        ],
        "alternatives": []
    },

    "R4": {
        "student_id": "S-102",
        "course": "CS301",
        "reasons": [
            "fees are unpaid",
            "would be 65 credits, limit 60"
        ],
        "handbook": [
            "fees.md",
            "credit_limit.md"
        ],
        "alternatives": []
    },

    "R5": {
        "student_id": "S-105",
        "course": "CS301",
        "reasons": [
            "CS201 grade 48, needs 55"
        ],
        "handbook": [
            "prerequisites.md",
            "advice.md",
            "waivers.md"
        ],
        "alternatives": [
            ("CS101", "Programming Foundations"),
            ("CS201", "Algorithms"),
            ("CS202", "Databases"),
            ("DS220", "Data Visualisation"),
            ("MA150", "Statistics")
        ]
    },

    "R6": {
        "student_id": "S-106",
        "course": "DS220",
        "reasons": [],
        "handbook": [
            "advice.md"
        ],
        "alternatives": []
    }
}


# ============================================================
# 11. TASK 9 TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("TASK 9 - TEST ALL SIX REQUESTS")
    print("=" * 70)

    passed = 0
    safe_count = 0

    for test_id, test in TESTS.items():

        print()
        print("=" * 70)
        print(f"TESTING {test_id}")
        print("=" * 70)

        print()
        print("Student ID:")
        print(test["student_id"])

        print()
        print("Requested course:")
        print(test["course"])

        print()
        print("Rule reasons:")

        if test["reasons"]:

            for reason in test["reasons"]:
                print(f"- {reason}")

        else:
            print("- None")

        print()
        print("Handbook pages:")

        for page in test["handbook"]:
            print(f"- {page}")

        final_reply, source = generate_reply(
            reasons=test["reasons"],
            handbook_files=test["handbook"],
            alternatives=test["alternatives"]
        )

        handbook_text = build_handbook_text(
            test["handbook"]
        )

        final_valid, final_error = validate_reply(
            reply=final_reply,
            reasons=test["reasons"],
            handbook_files=test["handbook"],
            handbook_text=handbook_text,
            alternatives=test["alternatives"]
        )

        print()
        print("FINAL REPLY:")
        print(final_reply)

        print()
        print(f"SOURCE: {source}")

        if final_valid:

            passed += 1
            print("FINAL VALIDATION: PASS")

        else:

            print(
                f"FINAL VALIDATION: FAIL - {final_error}"
            )

        if source == "SAFE":
            safe_count += 1

    print()
    print("=" * 70)
    print("TASK 9 FINAL SUMMARY")
    print("=" * 70)

    print(
        f"Final validated replies: {passed}/6"
    )

    print(
        f"Safe fallbacks used: {safe_count}/6"
    )

    print("=" * 70)
