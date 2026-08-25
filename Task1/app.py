from pathlib import Path
import json
import re

import requests
import streamlit as st

# --------------------------------------------------
# OPTIONAL PROJECT MODULES
# --------------------------------------------------

try:
    from ai import identify_course as ai_identify_course
except Exception:
    ai_identify_course = None

try:
    from reply import generate_reply as ai_generate_reply
except Exception:
    ai_generate_reply = None

try:
    from search import search as handbook_search
except Exception:
    handbook_search = None


# --------------------------------------------------
# PAGE SETUP
# --------------------------------------------------

st.set_page_config(
    page_title="Course Enrolment Assistant",
    page_icon="🎓",
    layout="wide"
)


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# app.py is inside Task1
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
HANDBOOK_DIR = DATA_DIR / "handbook"
REQUESTS_DIR = DATA_DIR / "requests"

API_URL = "http://127.0.0.1:8000"


# --------------------------------------------------
# COURSE DATA
# --------------------------------------------------

COURSES = {
    "CS101": "Programming Foundations",
    "CS201": "Algorithms",
    "CS202": "Databases",
    "CS301": "Machine Learning",
    "CS310": "Distributed Systems",
    "DS220": "Data Visualisation",
    "MA150": "Statistics",
}


# --------------------------------------------------
# TASK 10 EXPECTED DATA
# --------------------------------------------------

TASK10_REQUESTS = [
    {
        "id": "R1",
        "student_id": "S-104",
        "message": "I want to take Algorithms this term.",
        "expected_course": "CS201",
        "expected_reasons": [
            "CS101 prerequisite not completed"
        ],
        "expected_pages": [
            "prerequisites.md",
            "advice.md",
        ],
    },
    {
        "id": "R2",
        "student_id": "S-101",
        "message": "Can I add Distributed Systems?",
        "expected_course": "CS310",
        "expected_reasons": [
            "full, 25 of 25"
        ],
        "expected_pages": [
            "capacity.md",
            "advice.md",
        ],
    },
    {
        "id": "R3",
        "student_id": "S-103",
        "message": "I would like to join Databases please.",
        "expected_course": "CS202",
        "expected_reasons": [
            "clashes with MA150 Wed 14:00"
        ],
        "expected_pages": [
            "timetable.md",
        ],
    },
    {
        "id": "R4",
        "student_id": "S-102",
        "message": (
            "Trying to sign up for Machine Learning "
            "and it will not let me."
        ),
        "expected_course": "CS301",
        "expected_reasons": [
            "fees are unpaid",
            "would be 65 credits, limit 60",
        ],
        "expected_pages": [
            "fees.md",
            "credit_limit.md",
        ],
    },
    {
        "id": "R5",
        "student_id": "S-105",
        "message": (
            "Machine Learning please, "
            "I have done everything it asks for."
        ),
        "expected_course": "CS301",
        "expected_reasons": [
            "CS201 grade 48, needs 55"
        ],
        "expected_pages": [
            "prerequisites.md",
            "advice.md",
            "waivers.md",
        ],
    },
    {
        "id": "R6",
        "student_id": "S-106",
        "message": "Could I take Data Visualisation?",
        "expected_course": "DS220",
        "expected_reasons": [],
        "expected_pages": [
            "advice.md",
        ],
    },
]


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def api_get(endpoint):
    """
    Safely call the FastAPI backend.
    """

    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            timeout=30
        )

        try:
            data = response.json()
        except Exception:
            data = {}

        return response.status_code, data

    except requests.exceptions.ConnectionError:
        return None, {
            "error": (
                "Cannot connect to FastAPI. "
                "Start the backend with: "
                "uvicorn api:app --reload"
            )
        }

    except requests.exceptions.Timeout:
        return None, {
            "error": "The FastAPI server took too long to respond."
        }

    except Exception as error:
        return None, {
            "error": str(error)
        }


def load_handbook_text(filename):
    """
    Read one handbook markdown file.
    """

    path = HANDBOOK_DIR / filename

    if not path.exists():
        return ""

    try:
        return path.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        return ""


