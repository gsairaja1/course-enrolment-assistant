from pathlib import Path
import json
import re

from transformers import AutoTokenizer, AutoModelForCausalLM


# ============================================================
# 1. PROJECT PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# 2. GENERATIVE LLM
# ============================================================

MODEL_NAME = "HuggingFaceTB/SmolLM2-1.7B-Instruct"

print("Loading course identification LLM...")

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_NAME
)

model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME
)

print("Course identification LLM loaded.")


# ============================================================
# 3. REAL COURSE DATA
# ============================================================

REAL_COURSES = {
    "CS101": "Programming Foundations",
    "CS201": "Algorithms",
    "CS202": "Databases",
    "CS301": "Machine Learning",
    "CS310": "Distributed Systems",
    "DS220": "Data Visualisation",
    "MA150": "Statistics",
}

REAL_COURSE_CODES = set(
    REAL_COURSES.keys()
)


# ============================================================
# 4. COURSE ALIASES
# ============================================================

COURSE_ALIASES = {

    # Machine Learning
    "ml": "CS301",
    "machine learning": "CS301",

    # Algorithms
    "algorithms": "CS201",
    "algorithm": "CS201",

    # Databases
    "databases": "CS202",
    "database": "CS202",

    # Distributed Systems
    "distributed systems": "CS310",
    "distributed system": "CS310",

    # Data Visualisation
    "data visualisation": "DS220",
    "data visualization": "DS220",

    # Programming Foundations
    "programming foundations": "CS101",

    # Statistics
    "statistics": "MA150",
}


# ============================================================
# 5. DIRECT COURSE MATCH
# ============================================================

def direct_course_match(message):
    """
    Try to find a course directly from the student's message.

    Checks:
    1. Course code
    2. Exact course title
    3. Alias
    """

    text = message.lower().strip()

    # --------------------------------------------------------
    # 5.1 CHECK COURSE CODE
    # --------------------------------------------------------

    for code in REAL_COURSE_CODES:

        if re.search(
            rf"\b{re.escape(code.lower())}\b",
            text
        ):
            return code

    # --------------------------------------------------------
    # 5.2 CHECK FULL COURSE TITLE
    # --------------------------------------------------------

    for code, title in REAL_COURSES.items():

        if title.lower() in text:
            return code

    # --------------------------------------------------------
    # 5.3 CHECK COURSE ALIAS
    # --------------------------------------------------------

    for alias in sorted(
        COURSE_ALIASES,
        key=len,
        reverse=True
    ):

        if re.search(
            rf"\b{re.escape(alias)}\b",
            text
        ):
            return COURSE_ALIASES[alias]

    # Nothing found
    return None


# ============================================================
# 6. CREATE COURSE LIST FOR THE LLM
# ============================================================

COURSE_LIST = "\n".join(
    f"{code} - {title}"
    for code, title in REAL_COURSES.items()
)


# ============================================================
# 7. ASK THE LLM TO IDENTIFY THE COURSE
# ============================================================

def ask_llm_for_course(message):
    """
    Ask SmolLM2 to identify the course.

    The model is allowed to return null when
    the course cannot be identified confidently.
    """

    prompt = f"""
You are a course identification assistant.

Your ONLY job is to identify which course the student
is asking about.

Do NOT answer the student's question.
Do NOT explain.
Do NOT make an enrolment decision.

Student message:
{message}

Valid courses:
{COURSE_LIST}

Rules:

1. Choose ONLY from the valid courses listed above.
2. Understand indirect descriptions of courses.
3. If the student clearly describes a course, return its course code.
4. If the student does not clearly identify a course,
   return null.
5. Do NOT guess.
6. Do NOT invent a course code.
7. Return JSON only.

Examples:

"Can I take ML?"
-> {{"course_code": "CS301"}}

"I want to learn predictive models"
-> {{"course_code": "CS301"}}

"I want to learn how databases store information"
-> {{"course_code": "CS202"}}

"I want to study algorithms"
-> {{"course_code": "CS201"}}

"I want to learn basic programming"
-> {{"course_code": "CS101"}}

"I want to understand systems running across multiple computers"
-> {{"course_code": "CS310"}}

"I want to create charts and understand data visually"
-> {{"course_code": "DS220"}}

"I want to study probability and statistics"
-> {{"course_code": "MA150"}}

"Tell me something interesting"
-> {{"course_code": null}}

"What courses are available?"
-> {{"course_code": null}}

"I need help with my enrolment"
-> {{"course_code": null}}

Return exactly this format:

{{"course_code": "CS301"}}

OR

{{"course_code": null}}
""".strip()

    messages = [
        {
            "role": "user",
            "content": prompt
        }
    ]

    formatted_prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )

    inputs = tokenizer(
        formatted_prompt,
        return_tensors="pt"
    )

    print("Asking course identification LLM...")

    outputs = model.generate(
        **inputs,
        max_new_tokens=50,
        do_sample=False
    )

    # Remove original prompt tokens
    new_tokens = outputs[0][
        inputs["input_ids"].shape[1]:
    ]

    response = tokenizer.decode(
        new_tokens,
        skip_special_tokens=True
    ).strip()

    print("Course identification response:")
    print(response)

    return response


