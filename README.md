# 🎓 Course Enrolment Assistant

An AI-assisted course enrolment system that converts a student's natural-language request into a course code, checks enrolment eligibility using deterministic Python rules, retrieves relevant handbook guidance, and generates a student-friendly reply.

## 1. Project Overview

The Course Enrolment Assistant helps students understand whether they can enrol in a requested course.

A student can type a request such as:

> "I want to take Algorithms this term."

The system:

1. Identifies the requested course.
2. Checks enrolment rules.
3. Retrieves relevant handbook pages.
4. Generates and validates a readable response.
5. Displays the result through Streamlit.

**Important:** Python rules make the actual enrolment decision. AI is used for language understanding and response generation.


![Uploading Course enrolment assistant architecture.png…]()

## 2. Objective

- Validate student and course data.
- Store structured data in SQLite.
- Implement deterministic enrolment rules.
- Provide a FastAPI backend.
- Search handbook pages semantically.
- Identify courses from natural-language requests.
- Generate student-friendly replies.
- Validate AI replies before displaying them.
- Provide a Streamlit interface.
- Test the complete workflow with six supplied requests.

## 3. Features

### Student features

- Student lookup by ID.
- Fees-status display.
- Enrolment history.
- Course listing.
- Enrolment eligibility checking.

### Five enrolment rules

1. **Fees** — blocks unpaid fees.
2. **Prerequisites** — checks completion and minimum grade.
3. **Capacity** — checks whether a course is full.
4. **Timetable clash** — checks overlapping enrolled courses.
5. **Credit limit** — checks the 60-credit maximum.

### AI and handbook features

- Natural-language course identification.
- Semantic handbook search.
- Handbook-page retrieval.
- AI-generated replies.
- Reply validation and safe fallback.
- Python-controlled alternative-course suggestions.
- Waiver handling without automatically approving enrolment.

## 4. Project Structure

```text
course-enrolment-assistant/
│
├── .gitignore
│
├── Task1/
│   ├── __init__.py
│   ├── ai.py
│   ├── api.py
│   ├── app.py
│   ├── check_data.py
│   ├── enrolment.db
│   ├── load.py
│   ├── reply.py
│   ├── rules.py
│   └── search.py
│
└── data/
    ├── courses.csv
    ├── current_numbers.csv
    ├── enrolments.csv
    ├── prerequisites.csv
    ├── students.csv
    ├── handbook/
    │   ├── advice.md
    │   ├── capacity.md
    │   ├── credit_limit.md
    │   ├── fees.md
    │   ├── prerequisites.md
    │   ├── timetable.md
    │   ├── waivers.md
    │   └── withdrawal.md
    └── requests/
        ├── R1.json
        ├── R2.json
        ├── R3.json
        ├── R4.json
        ├── R5.json
        └── R6.json
```

## 5. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Main programming language |
| SQLite | Local relational database |
| SQL | Database queries and rule checks |
| FastAPI | Backend REST API |
| Uvicorn | FastAPI development server |
| Streamlit | Web interface |
| Sentence Transformers | Semantic handbook search |
| BAAI/bge-small-en-v1.5 | Handbook embedding model |
| NumPy | Vector similarity |
| AI model | Course identification and reply generation |
| CSV | Source data |
| JSON | Test requests |
| Markdown | Handbook content |
| Git/GitHub | Version control and repository |

## 6. How the Data Flows

```text
Student
   │
   ▼
Streamlit app.py
   │
   ├── Student ID
   └── Natural-language question
          │
          ▼
       ai.py
          │
          │ real course code
          ▼
       api.py
          │
          ▼
       rules.py
          │
          ├── fees_block()
          ├── prerequisite_block()
          ├── capacity_block()
          ├── clash_block()
          └── credit_block()
          │
          ▼
     SQLite enrolment.db
          │
          ▼
     Verified reasons
          │
          ▼
       search.py
          │
          ▼
     Handbook Markdown
          │
          ▼
       reply.py
          │
          ▼
    Validated final reply
          │
          ▼
       Streamlit
```

The AI does not decide whether enrolment is allowed. The Python rules produce the actual blocking reasons.

## 7. Task 1 → Task 10 Flow

### Task 1 — Data check

`check_data.py` reads the CSV files and checks for:

- Empty values.
- Inconsistent capitalization.
- Invalid student IDs.
- Invalid course codes.
- Missing grades for completed courses.
- Grades on currently enrolled courses.

The original data check found **8 data-quality issues**.

### Task 2 — Database creation

`load.py` reads the CSV files and creates:

```text
Task1/enrolment.db
```

Tables:

```text
students
courses
prerequisites
enrolments
current_numbers
```

Loaded row counts:

```text
students: 7
courses: 7
prerequisites: 6
enrolments: 20
current_numbers: 7
```

### Task 3 — Enrolment rules

`rules.py` implements:

```text
fees_block()
prerequisite_block()
capacity_block()
clash_block()
credit_block()
```

These rules produce deterministic reasons for the six test requests.

### Task 4 — FastAPI backend

`api.py` exposes:

```text
GET /students/{student_id}
GET /students/{student_id}/enrolments
GET /courses
GET /courses/{course_code}
GET /check/{student_id}/{course_code}
GET /requests/{request_id}
```

The check endpoint runs all five rules.

### Task 5 — Bad-input handling

`api.py` returns clear 404 responses for unknown students, courses, and request IDs.

A student with no enrolments returns HTTP 200 with an empty enrolment list.

### Task 6 — Streamlit page

`app.py` provides:

1. Student lookup.
2. Course list.
3. Manual enrolment check.
4. Natural-language assistant.
5. Loading indicators.
6. Clear error messages.

### Task 7 — Handbook search