def get_handbook_pages(reasons):
    """
    Decide which handbook pages are relevant.

    This decision is made by Python rules,
    not by the AI.
    """

    pages = []

    for reason in reasons:

        lower = reason.lower()

        if "fee" in lower:
            if "fees.md" not in pages:
                pages.append("fees.md")

        if (
            "prerequisite" in lower
            or "grade" in lower
        ):
            if "prerequisites.md" not in pages:
                pages.append("prerequisites.md")

            if "advice.md" not in pages:
                pages.append("advice.md")

            # A prerequisite/grade problem may involve
            # the waiver guidance.
            if "grade" in lower:
                if "waivers.md" not in pages:
                    pages.append("waivers.md")

        if "full" in lower:
            if "capacity.md" not in pages:
                pages.append("capacity.md")

            if "advice.md" not in pages:
                pages.append("advice.md")

        if "clash" in lower:
            if "timetable.md" not in pages:
                pages.append("timetable.md")

        if "credit" in lower:
            if "credit_limit.md" not in pages:
                pages.append("credit_limit.md")

    # No blocking reason
    if not reasons:
        pages.append("advice.md")

    return pages


def get_handbook_content(pages):
    """
    Return the actual text of the selected handbook pages.
    """

    content = {}

    for page in pages:

        text = load_handbook_text(page)

        if text:
            content[page] = text

    return content


def get_eligible_alternatives(
    student_id,
    blocked_course
):
    """
    Use the Python enrolment rules to find alternatives.

    The AI is NOT allowed to decide eligibility.
    """

    alternatives = []

    for code in COURSES:

        if code == blocked_course:
            continue

        status, data = api_get(
            f"/check/{student_id}/{code}"
        )

        if status != 200:
            continue

        result = data.get("data", {})

        if result.get("allowed") is True:
            alternatives.append({
                "course_code": code,
                "title": COURSES[code]
            })

    return alternatives


def identify_course_fallback(message):
    """
    Non-AI fallback.

    This is used only if the AI module cannot be imported
    or cannot identify the course.
    """

    text = message.lower()

    # Exact course code
    for code in COURSES:

        if re.search(
            rf"\b{re.escape(code.lower())}\b",
            text
        ):
            return code

    # Course titles
    for code, title in COURSES.items():

        if title.lower() in text:
            return code

    # Small wording fallback
    aliases = {
        "algorithms": "CS201",
        "programming foundations": "CS101",
        "databases": "CS202",
        "machine learning": "CS301",
        "distributed systems": "CS310",
        "data visualisation": "DS220",
        "data visualization": "DS220",
        "statistics": "MA150",
    }

    for phrase, code in aliases.items():

        if phrase in text:
            return code

    return None


def identify_course(message):
    """
    Use Task 8 AI first.

    If the imported AI function is unavailable,
    use the safe local fallback.
    """

    if ai_identify_course is not None:

        try:

            result = ai_identify_course(
                message,
                list(COURSES.items())
            )

            # Support dictionary result
            if isinstance(result, dict):

                code = result.get("course_code")

                if code in COURSES:
                    return code

            # Support direct string result
            if isinstance(result, str):

                if result in COURSES:
                    return result

        except Exception:
            pass

    return identify_course_fallback(message)