# ============================================================
# 8. EXTRACT JSON FROM LLM RESPONSE
# ============================================================

def extract_json(text):

    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    try:

        json_text = text[
            start:end + 1
        ]

        return json.loads(
            json_text
        )

    except json.JSONDecodeError:

        return None


# ============================================================
# 9. VALIDATE COURSE CODE
# ============================================================

def validate_course_code(data):
    """
    Validate the LLM output.

    Returns:
        Valid course code
        OR
        None when no valid course was identified.
    """

    # Output must be a dictionary
    if not isinstance(data, dict):
        return None

    # Get course_code
    code = data.get("course_code")

    # --------------------------------------------------------
    # IMPORTANT:
    # null means:
    # "The LLM could not confidently identify a course."
    # --------------------------------------------------------

    if code is None:
        return None

    # Course code must be a string
    if not isinstance(code, str):
        return None

    # Clean the code
    code = code.strip().upper()

    # Check against real courses
    if code not in REAL_COURSE_CODES:
        return None

    return code


# ============================================================
# 10. MAIN COURSE IDENTIFICATION FUNCTION
# ============================================================

def identify_course(message):
    """
    Convert a natural-language student message
    into a valid course code.

    Flow:

        Student message
              ↓
        Direct matching
              ↓
        If not found
              ↓
            LLM
              ↓
        Extract JSON
              ↓
        Validate code
              ↓
        Return course
    """

    # --------------------------------------------------------
    # STEP 1: Validate input
    # --------------------------------------------------------

    if not isinstance(message, str):

        return {
            "success": False,
            "course_code": None,
            "course_title": None
        }

    message = message.strip()

    if not message:

        return {
            "success": False,
            "course_code": None,
            "course_title": None
        }

    # --------------------------------------------------------
    # STEP 2: DIRECT MATCHING
    # --------------------------------------------------------

    code = direct_course_match(message)

    if code:

        return {
            "success": True,
            "course_code": code,
            "course_title": REAL_COURSES[code]
        }

    # --------------------------------------------------------
    # STEP 3: LLM FALLBACK
    # --------------------------------------------------------

    try:

        llm_response = ask_llm_for_course(
            message
        )

        # ----------------------------------------------------
        # STEP 4: EXTRACT JSON
        # ----------------------------------------------------

        parsed = extract_json(
            llm_response
        )

        # ----------------------------------------------------
        # STEP 5: VALIDATE COURSE
        # ----------------------------------------------------

        code = validate_course_code(
            parsed
        )

        # ----------------------------------------------------
        # STEP 6: VALID COURSE FOUND
        # ----------------------------------------------------

        if code:

            return {
                "success": True,
                "course_code": code,
                "course_title": REAL_COURSES[code]
            }

    except Exception as error:

        print(
            f"Course LLM failed: {error}"
        )

    # --------------------------------------------------------
    # STEP 7: COURSE NOT IDENTIFIED
    # --------------------------------------------------------

    return {
        "success": False,
        "course_code": None,
        "course_title": None
    }
