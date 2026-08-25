from pathlib import Path
import re

from transformers import AutoTokenizer, AutoModelForCausalLM


# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

HANDBOOK_DIR = BASE_DIR / "data" / "handbook"

MODEL_NAME = "HuggingFaceTB/SmolLM2-1.7B-Instruct"


# ============================================================
# 2. LOAD AI MODEL
# ============================================================

print("Loading reply model...")
print("Loading tokenizer...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

print("Tokenizer loaded.")

print("Loading model...")

model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)

print("Reply model loaded.")


# ============================================================
# 3. LOAD HANDBOOK
# ============================================================

def load_handbook(filename):
    """
    Load one handbook Markdown file.
    """

    path = HANDBOOK_DIR / filename

    if not path.exists():
        raise FileNotFoundError(
            f"Handbook file not found: {filename}"
        )

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:
        return file.read()


def build_handbook_text(handbook_files):
    """
    Combine all required handbook pages.
    """

    parts = []

    for filename in handbook_files:

        text = load_handbook(filename)

        parts.append(
            f"--- {filename} ---\n{text}"
        )

    return "\n\n".join(parts)


# ============================================================
# 4. EXTRACT NUMBERS AND COURSE CODES
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


# ============================================================
# 5. CHECK REASONS
# ============================================================

def check_reasons(reply, reasons):

    reply_lower = reply.lower()

    for reason in reasons:

        if reason.lower() not in reply_lower:

            return False, (
                f"reason missing: {reason}"
            )

    return True, ""


# ============================================================
# 6. CHECK HANDBOOK PAGES
# ============================================================

def check_handbook_pages(
    reply,
    handbook_files
):

    reply_lower = reply.lower()

    for filename in handbook_files:

        if filename.lower() not in reply_lower:

            return False, (
                f"handbook page {filename} is missing"
            )

    return True, ""


# ============================================================
# 7. CHECK NUMBERS AND COURSE CODES
# ============================================================

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


# ============================================================
# 8. WAIVER SAFETY
# ============================================================

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

    has_authority = any(
        phrase in reply_lower
        for phrase in approval_phrases
    )

    if not has_authority:

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


# ============================================================
# 9. ALTERNATIVE COURSE CHECK
# ============================================================

def check_alternative(
    reply,
    alternatives
):

    if not alternatives:
        return True, ""

    reply_lower = reply.lower()

    for course_code, title in alternatives:

        if course_code.lower() in reply_lower:
            return True, ""

        if title.lower() in reply_lower:
            return True, ""

    return False, (
        "eligible alternative course is missing"
    )


def needs_alternative(reasons):

    reason_text = " ".join(reasons).lower()

    return (
        "full" in reason_text
        or "prerequisite" in reason_text
    )


# ============================================================
# 10. BUILD PYTHON-VERIFIED ALTERNATIVE
# ============================================================

def build_alternative_text(alternatives):

    if not alternatives:
        return ""

    code, title = alternatives[0]

    return (
        f"\nVerified alternative: "
        f"{code} - {title}."
    )


# ============================================================
# 11. CLEAN AI RESPONSE
# ============================================================

def clean_ai_response(response):

    response = response.strip()

    # Remove accidental quotation marks.
    if response.startswith('"') and response.endswith('"'):
        response = response[1:-1].strip()

    # Remove accidental instruction leakage.
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
# 12. ASK AI
# ============================================================