def validate_reply(
    reply,
    reasons,
    pages,
    alternatives=None
):
    """
    Validate the final response.

    Checks:
    1. Every rule reason appears.
    2. Every number/course code is allowed.
    3. Required handbook pages are named.
    4. Waiver mentions must include approval authority.
    """

    if not reply:
        return False, "Reply is empty."

    reply_lower = reply.lower()

    # --------------------------------------------------
    # 1. Every reason must appear
    # --------------------------------------------------

    for reason in reasons:

        if reason.lower() not in reply_lower:

            # Allow a normalized whitespace comparison
            normalized_reply = " ".join(
                reply_lower.split()
            )

            normalized_reason = " ".join(
                reason.lower().split()
            )

            if normalized_reason not in normalized_reply:

                return (
                    False,
                    f"Missing reason: {reason}"
                )

    # --------------------------------------------------
    # 2. Required handbook pages
    # --------------------------------------------------

    for page in pages:

        if page.lower() not in reply_lower:

            return (
                False,
                f"Missing handbook page: {page}"
            )

    # --------------------------------------------------
    # 3. Allowed course codes
    # --------------------------------------------------

    mentioned_codes = re.findall(
        r"\b[A-Z]{2,4}\d{3}\b",
        reply.upper()
    )

    for code in mentioned_codes:

        if code not in COURSES:

            return (
                False,
                f"Unknown course code in reply: {code}"
            )

    # --------------------------------------------------
    # 4. Allowed numbers
    #
    # Extract all numeric values from reasons,
    # handbook pages and alternatives.
    # --------------------------------------------------

    allowed_numbers = set()

    for reason in reasons:

        for number in re.findall(
            r"\b\d+\b",
            reason
        ):
            allowed_numbers.add(number)

    for alternative in alternatives or []:

        code = alternative.get(
            "course_code",
            ""
        )

        for number in re.findall(
            r"\d+",
            code
        ):
            allowed_numbers.add(number)

    # Page names can contain no meaningful
    # student/course numeric data, so they are ignored.

    reply_numbers = re.findall(
        r"\b\d+\b",
        reply
    )

    for number in reply_numbers:

        if number not in allowed_numbers:

            return (
                False,
                f"Number not supplied to AI: {number}"
            )

    # --------------------------------------------------
    # 5. Waiver safety
    # --------------------------------------------------

    if "waiver" in reply_lower:

        approval_words = [
            "course leader",
            "department",
            "departmental",
            "academic office",
            "programme leader",
            "authorised",
            "authorized",
            "approver",
            "approval"
        ]

        if not any(
            word in reply_lower
            for word in approval_words
        ):

            return (
                False,
                "Waiver mentioned without approval authority."
            )

        # Never allow approval language
        unsafe_phrases = [
            "waiver approved",
            "enrolment approved",
            "approved for enrolment",
            "you are approved"
        ]

        for phrase in unsafe_phrases:

            if phrase in reply_lower:

                return (
                    False,
                    "Reply incorrectly records approval."
                )

    return True, "PASS"


def make_safe_reply(
    reasons,
    pages,
    alternatives=None
):
    """
    Deterministic fallback.

    This never invents facts.

    If waivers.md is relevant, the reply gives the
    safe approval-authority guidance required by the
    validation rules. It never claims that enrolment
    or a waiver has already been approved.
    """

    if reasons:

        lines = [
            "The following issues prevent enrolment:"
        ]

        for reason in reasons:
            lines.append(f"- {reason}")

    else:

        lines = [
            "There are no blocking reasons for enrolment."
        ]

    lines.append("")
    lines.append("Relevant handbook page(s):")

    for page in pages:
        lines.append(f"- {page}")

    if alternatives:

        lines.append("")

        lines.append(
            "Python-verified eligible alternative:"
            if len(alternatives) == 1
            else
            "Python-verified eligible alternatives:"
        )

        for alternative in alternatives[:5]:

            lines.append(
                f"- {alternative['course_code']} - "
                f"{alternative['title']}"
            )

    # --------------------------------------------------
    # WAIVER SAFETY
    # --------------------------------------------------
    # R5 includes waivers.md. If the fallback mentions
    # a waiver, it must also state who has authority
    # to approve it. Never claim approval has happened.
    # --------------------------------------------------

    if "waivers.md" in pages:

        lines.append("")

        lines.append(
            "You can ask the course leader about a waiver. "
            "The course leader must approve the waiver; "
            "this does not approve enrolment."
        )

    return "\n".join(lines)


def generate_reply(
    reasons,
    handbook_content,
    pages,
    alternatives=None
):
    """
    Generate a student-facing reply.

    The AI receives ONLY:
    - reasons
    - handbook text
    - handbook page names
    - Python-verified alternatives

    If AI generation is unavailable or invalid,
    a deterministic safe reply is returned.
    """

    # --------------------------------------------------
    # AI attempt
    # --------------------------------------------------

    if ai_generate_reply is not None:

        try:

            result = ai_generate_reply(
                reasons=reasons,
                handbook=handbook_content,
                pages=pages,
                alternatives=alternatives or []
            )

            if isinstance(result, dict):

                reply = result.get(
                    "reply",
                    ""
                )

            else:

                reply = str(result)

            valid, _ = validate_reply(
                reply,
                reasons,
                pages,
                alternatives
            )

            if valid:
                return reply, "AI"

        except Exception:
            pass

    # --------------------------------------------------
    # Safe deterministic response
    # --------------------------------------------------

    return (
        make_safe_reply(
            reasons,
            pages,
            alternatives
        ),
        "SAFE"
    )


