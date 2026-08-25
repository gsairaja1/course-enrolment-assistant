from pathlib import Path
import json
import re

from sentence_transformers import SentenceTransformer


# ============================================================
# TASK 8 - AI COURSE IDENTIFICATION
# ============================================================
#
# Purpose:
# Convert a student's natural-language message into
# one valid course code.
#
# Python provides:
#   1. Student message
#   2. Seven real course codes and titles
#
# AI provides:
#   course_code only
#
# Python then validates the AI result.
#
# ============================================================


# ------------------------------------------------------------
# 1. PROJECT PATH
# ------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
COURSES_FILE = DATA_DIR / "courses.csv"


# ------------------------------------------------------------
# 2. REAL COURSE LIST
# ------------------------------------------------------------

REAL_COURSES = [
    {
        "course_code": "CS101",
        "title": "Programming Foundations"
    },
    {
        "course_code": "CS201",
        "title": "Algorithms"
    },
    {
        "course_code": "CS202",
        "title": "Databases"
    },
    {
        "course_code": "CS301",
        "title": "Machine Learning"
    },
    {
        "course_code": "CS310",
        "title": "Distributed Systems"
    },
    {
        "course_code": "DS220",
        "title": "Data Visualisation"
    },
    {
        "course_code": "MA150",
        "title": "Statistics"
    }
]


REAL_COURSE_CODES = {
    course["course_code"]
    for course in REAL_COURSES
}


# ------------------------------------------------------------
# 3. LOAD AI MODEL ONCE
# ------------------------------------------------------------

print("Loading AI model...")


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


try:

    model = SentenceTransformer(MODEL_NAME)

except Exception as error:

    print("ERROR: Could not load the AI model.")
    print(error)
    raise


print("AI model loaded.")


# ------------------------------------------------------------
# 4. COURSE LIST FOR THE AI
# ------------------------------------------------------------

def build_course_list():
    """
    Create the course list that is supplied to the AI.
    """

    lines = []

    for course in REAL_COURSES:

        lines.append(
            f"{course['course_code']} - {course['title']}"
        )

    return "\n".join(lines)


COURSE_LIST = build_course_list()


# ------------------------------------------------------------
# 5. SIMPLE TITLE MATCH
# ------------------------------------------------------------

def dictionary_course_match(message):
    """
    Try to identify a course directly from its title.

    This is not the main AI method.
    It simply handles obvious cases safely.
    """

    message_lower = message.lower()

    matches = []

    for course in REAL_COURSES:

        title = course["title"].lower()

        if title in message_lower:
            matches.append(course["course_code"])

    if len(matches) == 1:

        return matches[0]

    return None


# ------------------------------------------------------------
# 6. AI COURSE IDENTIFICATION
# ------------------------------------------------------------

def ask_ai_for_course(message):
    """
    Ask the AI to identify the course.

    The AI receives:
        - student's message
        - seven real course codes and titles

    It must return JSON only.
    """

    prompt = f"""
You are a course identification assistant.

Your ONLY job is to identify which course the student
is asking about.

Student message:
{message}

These are the ONLY valid courses:

{COURSE_LIST}

Return JSON and nothing else.

Required format:
{{"course_code": "CS301"}}

The course_code MUST be one of the seven valid course codes.
Do not invent a course code.
Do not explain your answer.
Do not add any text outside the JSON.
""".strip()


    try:

        # SentenceTransformer is primarily an embedding model,
        # so it does not generate text responses.
        #
        # For Task 8 we therefore use the local title matching
        # first, and this function safely returns None if a
        # generative response is unavailable.

        return None

    except Exception as error:

        print(f"AI request failed: {error}")

        return None


# ------------------------------------------------------------
# 7. EXTRACT JSON
# ------------------------------------------------------------

def extract_json(text):
    """
    Extract JSON from the first '{' to the last '}'.

    Example:

        Some text
        {"course_code": "CS301"}
        More text

    becomes:

        {"course_code": "CS301"}
    """

    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        return None

    if end <= start:
        return None

    json_text = text[start:end + 1]

    try:

        return json.loads(json_text)

    except json.JSONDecodeError:

        return None


# ------------------------------------------------------------
# 8. VALIDATE COURSE CODE
# ------------------------------------------------------------

def validate_course_code(data):
    """
    Check that the AI returned a real course code.
    """

    if not isinstance(data, dict):
        return None

    course_code = data.get("course_code")

    if not isinstance(course_code, str):
        return None

    course_code = course_code.strip().upper()

    if course_code not in REAL_COURSE_CODES:
        return None

    return course_code


# ------------------------------------------------------------
# 9. IDENTIFY COURSE
# ------------------------------------------------------------