`search.py` loads Markdown handbook pages and creates embeddings with:

```text
BAAI/bge-small-en-v1.5
```

It compares the question vector with handbook vectors using normalized dot products.

### Task 8 — AI course identification

`ai.py` receives the student's message and the seven real course codes with titles.

Example:

```text
Machine Learning please, I have done everything it asks for.
```

The AI should return:

```json
{"course_code": "CS301"}
```

The code is checked against the real course list before it is used.

Task 8 result:

```text
Six requests: 6/6 passed
Fake course-code test: PASSED
No-JSON test: PASSED
```

### Task 9 — AI reply

`reply.py` receives the Python-generated reasons and retrieved handbook information.

The reply is checked so that:

- Every Python reason appears.
- Numbers and course codes are controlled by the supplied information.
- A failed first response gets one rewrite attempt.
- A second failure uses a safe fallback.
- Waiver replies identify the approving authority.
- A waiver never means enrolment is approved.

### Task 10 — Complete system test

`app.py` runs all six supplied requests and compares:

- Expected course.
- Found course.
- Python reasons.
- Expected handbook pages.
- Retrieved handbook pages.
- Final reply validation.

**Final result: 6/6 passed.**

## 8. How the Main Files Connect

### `rules.py`

Responsible for the actual enrolment decision.

```text
SQLite → rules.py → Python reasons
```

### `api.py`

Provides the backend API.

```text
app.py → api.py → rules.py → SQLite
```

### `search.py`

Finds relevant handbook pages.

```text
Question → search.py → handbook pages
```

### `ai.py`

Converts natural-language course requests into real course codes.

```text
Student message → ai.py → course code
```

### `reply.py`

Turns verified reasons and handbook information into a readable reply.

```text
Reasons + handbook → reply.py → validated reply
```

### `app.py`

Connects the user interface to the complete workflow.

```text
Student
  ↓
app.py
  ↓
ai.py
  ↓
api.py / rules.py
  ↓
search.py
  ↓
reply.py
  ↓
validated response
```

## 9. Installation

Clone the repository:

```bash
git clone https://github.com/gsairaja1/course-enrolment-assistant.git
cd course-enrolment-assistant
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.venv\Scripts\Activate.ps1
```

Install the required packages:

```bash
pip install fastapi uvicorn streamlit requests numpy sentence-transformers
```

The AI/search models may download from Hugging Face the first time they are used.

## 10. How to Run FastAPI

Open PowerShell and go to:

```powershell
cd C:\path\to\course-enrolment-assistant\Task1
```

Run:

```powershell
uvicorn api:app --reload
```

FastAPI:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

Keep this terminal running.

## 11. How to Run Streamlit

Open a second PowerShell window:

```powershell
cd C:\path\to\course-enrolment-assistant\Task1
```

Run:

```powershell
streamlit run app.py
```

Streamlit normally opens:

```text
http://localhost:8501
```

For the complete application, start **FastAPI first** and then **Streamlit**.

## 12. Task 10 Result — 6/6 Passed

| Request | Expected | Found | Reason | Handbook pages | Result |
|---|---|---|---|---|---|
| R1 | CS201 | CS201 | CS101 prerequisite not completed | prerequisites.md, advice.md | PASS |
| R2 | CS310 | CS310 | full, 25 of 25 | capacity.md, advice.md | PASS |
| R3 | CS202 | CS202 | clashes with MA150 Wed 14:00 | timetable.md | PASS |
| R4 | CS301 | CS301 | fees are unpaid; would be 65 credits, limit 60 | fees.md, credit_limit.md | PASS |
| R5 | CS301 | CS301 | CS201 grade 48, needs 55 | prerequisites.md, advice.md, waivers.md | PASS |
| R6 | DS220 | DS220 | No blocking reason | advice.md | PASS |

### Final result

```text
Tests Passed: 6/6
```

All six requests matched the expected course, reasons, handbook pages, and validated reply.

## 13. Example Output

### Blocked enrolment

For `S-102` requesting `CS301`:

```text
Course identified: CS301 - Machine Learning

Enrolment blocked.

Reasons:
- fees are unpaid
- would be 65 credits, limit 60

Handbook Pages:
- fees.md
- credit_limit.md
```

Final reply:

```text
The following issues prevent enrolment:
- fees are unpaid
- would be 65 credits, limit 60

Relevant handbook page(s):
- fees.md
- credit_limit.md
```

### Approved enrolment

For `S-106` requesting `DS220`:

```text
Course identified: DS220 - Data Visualisation

There are no blocking reasons for enrolment.

Relevant handbook page(s):
- advice.md
```

## 14. GitHub Project Usage

Repository:

https://github.com/gsairaja1/course-enrolment-assistant

After making changes:

```powershell
git status
git add .
git commit -m "Describe your change"
git push
```

The `main` branch contains the project source code, data, handbook documents, test requests, and SQLite database.

## Architecture Summary

```text
                  ┌─────────────────────┐
                  │      Student        │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │     Streamlit       │
                  │       app.py        │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │       ai.py         │
                  │ Course identification│
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │       api.py        │
                  │     FastAPI API     │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │      rules.py       │
                  │ 5 enrolment rules   │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │   enrolment.db      │
                  │      SQLite         │
                  └──────────┬──────────┘
                             │
                             ▼
                     Verified reasons
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
       ┌──────────────┐              ┌──────────────┐
       │  search.py   │              │   reply.py   │
       │   Handbook   │              │ AI response  │
       │    search    │              │ + validation │
       └──────┬───────┘              └──────┬───────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
                  ┌─────────────────────┐
                  │ Validated final     │
                  │ student response    │
                  └─────────────────────┘
```

## License

No open-source license has been added to this repository yet.