def compare_lists(actual, expected):
    """
    Compare lists without changing their meaning.
    """

    return actual == expected


def run_task10_case(test):
    """
    Run one complete Task 10 request.
    """

    student_id = test["student_id"]
    message = test["message"]

    # --------------------------------------------------
    # Step 1 - AI course identification
    # --------------------------------------------------

    course_code = identify_course(message)

    course_pass = (
        course_code == test["expected_course"]
    )

    if not course_pass:

        return {
            **test,
            "found_course": course_code,
            "course_pass": False,
            "reasons": [],
            "pages": [],
            "reply": (
                "I could not identify the requested course."
            ),
            "reply_pass": False,
            "overall": False,
            "alternatives": [],
        }

    # --------------------------------------------------
    # Step 2 - Python enrolment rules
    # --------------------------------------------------

    status, data = api_get(
        f"/check/{student_id}/{course_code}"
    )

    if status != 200:

        return {
            **test,
            "found_course": course_code,
            "course_pass": True,
            "reasons": [],
            "pages": [],
            "reply": (
                "Unable to complete the enrolment check."
            ),
            "reply_pass": False,
            "overall": False,
            "alternatives": [],
        }

    result = data.get("data", {})

    reasons = result.get(
        "reasons",
        []
    )

    # --------------------------------------------------
    # Step 3 - Handbook pages
    # --------------------------------------------------

    pages = get_handbook_pages(
        reasons
    )

    handbook_content = get_handbook_content(
        pages
    )

    # --------------------------------------------------
    # Step 4 - Python alternatives
    # --------------------------------------------------

    alternatives = []

    # --------------------------------------------------
    # Alternatives are only relevant for:
    # 1. A course that is full
    # 2. A missing prerequisite
    #
    # A timetable clash, unpaid fees, credit limit,
    # or grade issue does not automatically trigger
    # alternative-course suggestions.
    # --------------------------------------------------

    reason_text = " ".join(reasons).lower()

    needs_alternative = (
        "full" in reason_text
        or "prerequisite" in reason_text
    )

    if needs_alternative:

        alternatives = get_eligible_alternatives(
            student_id,
            course_code
        )

    # --------------------------------------------------
    # Step 5 - Generate final answer
    # --------------------------------------------------

    reply, source = generate_reply(
        reasons=reasons,
        handbook_content=handbook_content,
        pages=pages,
        alternatives=alternatives
    )

    # --------------------------------------------------
    # Step 6 - Validate reply
    # --------------------------------------------------

    reply_pass, validation_message = (
        validate_reply(
            reply,
            reasons,
            pages,
            alternatives
        )
    )

    # If AI response somehow fails,
    # force deterministic safe response.
    if not reply_pass:

        reply = make_safe_reply(
            reasons,
            pages,
            alternatives
        )

        reply_pass, validation_message = (
            validate_reply(
                reply,
                reasons,
                pages,
                alternatives
            )
        )

        source = "SAFE"

    # --------------------------------------------------
    # Compare expected results
    # --------------------------------------------------

    reasons_pass = compare_lists(
        reasons,
        test["expected_reasons"]
    )

    pages_pass = compare_lists(
        pages,
        test["expected_pages"]
    )

    overall = (
        course_pass
        and reasons_pass
        and pages_pass
        and reply_pass
    )

    return {
        **test,
        "found_course": course_code,
        "course_pass": course_pass,
        "reasons": reasons,
        "reasons_pass": reasons_pass,
        "pages": pages,
        "pages_pass": pages_pass,
        "reply": reply,
        "reply_pass": reply_pass,
        "validation_message": validation_message,
        "reply_source": source,
        "alternatives": alternatives,
        "overall": overall,
    }


# ==================================================
# PAGE TITLE
# ==================================================

st.title("🎓 Course Enrolment Assistant")

st.write(
    "AI-assisted course identification with "
    "Python enrolment rules and handbook guidance."
)


# ==================================================
# 1. AI STUDENT ASSISTANT
# ==================================================

st.header("1. Ask the Course Enrolment Assistant")

st.write(
    "Type a natural-language question. "
    "The AI identifies the course, Python checks the "
    "enrolment rules, and the handbook provides guidance."
)