def ask_ai(
    reasons,
    handbook_text,
    handbook_files,
    alternatives,
    retry=False
):

    reasons_text = "\n".join(
        f"- {reason}"
        for reason in reasons
    )

    pages_text = "\n".join(
        f"- {filename}"
        for filename in handbook_files
    )

    alternative_text = build_alternative_text(
        alternatives
    )

    system_message = """
You are a student support assistant.

Python has already decided whether enrolment is blocked.

You must NOT make a new decision.

Write only a short student-facing explanation.

IMPORTANT:

- Use the exact reason text supplied by Python.
- Do not change the reason wording.
- Mention every supplied handbook filename.
- Explain briefly what the student should do next.
- Do not invent facts.
- Do not invent numbers.
- Do not invent course codes.
- If an alternative course is supplied, mention that exact alternative.
- If a waiver is mentioned, say that the course leader decides or approves it.
- Never say enrolment has been approved.
- Never say the student is approved.
- Keep the answer short.
"""

    if retry:

        system_message += """
The previous answer failed validation.

Write a completely new answer.

Make sure every Python reason appears exactly.
Make sure every handbook filename appears exactly.
Do not add any new numbers or course codes.
"""

    user_message = (
        "PYTHON REASONS:\n"
        f"{reasons_text if reasons_text else 'No blocking reason.'}"
        "\n\n"
        "HANDBOOK PAGES:\n"
        f"{pages_text}"
        "\n\n"
        "HANDBOOK CONTENT:\n"
        f"{handbook_text}"
        "\n\n"
        "PYTHON-VERIFIED ALTERNATIVE:"
        f"{alternative_text}"
        "\n\n"
        "Write only the student-facing reply."
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
# 13. VALIDATE RESPONSE
# ============================================================

def validate_reply(
    reply,
    reasons,
    handbook_files,
    handbook_text,
    alternatives
):

    # --------------------------------------------------------
    # CHECK 1 - EVERY REASON
    # --------------------------------------------------------

    valid, error = check_reasons(
        reply,
        reasons
    )

    if not valid:
        return False, error


    # --------------------------------------------------------
    # CHECK 2 - EVERY HANDBOOK PAGE
    # --------------------------------------------------------

    valid, error = check_handbook_pages(
        reply,
        handbook_files
    )

    if not valid:
        return False, error


    # --------------------------------------------------------
    # CHECK 3 - NUMBERS AND COURSE CODES
    # --------------------------------------------------------

    allowed_text = (
        "\n".join(reasons)
        + "\n"
        + handbook_text
    )

    for code, title in alternatives:

        allowed_text += (
            f"\n{code}\n{title}"
        )

    valid, error = check_numbers_and_codes(
        reply,
        allowed_text
    )

    if not valid:
        return False, error


    # --------------------------------------------------------
    # CHECK 4 - WAIVER
    # --------------------------------------------------------

    valid, error = check_waiver_safety(
        reply
    )

    if not valid:
        return False, error


    # --------------------------------------------------------
    # CHECK 5 - ALTERNATIVE
    # --------------------------------------------------------

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
# 14. DETERMINISTIC SAFE FALLBACK
# ============================================================

def fallback_reply(
    reasons,
    handbook_files,
    alternatives
):
    """
    Safe deterministic fallback.

    This response does not depend on the AI.
    It uses only facts supplied by Python.
    """

    # --------------------------------------------------------
    # REASONS
    # --------------------------------------------------------

    if reasons:

        reason_lines = "\n".join(
            f"- {reason}"
            for reason in reasons
        )

    else:

        reason_lines = "No blocking reason."


    # --------------------------------------------------------
    # HANDBOOK PAGES
    # --------------------------------------------------------

    page_lines = "\n".join(
        f"- {page}"
        for page in handbook_files
    )


    # --------------------------------------------------------
    # START RESPONSE
    # --------------------------------------------------------

    if reasons:

        reply = (
            "The following issues prevent enrolment:\n"
            f"{reason_lines}\n\n"
            "Relevant handbook page(s):\n"
            f"{page_lines}"
        )

    else:

        reply = (
            "There are no blocking reasons for enrolment.\n\n"
            "Relevant handbook page(s):\n"
            f"{page_lines}"
        )


    # --------------------------------------------------------
    # VERIFIED ALTERNATIVE
    # --------------------------------------------------------

    if (
        reasons
        and needs_alternative(reasons)
        and alternatives
    ):

        code, title = alternatives[0]

        reply += (
            "\n\n"
            "You could instead consider the "
            f"eligible course {code} - {title}."
        )


    # --------------------------------------------------------
    # WAIVER SAFETY
    # --------------------------------------------------------

    if "waivers.md" in handbook_files:

        reply += (
            "\n\n"
            "You may ask for a waiver. "
            "The course leader decides whether "
            "a waiver can be approved. "
            "Enrolment is not approved automatically."
        )


    return reply

# ============================================================
# 15. GENERATE FINAL REPLY
# ============================================================

def generate_reply(
    reasons,
    handbook_files,
    alternatives
):

    handbook_text = build_handbook_text(
        handbook_files
    )


    # ========================================================
    # FIRST AI ATTEMPT
    # ========================================================

    print()
    print("FIRST AI ATTEMPT")

    reply = ask_ai(
        reasons=reasons,
        handbook_text=handbook_text,
        handbook_files=handbook_files,
        alternatives=alternatives,
        retry=False
    )

    print()
    print("AI RESPONSE:")
    print(reply)

    valid, error = validate_reply(
        reply=reply,
        reasons=reasons,
        handbook_files=handbook_files,
        handbook_text=handbook_text,
        alternatives=alternatives
    )

    if valid:

        print()
        print("FIRST RESPONSE PASSED VALIDATION.")

        return reply, True


    # ========================================================
    # RETRY
    # ========================================================

    print()
    print(
        f"Validation failed: {error}"
    )

    print()
    print("FIRST RESPONSE FAILED.")
    print("Trying one rewrite...")

    reply = ask_ai(
        reasons=reasons,
        handbook_text=handbook_text,
        handbook_files=handbook_files,
        alternatives=alternatives,
        retry=True
    )

    print()
    print("AI RETRY RESPONSE:")
    print(reply)

    valid, error = validate_reply(
        reply=reply,
        reasons=reasons,
        handbook_files=handbook_files,
        handbook_text=handbook_text,
        alternatives=alternatives
    )

    if valid:

        print()
        print("SECOND RESPONSE PASSED VALIDATION.")

        return reply, True


    # ========================================================
    # SAFE FALLBACK
    # ========================================================

    print()
    print(
        f"SECOND RESPONSE FAILED: {error}"
    )

    print()
    print("Showing safe fallback.")

    return (
        fallback_reply(
            reasons,
            handbook_files,
            alternatives
        ),
        False
    )


# ============================================================
# 16. TASK 9 TEST CASES
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
# 17. MAIN TASK 9 TEST
# ============================================================

if __name__ == "__main__":

    print()
    print("=" * 70)
    print("TASK 9 - TEST ALL SIX REQUESTS")
    print("=" * 70)

    passed = 0
    fallback_count = 0

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

                print(
                    f"- {reason}"
                )

        else:

            print("- None")

        print()
        print("Handbook pages:")

        for page in test["handbook"]:

            print(
                f"- {page}"
            )

        if test["alternatives"]:

            print()
            print(
                "Python-verified eligible alternatives:"
            )

            for code, title in test["alternatives"]:

                print(
                    f"- {code} - {title}"
                )

        final_reply, ai_passed = generate_reply(
            reasons=test["reasons"],
            handbook_files=test["handbook"],
            alternatives=test["alternatives"]
        )

        print()
        print("=" * 70)
        print(f"FINAL REPLY - {test_id}")
        print("=" * 70)

        print(final_reply)

        # ----------------------------------------------------
        # IMPORTANT:
        # The final reply is validated one more time.
        # ----------------------------------------------------

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

        if final_valid:

            passed += 1

            print()
            print("FINAL VALIDATION: PASS")

        else:

            fallback_count += 1

            print()
            print(
                f"FINAL VALIDATION FAILED: {final_error}"
            )

            # Absolute final safety net.
            final_reply = fallback_reply(
                test["reasons"],
                test["handbook"],
                test["alternatives"]
            )

            print()
            print("FINAL SAFE REPLY:")
            print(final_reply)


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print()
    print("=" * 70)
    print("TASK 9 FINAL SUMMARY")
    print("=" * 70)

    print(
        f"Final validated replies: {passed}/6"
    )

    print(
        f"Fallbacks used: {fallback_count}/6"
    )

    print("=" * 70)

    if passed == 6:

        print(
            "TASK 9: ALL SIX REPLIES PASSED."
        )

    else:

        print(
            "TASK 9: SAFE FALLBACKS WERE USED "
            "WHERE AI OUTPUT FAILED."
        )

    print("=" * 70)