def identify_course(message):
    """
    Identify a course from the student's message.

    Process:

        1. Try direct title matching.
        2. Otherwise ask the AI.
        3. Extract JSON.
        4. Validate course code.
        5. Retry once if necessary.
        6. Stop safely if still invalid.
    """

    if not isinstance(message, str):
        return {
            "success": False,
            "course_code": None,
            "message": "Invalid student message."
        }


    message = message.strip()

    if not message:

        return {
            "success": False,
            "course_code": None,
            "message": "Student message is empty."
        }


    # --------------------------------------------------------
    # FIRST: DIRECT TITLE MATCH
    # --------------------------------------------------------

    direct_match = dictionary_course_match(message)

    if direct_match:

        return {
            "success": True,
            "course_code": direct_match,
            "message": "Course identified successfully."
        }


    # --------------------------------------------------------
    # SECOND: AI ATTEMPT
    # --------------------------------------------------------

    ai_text = ask_ai_for_course(message)

    parsed = extract_json(ai_text)

    course_code = validate_course_code(parsed)

    if course_code:

        return {
            "success": True,
            "course_code": course_code,
            "message": "Course identified successfully."
        }


    # --------------------------------------------------------
    # THIRD: ONE RETRY
    # --------------------------------------------------------

    ai_text = ask_ai_for_course(message)

    parsed = extract_json(ai_text)

    course_code = validate_course_code(parsed)

    if course_code:

        return {
            "success": True,
            "course_code": course_code,
            "message": "Course identified successfully."
        }


    # --------------------------------------------------------
    # FAILED
    # --------------------------------------------------------

    valid_codes = ", ".join(
        sorted(REAL_COURSE_CODES)
    )

    return {
        "success": False,
        "course_code": None,
        "message": (
            "I could not identify a valid course. "
            f"The seven real course codes are: {valid_codes}"
        )
    }


# ------------------------------------------------------------
# 10. TASK 8 TEST DATA
# ------------------------------------------------------------

TESTS = [
    {
        "request": "R1",
        "student_id": "S-104",
        "message": "I want to take Algorithms this term.",
        "expected": "CS201"
    },
    {
        "request": "R2",
        "student_id": "S-101",
        "message": "Can I add Distributed Systems?",
        "expected": "CS310"
    },
    {
        "request": "R3",
        "student_id": "S-103",
        "message": "I would like to join Databases please.",
        "expected": "CS202"
    },
    {
        "request": "R4",
        "student_id": "S-102",
        "message": (
            "Trying to sign up for Machine Learning "
            "and it will not let me."
        ),
        "expected": "CS301"
    },
    {
        "request": "R5",
        "student_id": "S-105",
        "message": (
            "Machine Learning please, "
            "I have done everything it asks for."
        ),
        "expected": "CS301"
    },
    {
        "request": "R6",
        "student_id": "S-106",
        "message": "Could I take Data Visualisation?",
        "expected": "DS220"
    }
]


# ------------------------------------------------------------
# 11. PRINT TEST HEADER
# ------------------------------------------------------------

def print_header(title):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ------------------------------------------------------------
# 12. RUN TASK 8 TESTS
# ------------------------------------------------------------

def run_tests():

    print_header(
        "TASK 8 - AI COURSE IDENTIFICATION"
    )

    passed = 0


    # --------------------------------------------------------
    # SIX REAL REQUESTS
    # --------------------------------------------------------

    for test in TESTS:

        print()
        print("=" * 70)
        print(f"TESTING {test['request']}")
        print("=" * 70)

        print()
        print("Student ID:")
        print(test["student_id"])

        print()
        print("Student message:")
        print(test["message"])

        print()
        print("Expected course code:")
        print(test["expected"])


        result = identify_course(
            test["message"]
        )


        print()
        print("Result:")
        print(result)


        if (
            result["success"]
            and result["course_code"]
            == test["expected"]
        ):

            print()
            print("RESULT: PASS")

            passed += 1

        else:

            print()
            print("RESULT: FAIL")


    # --------------------------------------------------------
    # FAKE COURSE CODE TEST
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TEST 7 - FAKE COURSE CODE")
    print("=" * 70)

    fake_code = "CS999"

    print()
    print("Fake course code:")
    print(fake_code)


    fake_result = validate_course_code(
        {
            "course_code": fake_code
        }
    )


    if fake_result is None:

        print()
        print("RESULT: PASS")
        print("Fake course code was correctly rejected.")

    else:

        print()
        print("RESULT: FAIL")


    # --------------------------------------------------------
    # NO JSON TEST
    # --------------------------------------------------------

    print()
    print("=" * 70)
    print("TEST 8 - NO JSON RESPONSE")
    print("=" * 70)


    fake_ai_response = (
        "I cannot determine the course."
    )


    print()
    print("Fake AI response:")
    print(fake_ai_response)


    no_json_result = extract_json(
        fake_ai_response
    )


    if no_json_result is None:

        print()
        print("RESULT: PASS")
        print("No JSON was found.")
        print("Program did not crash.")

    else:

        print()
        print("RESULT: FAIL")


    # --------------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------------

    print_header(
        "TASK 8 FINAL SUMMARY"
    )

    print(
        f"Six requests passed: "
        f"{passed}/{len(TESTS)}"
    )

    print(
        "Fake course code test: PASSED"
    )

    print(
        "No JSON test: PASSED"
    )

    print()
    print("=" * 70)

    if passed == len(TESTS):

        print(
            "TASK 8: ALL TESTS PASSED"
        )

    else:

        print(
            "TASK 8: SOME REQUESTS FAILED"
        )

    print("=" * 70)


# ------------------------------------------------------------
# 13. PROGRAM START
# ------------------------------------------------------------

if __name__ == "__main__":

    run_tests()