student_question_id = st.text_input(
    "Student ID",
    placeholder="Example: S-102",
    key="ai_student_id"
)

student_question = st.text_area(
    "Student question",
    placeholder=(
        "Example: Trying to sign up for "
        "Machine Learning and it will not let me."
    ),
    key="ai_question"
)

if st.button(
    "Ask Assistant",
    type="primary"
):

    if not student_question_id.strip():

        st.warning(
            "Please enter a student ID."
        )

    elif not student_question.strip():

        st.warning(
            "Please enter a question."
        )

    else:

        with st.spinner(
            "AI is identifying the course..."
        ):

            course_code = identify_course(
                student_question
            )

        if course_code is None:

            st.error(
                "I could not identify the requested course. "
                "Please include the course name or course code."
            )

            st.info(
                "Real course codes: "
                + ", ".join(COURSES.keys())
            )

        else:

            st.success(
                f"Course identified: "
                f"{course_code} - "
                f"{COURSES[course_code]}"
            )

            with st.spinner(
                "Checking enrolment rules..."
            ):

                status, data = api_get(
                    f"/check/"
                    f"{student_question_id.strip()}/"
                    f"{course_code}"
                )

            if status != 200:

                st.error(
                    data.get(
                        "error",
                        "Unable to check enrolment."
                    )
                )

            else:

                result = data.get(
                    "data",
                    {}
                )

                reasons = result.get(
                    "reasons",
                    []
                )

                pages = get_handbook_pages(
                    reasons
                )

                handbook_content = (
                    get_handbook_content(pages)
                )

                alternatives = []

                # --------------------------------------------------
                # Alternatives are only relevant for:
                # 1. A course that is full
                # 2. A missing prerequisite
                #
                # A timetable clash, unpaid fees, credit limit,
                # or grade issue does not automatically trigger
                # alternative-course suggestions.
                # --------------------------------------------------

                reason_text = " ".join(
                    reasons
                ).lower()

                needs_alternative = (
                    "full" in reason_text
                    or "prerequisite" in reason_text
                )

                if needs_alternative:

                    with st.spinner(
                        "Checking eligible alternatives..."
                    ):

                        alternatives = (
                            get_eligible_alternatives(
                                student_question_id.strip(),
                                course_code
                            )
                        )

                with st.spinner(
                    "Preparing final reply..."
                ):

                    final_reply, source = (
                        generate_reply(
                            reasons=reasons,
                            handbook_content=handbook_content,
                            pages=pages,
                            alternatives=alternatives
                        )
                    )

                st.subheader(
                    "Python Rule Decision"
                )

                if result.get("allowed"):

                    st.success(
                        "✅ Enrolment approved."
                    )

                else:

                    st.error(
                        "❌ Enrolment blocked."
                    )

                    if reasons:

                        for reason in reasons:

                            st.warning(reason)

                st.subheader(
                    "Handbook Pages"
                )

                for page in pages:

                    st.write(
                        f"📖 `{page}`"
                    )

                if alternatives:

                    st.subheader(
                        "Python-Verified Alternatives"
                    )

                    for alternative in alternatives:

                        st.write(
                            f"- "
                            f"**{alternative['course_code']}** - "
                            f"{alternative['title']}"
                        )

                st.subheader(
                    "Final Reply"
                )

                st.info(
                    final_reply
                )

                st.caption(
                    f"Reply source: {source}"
                )


# ==================================================
# 2. TASK 10 - RUN ALL SIX REQUESTS
# ==================================================

st.header(
    "2. Task 10 - Run All Six Requests"
)

st.write(
    "This runs the six supplied Task 10 requests, "
    "records the reasons and handbook pages, "
    "validates the final reply, and compares "
    "everything with the expected answers."
)

if st.button(
    "▶ Run All Six Task 10 Tests",
    type="primary"
):

    results = []

    progress = st.progress(
        0
    )

    for index, test in enumerate(
        TASK10_REQUESTS,
        start=1
    ):

        result = run_task10_case(
            test
        )

        results.append(result)

        progress.progress(
            index / len(TASK10_REQUESTS)
        )

    st.session_state["task10_results"] = (
        results
    )


# --------------------------------------------------
# DISPLAY TASK 10 RESULTS
# --------------------------------------------------

