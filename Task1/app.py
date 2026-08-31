from pathlib import Path
import re

import requests
import streamlit as st


# ============================================================
# OPTIONAL PROJECT MODULES
# ============================================================

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


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="Course Enrolment Assistant",
    page_icon="🎓",
    layout="wide"
)


# ============================================================
# CUSTOM CSS
# ============================================================

CSS_FILE = Path(__file__).resolve().parent / "style.css"

if CSS_FILE.exists():
    st.markdown(
        f"<style>{CSS_FILE.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent

DATA_DIR = PROJECT_DIR / "data"
HANDBOOK_DIR = DATA_DIR / "handbook"

API_URL = "http://127.0.0.1:8000"


# ============================================================
# COURSE DATA
# ============================================================

COURSES = {
    "CS101": "Programming Foundations",
    "CS201": "Algorithms",
    "CS202": "Databases",
    "CS301": "Machine Learning",
    "CS310": "Distributed Systems",
    "DS220": "Data Visualisation",
    "MA150": "Statistics",
}


# ============================================================
# TASK 10 EXPECTED DATA
# ============================================================

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
            "course is full, 25 of 25"
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


# ============================================================
# FASTAPI HELPER
# ============================================================

def api_get(endpoint):
    """Call the FastAPI backend safely."""

    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            timeout=30,
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
                "Start it with: uvicorn api:app --reload"
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


# ============================================================
# COURSE IDENTIFICATION
# ============================================================

def identify_course_fallback(message):
    """Simple non-AI course-identification fallback."""

    text = message.lower()

    for code in COURSES:
        if re.search(
            rf"\b{re.escape(code.lower())}\b",
            text,
        ):
            return code

    for code, title in COURSES.items():
        if title.lower() in text:
            return code

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
    """Use AI course identification, then fall back safely."""

    if ai_identify_course is not None:

        try:
            result = ai_identify_course(
                message,
                list(COURSES.items()),
            )

            if isinstance(result, dict):

                code = result.get(
                    "course_code"
                )

                if code in COURSES:
                    return code

            if isinstance(result, str):

                if result in COURSES:
                    return result

        except Exception as error:
            print(
                f"Course AI failed: {error}"
            )

    return identify_course_fallback(
        message
    )


# ============================================================
# VECTOR / RAG HANDBOOK RETRIEVAL
# ============================================================

def retrieve_handbook(
    question,
    reasons,
    k=5,
):
    """
    Use search.py to retrieve handbook chunks.

    search.py performs:
        question -> embedding -> vector similarity
        -> top handbook chunks

    Returns:
        pages
        handbook_text
        raw search results
    """

    if handbook_search is None:
        return [], "", []

    reason_text = " ".join(
        reasons or []
    )

    retrieval_query = (
        f"{question}\n"
        f"Verified enrolment reasons: {reason_text}"
    )

    try:

        results = handbook_search(
            retrieval_query,
            k=k,
        )

    except Exception as error:

        print(
            f"Handbook vector search failed: {error}"
        )

        return [], "", []

    if not results:
        return [], "", []

    pages = []
    chunks = []

    for result in results:

        filename = str(
            result.get(
                "file",
                ""
            )
        ).strip()

        text = str(
            result.get(
                "text",
                ""
            )
        ).strip()

        if not filename:
            continue

        if filename not in pages:
            pages.append(filename)

        if text:

            chunks.append(
                f"--- {filename} ---\n{text}"
            )

    handbook_text = "\n\n".join(
        chunks
    )

    return (
        pages,
        handbook_text,
        results,
    )


# ============================================================
# HANDBOOK FALLBACK
# ============================================================

def get_handbook_pages_fallback(
    reasons
):
    """
    Backup only.

    Normal application retrieval uses vector search.
    """

    pages = []

    for reason in reasons or []:

        lower = reason.lower()

        if "fee" in lower:

            if "fees.md" not in pages:
                pages.append(
                    "fees.md"
                )

        if (
            "prerequisite" in lower
            or "grade" in lower
        ):

            if "prerequisites.md" not in pages:
                pages.append(
                    "prerequisites.md"
                )

            if "advice.md" not in pages:
                pages.append(
                    "advice.md"
                )

            if "grade" in lower:

                if "waivers.md" not in pages:
                    pages.append(
                        "waivers.md"
                    )

        if "full" in lower:

            if "capacity.md" not in pages:
                pages.append(
                    "capacity.md"
                )

            if "advice.md" not in pages:
                pages.append(
                    "advice.md"
                )

        if "clash" in lower:

            if "timetable.md" not in pages:
                pages.append(
                    "timetable.md"
                )

        if "credit" in lower:

            if "credit_limit.md" not in pages:
                pages.append(
                    "credit_limit.md"
                )

    if (
        not reasons
        and "advice.md" not in pages
    ):
        pages.append(
            "advice.md"
        )

    return pages


def load_handbook_text(
    filename
):
    """Load one handbook file."""

    path = HANDBOOK_DIR / filename

    if not path.exists():
        return ""

    try:

        return path.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        return ""


def get_handbook_content(
    pages
):
    """Load fallback handbook files."""

    content = {}

    for page in pages or []:

        text = load_handbook_text(
            page
        )

        if text:
            content[page] = text

    return content


# ============================================================
# PYTHON-VERIFIED ALTERNATIVES
# ============================================================

def get_eligible_alternatives(
    student_id,
    blocked_course,
):
    """
    Use Python/FastAPI rules to find eligible alternatives.

    The AI does not decide eligibility.
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

        result = data.get(
            "data",
            {}
        )

        if result.get("allowed") is True:

            alternatives.append({
                "course_code": code,
                "title": COURSES[code],
            })

    return alternatives


# ============================================================
# FINAL REPLY VALIDATION
# ============================================================

def validate_reply(
    reply,
    reasons,
    pages,
    alternatives=None,
):
    """
    Validate final output against verified Python facts.
    """

    alternatives = alternatives or []

    if not reply:
        return False, "Reply is empty."

    reply_lower = reply.lower()
    normalized_reply = " ".join(
        reply_lower.split()
    )

    for reason in reasons or []:

        normalized_reason = " ".join(
            reason.lower().split()
        )

        if normalized_reason not in normalized_reply:

            return (
                False,
                f"Missing reason: {reason}",
            )

    for page in pages or []:

        if page.lower() not in reply_lower:

            return (
                False,
                f"Missing handbook page: {page}",
            )

    mentioned_codes = re.findall(
        r"\b[A-Z]{2,4}\d{3}\b",
        reply.upper(),
    )

    for code in mentioned_codes:

        if code not in COURSES:

            return (
                False,
                f"Unknown course code in reply: {code}",
            )

    allowed_numbers = set()

    for reason in reasons or []:

        for number in re.findall(
            r"\b\d+\b",
            reason,
        ):
            allowed_numbers.add(
                number
            )

    for alternative in alternatives:

        for number in re.findall(
            r"\d+",
            alternative.get(
                "course_code",
                "",
            ),
        ):
            allowed_numbers.add(
                number
            )

    for number in re.findall(
        r"\b\d+\b",
        reply,
    ):

        if number not in allowed_numbers:

            return (
                False,
                f"Number not supplied to AI: {number}",
            )

    if "waiver" in reply_lower:

        authority_terms = [
            "course leader",
            "department",
            "departmental",
            "academic office",
            "programme leader",
            "authorised",
            "authorized",
            "approval",
            "approver",
        ]

        if not any(
            term in reply_lower
            for term in authority_terms
        ):

            return (
                False,
                "Waiver mentioned without approval authority.",
            )

        unsafe_phrases = [
            "waiver approved",
            "enrolment approved",
            "approved for enrolment",
            "you are approved",
        ]

        for phrase in unsafe_phrases:

            if phrase in reply_lower:

                return (
                    False,
                    "Reply incorrectly records approval.",
                )

    return True, "PASS"


# ============================================================
# SAFE FINAL RESPONSE
# ============================================================

def make_safe_reply(
    reasons,
    pages,
    alternatives=None,
):
    """
    Guaranteed fact-based reply.

    Used if the AI output fails validation.
    """

    reasons = reasons or []
    pages = pages or []
    alternatives = alternatives or []

    lines = []

    if reasons:

        lines.append(
            "The following issues prevent enrolment:"
        )

        for reason in reasons:

            lines.append(
                f"- {reason}"
            )

    else:

        lines.append(
            "There are no blocking reasons for enrolment."
        )

    if pages:

        lines.append("")
        lines.append(
            "Relevant handbook page(s):"
        )

        for page in pages:

            lines.append(
                f"- {page}"
            )

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

    if "waivers.md" in pages:

        lines.append("")

        lines.append(
            "You can ask the course leader about a waiver. "
            "The course leader decides whether the waiver "
            "can be approved; this does not approve enrolment."
        )

    return "\n".join(lines)


# ============================================================
# REPLY.PY CONNECTION
# ============================================================

def generate_reply(
    reasons,
    handbook_content,
    pages,
    search_results=None,
    alternatives=None,
):
    """
    Pass the actual RAG handbook content to reply.py.

    Connection:
        app.py -> reply.py
        reasons
        handbook
        pages
        search_results
        alternatives
    """

    alternatives = alternatives or []

    if ai_generate_reply is not None:

        try:

            reply_kwargs = {
                "reasons": reasons,
                "handbook": handbook_content,
                "pages": pages,
                "alternatives": alternatives,
            }

            # Pass the raw RAG results when reply.py supports them.
            # This keeps app.py compatible with older reply.py versions.
            try:
                import inspect

                if "search_results" in inspect.signature(
                    ai_generate_reply
                ).parameters:
                    reply_kwargs["search_results"] = search_results or []
            except Exception:
                pass

            result = ai_generate_reply(**reply_kwargs)

            if (
                isinstance(result, tuple)
                and len(result) == 2
            ):

                reply = str(
                    result[0]
                )

                source = str(
                    result[1]
                )

            elif isinstance(
                result,
                dict
            ):

                reply = str(
                    result.get(
                        "reply",
                        ""
                    )
                )

                source = "AI"

            else:

                reply = str(
                    result
                )

                source = "AI"

            valid, message = (
                validate_reply(
                    reply,
                    reasons,
                    pages,
                    alternatives,
                )
            )

            if valid:

                return reply, source

            print(
                f"App validation failed: {message}"
            )

        except Exception as error:

            print(
                f"reply.py failed: {error}"
            )

    return (
        make_safe_reply(
            reasons,
            pages,
            alternatives,
        ),
        "SAFE",
    )


# ============================================================
# TASK 10 HELPERS
# ============================================================

def pages_cover_expected(
    retrieved,
    expected,
):
    """
    RAG can return additional useful pages.

    Every expected page must be present.
    """

    retrieved_set = set(
        retrieved or []
    )

    return all(
        page in retrieved_set
        for page in expected or []
    )


def run_task10_case(
    test
):
    """Run one complete Task 10 request."""

    student_id = test[
        "student_id"
    ]

    message = test[
        "message"
    ]

    # --------------------------------------------------------
    # Step 1 - course identification
    # --------------------------------------------------------

    course_code = identify_course(
        message
    )

    course_pass = (
        course_code
        == test["expected_course"]
    )

    if not course_pass:

        return {
            **test,
            "found_course": course_code,
            "course_pass": False,
            "reasons": [],
            "reasons_pass": False,
            "pages": [],
            "pages_pass": False,
            "retrieved_chunks": [],
            "reply": (
                "I could not identify the requested course."
            ),
            "reply_pass": False,
            "overall": False,
            "alternatives": [],
            "reply_source": "SAFE",
        }

    # --------------------------------------------------------
    # Step 2 - Python rules
    # --------------------------------------------------------

    status, data = api_get(
        f"/check/{student_id}/{course_code}"
    )

    if status != 200:

        return {
            **test,
            "found_course": course_code,
            "course_pass": True,
            "reasons": [],
            "reasons_pass": False,
            "pages": [],
            "pages_pass": False,
            "retrieved_chunks": [],
            "reply": (
                "Unable to complete the enrolment check."
            ),
            "reply_pass": False,
            "overall": False,
            "alternatives": [],
            "reply_source": "SAFE",
        }

    result = data.get(
        "data",
        {}
    )

    reasons = result.get(
        "reasons",
        []
    )

    # --------------------------------------------------------
    # Step 3 - REAL VECTOR / RAG retrieval
    # --------------------------------------------------------

    (
        pages,
        handbook_text,
        search_results,
    ) = retrieve_handbook(
        question=message,
        reasons=reasons,
        k=5,
    )

    # Search fallback only if vector search fails.
    if not pages:

        pages = (
            get_handbook_pages_fallback(
                reasons
            )
        )

        fallback_content = (
            get_handbook_content(
                pages
            )
        )

        handbook_text = "\n\n".join(
            f"--- {filename} ---\n{text}"
            for filename, text
            in fallback_content.items()
        )

    # --------------------------------------------------------
    # Step 4 - Python alternatives
    # --------------------------------------------------------

    alternatives = []

    reason_text = " ".join(
        reasons
    ).lower()

    if (
        "full" in reason_text
        or "prerequisite" in reason_text
    ):

        alternatives = (
            get_eligible_alternatives(
                student_id,
                course_code,
            )
        )

    # --------------------------------------------------------
    # Step 5 - reply.py
    # --------------------------------------------------------

    reply, source = generate_reply(
        reasons=reasons,
        handbook_content=handbook_text,
        pages=pages,
        search_results=search_results,
        alternatives=alternatives,
    )

    # --------------------------------------------------------
    # Step 6 - final safety validation
    # --------------------------------------------------------

    reply_pass, validation_message = (
        validate_reply(
            reply,
            reasons,
            pages,
            alternatives,
        )
    )

    if not reply_pass:

        reply = make_safe_reply(
            reasons,
            pages,
            alternatives,
        )

        reply_pass, validation_message = (
            validate_reply(
                reply,
                reasons,
                pages,
                alternatives,
            )
        )

        source = "SAFE"

    # --------------------------------------------------------
    # Step 7 - compare expected result
    # --------------------------------------------------------

    reasons_pass = (
        reasons
        == test["expected_reasons"]
    )

    pages_pass = pages_cover_expected(
        pages,
        test["expected_pages"],
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
        "retrieved_chunks": search_results,
        "reply": reply,
        "reply_pass": reply_pass,
        "validation_message": validation_message,
        "reply_source": source,
        "alternatives": alternatives,
        "overall": overall,
    }


# ============================================================
# STREAMLIT PAGE
# ============================================================

st.title(
    "🎓 Course Enrolment Assistant"
)

st.write(
    "AI course identification → Python enrolment rules "
    "→ BGE vector/RAG handbook retrieval → "
    "validated final reply."
)


# ============================================================
# 1. AI STUDENT ASSISTANT
# ============================================================

st.header(
    "1. Ask the Course Enrolment Assistant"
)

st.write(
    "The AI identifies the course. Python checks the "
    "rules. BGE embeddings retrieve relevant handbook "
    "chunks. The reply model creates the final response."
)

student_question_id = st.text_input(
    "Student ID",
    placeholder="Example: S-102",
    key="ai_student_id",
)

student_question = st.text_area(
    "Student question",
    placeholder=(
        "Example: Trying to sign up for "
        "Machine Learning and it will not let me."
    ),
    key="ai_question",
)

if st.button(
    "Ask Assistant",
    type="primary",
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

        # ----------------------------------------------------
        # Step 1 - course
        # ----------------------------------------------------

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

        else:

            st.success(
                f"Course identified: "
                f"{course_code} - "
                f"{COURSES[course_code]}"
            )

            # ------------------------------------------------
            # Step 2 - Python rules
            # ------------------------------------------------

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
                        "Unable to check enrolment.",
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

                # --------------------------------------------
                # Step 3 - REAL RAG
                # --------------------------------------------

                with st.spinner(
                    "Searching the handbook with embeddings..."
                ):

                    (
                        pages,
                        handbook_text,
                        search_results,
                    ) = retrieve_handbook(
                        question=student_question,
                        reasons=reasons,
                        k=5,
                    )

                # Fallback only if vector search is unavailable.
                if not pages:

                    pages = (
                        get_handbook_pages_fallback(
                            reasons
                        )
                    )

                    fallback_content = (
                        get_handbook_content(
                            pages
                        )
                    )

                    handbook_text = (
                        "\n\n".join(
                            f"--- {filename} ---\n{text}"
                            for filename, text
                            in fallback_content.items()
                        )
                    )

                    st.warning(
                        "Vector search was unavailable, "
                        "so the handbook fallback was used."
                    )

                # --------------------------------------------
                # Step 4 - alternatives
                # --------------------------------------------

                alternatives = []

                reason_text = " ".join(
                    reasons
                ).lower()

                if (
                    "full" in reason_text
                    or "prerequisite" in reason_text
                ):

                    with st.spinner(
                        "Checking eligible alternatives..."
                    ):

                        alternatives = (
                            get_eligible_alternatives(
                                student_question_id.strip(),
                                course_code,
                            )
                        )

                # --------------------------------------------
                # Step 5 - final reply
                # --------------------------------------------

                with st.spinner(
                    "Preparing final reply..."
                ):

                    final_reply, source = (
                        generate_reply(
                            reasons=reasons,
                            handbook_content=handbook_text,
                            pages=pages,
                            search_results=search_results,
                            alternatives=alternatives,
                        )
                    )

                # --------------------------------------------
                # Step 6 - validate
                # --------------------------------------------

                reply_pass, validation_message = (
                    validate_reply(
                        final_reply,
                        reasons,
                        pages,
                        alternatives,
                    )
                )

                if not reply_pass:

                    final_reply = make_safe_reply(
                        reasons,
                        pages,
                        alternatives,
                    )

                    reply_pass, validation_message = (
                        validate_reply(
                            final_reply,
                            reasons,
                            pages,
                            alternatives,
                        )
                    )

                    source = "SAFE"

                # --------------------------------------------
                # DECISION
                # --------------------------------------------

                st.subheader(
                    "Python Rule Decision"
                )

                if result.get("allowed"):

                    st.success(
                        "✅ No enrolment rule blocked the request."
                    )

                else:

                    st.error(
                        "❌ Enrolment blocked."
                    )

                    for reason in reasons:

                        st.warning(
                            reason
                        )

                # --------------------------------------------
                # RAG RESULTS
                # --------------------------------------------

                st.subheader(
                    "Retrieved Handbook Content"
                )

                if search_results:

                    # Show only the highest-scoring RAG result in the UI.
                    top_result = search_results[0]
                    top_file = top_result.get("file", "Unknown")
                    top_score = top_result.get("score", "N/A")
                    top_text = top_result.get("text", "")

                    st.write(
                        f"**Top result: {top_file}** "
                        f"(score: {top_score})"
                    )

                    import html

                    safe_handbook_text = html.escape(
                        str(top_text)
                    ).replace("\n", "<br>")

                    st.markdown(
                        f'<div class="handbook-text">'
                        f"{safe_handbook_text}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                else:

                    st.info(
                        "No vector-search results were available."
                    )

                # --------------------------------------------
                # HANDBOOK PAGES
                # --------------------------------------------

                st.subheader(
                    "Handbook Pages"
                )

                for page in pages:

                    st.write(
                        f"📖 `{page}`"
                    )

                # --------------------------------------------
                # ALTERNATIVES
                # --------------------------------------------

                if alternatives:

                    st.subheader(
                        "Python-Verified Alternatives"
                    )

                    for alternative in alternatives:

                        st.write(
                            f"- **{alternative['course_code']}** - "
                            f"{alternative['title']}"
                        )

                # --------------------------------------------
                # FINAL REPLY
                # --------------------------------------------

                st.subheader(
                    "Final Reply"
                )

                st.info(
                    final_reply
                )

                st.caption(
                    f"Reply source: {source} | "
                    f"Validation: "
                    f"{'PASS' if reply_pass else 'FAIL'}"
                )


# ============================================================
# 2. TASK 10
# ============================================================

st.header(
    "2. Task 10 - Run All Six Requests"
)

st.write(
    "Runs all six requests and checks course identification, "
    "Python reasons, RAG handbook retrieval, and final reply."
)

if st.button(
    "▶ Run All Six Task 10 Tests",
    type="primary",
):

    results = []

    progress = st.progress(
        0
    )

    for index, test in enumerate(
        TASK10_REQUESTS,
        start=1,
    ):

        result = run_task10_case(
            test
        )

        results.append(
            result
        )

        progress.progress(
            index / len(
                TASK10_REQUESTS
            )
        )

    st.session_state[
        "task10_results"
    ] = results


if (
    "task10_results"
    in st.session_state
):

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
            f"**Expected course:** "
            f"{result['expected_course']}"
        )

        st.write(
            f"**Found course:** "
            f"{result.get('found_course')}"
        )

        if result.get(
            "course_pass"
        ):

            st.success(
                "Course identification: PASS"
            )

        else:

            st.error(
                "Course identification: FAIL"
            )

        st.write(
            "**Expected reasons:**"
        )

        for reason in result.get(
            "expected_reasons",
            [],
        ):

            st.write(
                f"- {reason}"
            )

        st.write(
            "**Actual Python reasons:**"
        )

        if result.get(
            "reasons"
        ):

            for reason in result[
                "reasons"
            ]:

                st.write(
                    f"- {reason}"
                )

        else:

            st.write(
                "- None"
            )

        if result.get(
            "reasons_pass"
        ):

            st.success(
                "Reasons comparison: PASS"
            )

        else:

            st.error(
                "Reasons comparison: FAIL"
            )

        st.write(
            "**Expected handbook pages:**"
        )

        for page in result.get(
            "expected_pages",
            [],
        ):

            st.write(
                f"- `{page}`"
            )

        st.write(
            "**Retrieved handbook pages:**"
        )

        for page in result.get(
            "pages",
            [],
        ):

            st.write(
                f"- `{page}`"
            )

        if result.get(
            "pages_pass"
        ):

            st.success(
                "RAG handbook retrieval: PASS"
            )

        else:

            st.error(
                "RAG handbook retrieval: FAIL"
            )

        if result.get(
            "retrieved_chunks"
        ):

            st.write(
                "**Top vector-search results:**"
            )

            for item in result[
                "retrieved_chunks"
            ]:

                st.caption(
                    f"{item.get('file')} | "
                    f"score={item.get('score')}"
                )

        st.write(
            "**Final reply:**"
        )

        st.code(
            result.get(
                "reply",
                "",
            ),
            language="text",
        )

        if result.get(
            "reply_pass"
        ):

            st.success(
                "Reply validation: PASS"
            )

        else:

            st.error(
                "Reply validation: FAIL"
            )

        st.write(
            f"**Reply source:** "
            f"{result.get('reply_source')}"
        )

        if result.get(
            "alternatives"
        ):

            st.write(
                "**Python-verified alternatives:**"
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
            "overall"
        ):

            st.success(
                f"{result['id']}: PASS"
            )

        else:

            st.error(
                f"{result['id']}: FAIL"
            )

        st.divider()

    st.subheader(
        "Task 10 Final Comparison"
    )

    table_rows = []

    for result in results:

        reasons_text = (
            "; ".join(
                result.get(
                    "reasons",
                    [],
                )
            )
            if result.get(
                "reasons"
            )
            else "None"
        )

        pages_text = (
            ", ".join(
                result.get(
                    "pages",
                    [],
                )
            )
            if result.get(
                "pages"
            )
            else "None"
        )

        table_rows.append(
            {
                "Test": result[
                    "id"
                ],
                "Expected Course": result[
                    "expected_course"
                ],
                "Found Course": result.get(
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
        if result.get(
            "overall"
        )
    )

    st.subheader(
        "Task 10 Summary"
    )

    st.write(
        f"Tests Passed: {passed}/6"
    )

    if passed == 6:

        st.success(
            "✅ All six Task 10 requests passed."
        )

    else:

        st.warning(
            "Some Task 10 checks still need correction."
        )


# ============================================================
# 3. STUDENT LOOKUP
# ============================================================

st.header(
    "3. Student Lookup"
)

lookup_student = st.text_input(
    "Enter Student ID",
    placeholder="Example: S-102",
    key="lookup_student",
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
                f"/students/"
                f"{lookup_student.strip()}"
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

            (
                enrolment_status,
                enrolment_data,
            ) = api_get(
                f"/students/"
                f"{lookup_student.strip()}/"
                f"enrolments"
            )

            if enrolment_status == 200:

                enrolments = (
                    enrolment_data
                    .get(
                        "data",
                        {}
                    )
                    .get(
                        "enrolments",
                        []
                    )
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


# ============================================================
# 4. COURSE LIST
# ============================================================

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

            if course.get(
                "full"
            ):

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


# ============================================================
# 5. MANUAL ENROLMENT CHECK
# ============================================================

st.header(
    "5. Manual Enrolment Check"
)

manual_student = st.text_input(
    "Student ID",
    placeholder="Example: S-102",
    key="manual_student",
)

manual_course = st.text_input(
    "Course Code",
    placeholder="Example: CS301",
    key="manual_course",
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
                    "✅ No enrolment rule blocked this course."
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


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Course Enrolment Assistant | "
    "Python Rules + FastAPI + BGE Vector Search + RAG + AI"
)