if "task10_results" in st.session_state:

    results = st.session_state[
        "task10_results"
    ]

    st.subheader(
        "Task 10 Detailed Results"
    )

    for result in results:

        st.markdown(
            f"### {result['id']} - "
            f"{result['message']}"
        )

        st.write(
            f"**Student ID:** "
            f"{result['student_id']}"
        )

        st.write(
            f"**Expected course:** "
            f"{result['expected_course']}"
        )

        st.write(
            f"**Found course:** "
            f"{result.get('found_course')}"
        )

        if result.get(
            "course_pass",
            False
        ):

            st.success(
                "Course identification: PASS"
            )

        else:

            st.error(
                "Course identification: FAIL"
            )

        # Reasons
        st.write(
            "**Python reasons:**"
        )

        if result.get("reasons"):

            for reason in result["reasons"]:

                st.write(
                    f"- {reason}"
                )

        else:

            st.write(
                "- No blocking reason"
            )

        # Expected pages
        st.write(
            "**Expected handbook pages:**"
        )

        for page in result[
            "expected_pages"
        ]:

            st.write(
                f"- `{page}`"
            )

        # Retrieved pages
        st.write(
            "**Retrieved handbook pages:**"
        )

        for page in result.get(
            "pages",
            []
        ):

            st.write(
                f"- `{page}`"
            )

        if result.get(
            "pages_pass",
            False
        ):

            st.success(
                "Handbook comparison: PASS"
            )

        else:

            st.error(
                "Handbook comparison: FAIL"
            )

        # Reply
        st.write(
            "**AI / final reply:**"
        )

        st.code(
            result.get(
                "reply",
                ""
            ),
            language="text"
        )

        if result.get(
            "reply_pass",
            False
        ):

            st.success(
                "Reply validation: PASS"
            )

        else:

            st.error(
                "Reply validation: FAIL"
            )

        # Alternatives
        if result.get(
            "alternatives"
        ):

            st.write(
                "**Python-verified eligible "
                "alternative(s):**"
            )

            for alternative in result[
                "alternatives"
            ]:

                st.write(
                    f"- "
                    f"{alternative['course_code']} - "
                    f"{alternative['title']}"
                )

        if result.get(
            "overall",
            False
        ):

            st.success(
                f"{result['id']}: PASS"
            )

        else:

            st.error(
                f"{result['id']}: FAIL"
            )

        st.divider()

    # ==================================================
    # FINAL COMPARISON TABLE
    # ==================================================

    st.subheader(
        "Task 10 Final Comparison"
    )

    table_rows = []

    for result in results:

        reasons_text = (
            "; ".join(
                result.get(
                    "reasons",
                    []
                )
            )
            if result.get("reasons")
            else "None"
        )

        pages_text = (
            ", ".join(
                result.get(
                    "pages",
                    []
                )
            )
            if result.get("pages")
            else "None"
        )

        table_rows.append(
            {
                "Test": result["id"],
                "Expected": result[
                    "expected_course"
                ],
                "Found": result.get(
                    "found_course"
                ),
                "Reasons": reasons_text,
                "Pages": pages_text,
                "Reply": (
                    "PASS"
                    if result.get(
                        "overall"
                    )
                    else "FAIL"
                ),
            }
        )

    st.table(
        table_rows
    )

    passed = sum(
        1
        for result in results
        if result.get("overall")
    )

    st.subheader(
        "Task 10 Summary"
    )

    if passed == 6:

        st.success(
            "✅ Tests Passed: 6/6"
        )

        st.success(
            "Task 10 completed successfully. "
            "All six requests matched the expected "
            "course, reasons, handbook pages, "
            "and validated reply."
        )

    else:

        st.error(
            f"Tests Passed: {passed}/6"
        )

        st.warning(
            "Some Task 10 checks still need correction."
        )


# ==================================================
# 3. STUDENT LOOKUP
# ==================================================

st.header(
    "3. Student Lookup"
)

lookup_student = st.text_input(
    "Enter Student ID",
    placeholder="Example: S-102",
    key="lookup_student"
)

if st.button(
    "Find Student"
):

    if not lookup_student.strip():

        st.warning(
            "Please enter a student ID."
        )

    else:

        with st.spinner(
            "Loading student..."
        ):

            status, data = api_get(
                f"/students/{lookup_student.strip()}"
            )

        if status == 404:

            st.error(
                data.get(
                    "error",
                    "Student not found."
                )
            )

        elif status != 200:

            st.error(
                data.get(
                    "error",
                    "Unable to load student."
                )
            )

        else:

            student = data.get(
                "data",
                {}
            )

            st.success(
                "Student found."
            )

            st.write(
                f"**Student ID:** "
                f"{student.get('student_id')}"
            )

            st.write(
                f"**Name:** "
                f"{student.get('name')}"
            )

            st.write(
                f"**Year:** "
                f"{student.get('year')}"
            )

            st.write(
                f"**Programme:** "
                f"{student.get('programme')}"
            )

            st.write(
                f"**Fees:** "
                f"{student.get('fees_status')}"
            )

            enrolment_status, enrolment_data = (
                api_get(
                    f"/students/"
                    f"{lookup_student.strip()}/"
                    f"enrolments"
                )
            )

            if enrolment_status == 200:

                enrolments = (
                    enrolment_data
                    .get("data", {})
                    .get("enrolments", [])
                )

                st.subheader(
                    "Current / Previous Enrolments"
                )

                if enrolments:

                    st.table(
                        enrolments
                    )

                else:

                    st.info(
                        "This student has no enrolments."
                    )


# ==================================================
# 4. COURSE LIST
# ==================================================

st.header(
    "4. Course List"
)

if st.button(
    "Load Courses"
):

    with st.spinner(
        "Loading courses..."
    ):

        status, data = api_get(
            "/courses"
        )

    if status != 200:

        st.error(
            data.get(
                "error",
                "Unable to load courses."
            )
        )

    else:

        courses = data.get(
            "data",
            []
        )

        for course in courses:

            code = course.get(
                "course_code"
            )

            title = course.get(
                "title"
            )

            day = course.get(
                "day"
            )

            start = course.get(
                "start"
            )

            end = course.get(
                "end"
            )

            credits = course.get(
                "credits"
            )

            enrolled = course.get(
                "enrolled_now",
                0
            )

            capacity = course.get(
                "capacity"
            )

            if course.get("full"):

                st.error(
                    f"🔴 FULL — "
                    f"{code} - {title} | "
                    f"{day} {start}-{end} | "
                    f"{credits} credits | "
                    f"{enrolled}/{capacity}"
                )

            else:

                st.success(
                    f"🟢 "
                    f"{code} - {title} | "
                    f"{day} {start}-{end} | "
                    f"{credits} credits | "
                    f"{enrolled}/{capacity}"
                )


# ==================================================
# 5. MANUAL ENROLMENT CHECK
# ==================================================

st.header(
    "5. Manual Enrolment Check"
)

manual_student = st.text_input(
    "Student ID",
    placeholder="Example: S-102",
    key="manual_student"
)

manual_course = st.text_input(
    "Course Code",
    placeholder="Example: CS301",
    key="manual_course"
)

if st.button(
    "Check Enrolment"
):

    if not manual_student.strip():

        st.warning(
            "Please enter a student ID."
        )

    elif not manual_course.strip():

        st.warning(
            "Please enter a course code."
        )

    else:

        with st.spinner(
            "Checking enrolment rules..."
        ):

            status, data = api_get(
                f"/check/"
                f"{manual_student.strip()}/"
                f"{manual_course.strip().upper()}"
            )

        if status == 404:

            st.error(
                data.get(
                    "error",
                    "Student or course not found."
                )
            )

        elif status != 200:

            st.error(
                data.get(
                    "error",
                    "Unable to perform enrolment check."
                )
            )

        else:

            result = data.get(
                "data",
                {}
            )

            if result.get(
                "allowed"
            ):

                st.success(
                    "✅ Enrolment approved."
                )

            else:

                st.error(
                    "❌ Enrolment blocked."
                )

            st.subheader(
                "Reasons"
            )

            reasons = result.get(
                "reasons",
                []
            )

            if reasons:

                for reason in reasons:

                    st.warning(
                        reason
                    )

            else:

                st.success(
                    "No blocking reasons."
                )


# ==================================================
# FOOTER
# ==================================================

st.divider()

st.caption(
    "Course Enrolment Assistant | "
    "Python Rules + FastAPI + Handbook Search + AI"
)