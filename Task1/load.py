from pathlib import Path
import csv
import sqlite3


# --------------------------------------------------
# 1. PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(__file__).resolve().parent / "enrolment.db"


# --------------------------------------------------
# 2. READ CSV
# --------------------------------------------------

def read_csv(filename):
    path = DATA_DIR / filename

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# 3. CONNECT TO DATABASE
# --------------------------------------------------

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# Enable foreign keys
cursor.execute("PRAGMA foreign_keys = ON")


# --------------------------------------------------
# 4. REMOVE OLD TABLES
# --------------------------------------------------

cursor.execute("DROP TABLE IF EXISTS current_numbers")
cursor.execute("DROP TABLE IF EXISTS enrolments")
cursor.execute("DROP TABLE IF EXISTS prerequisites")
cursor.execute("DROP TABLE IF EXISTS courses")
cursor.execute("DROP TABLE IF EXISTS students")


# --------------------------------------------------
# 5. CREATE STUDENTS TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE students (
    student_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    year INTEGER,
    programme TEXT NOT NULL,
    fees_status TEXT NOT NULL
)
""")


# --------------------------------------------------
# 6. CREATE COURSES TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE courses (
    course_code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL,
    capacity INTEGER NOT NULL,
    term TEXT NOT NULL,
    day TEXT NOT NULL,
    start TEXT NOT NULL,
    end TEXT NOT NULL
)
""")


# --------------------------------------------------
# 7. CREATE PREREQUISITES TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE prerequisites (
    course_code TEXT NOT NULL,
    requires TEXT NOT NULL,
    minimum_grade INTEGER NOT NULL,

    PRIMARY KEY (course_code, requires),

    FOREIGN KEY (course_code)
        REFERENCES courses(course_code),

    FOREIGN KEY (requires)
        REFERENCES courses(course_code)
)
""")


# --------------------------------------------------
# 8. CREATE ENROLMENTS TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE enrolments (
    student_id TEXT NOT NULL,
    course_code TEXT NOT NULL,
    status TEXT NOT NULL,
    grade INTEGER,

    PRIMARY KEY (student_id, course_code),

    FOREIGN KEY (student_id)
        REFERENCES students(student_id),

    FOREIGN KEY (course_code)
        REFERENCES courses(course_code)
)
""")


# --------------------------------------------------
# 9. CREATE CURRENT NUMBERS TABLE
# --------------------------------------------------

cursor.execute("""
CREATE TABLE current_numbers (
    course_code TEXT PRIMARY KEY,
    enrolled_now INTEGER NOT NULL,

    FOREIGN KEY (course_code)
        REFERENCES courses(course_code)
)
""")


# --------------------------------------------------
# 10. LOAD STUDENTS
# --------------------------------------------------

students = read_csv("students.csv")

for row in students:

    # Task 1 problem:
    # Missing year is stored as NULL.
    year = row["year"].strip()

    if year == "":
        year = None
    else:
        year = int(year)

    # Task 1 problem:
    # Normalize PAID / paid to lowercase.
    fees_status = row["fees_status"].strip().lower()

    cursor.execute("""
        INSERT INTO students
        (student_id, name, year, programme, fees_status)
        VALUES (?, ?, ?, ?, ?)
    """, (
        row["student_id"].strip(),
        row["name"].strip(),
        year,
        row["programme"].strip(),
        fees_status
    ))


# --------------------------------------------------
# 11. LOAD COURSES
# --------------------------------------------------

courses = read_csv("courses.csv")

for row in courses:

    cursor.execute("""
        INSERT INTO courses
        (course_code, title, credits, capacity, term, day, start, end)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        row["course_code"].strip(),
        row["title"].strip(),
        int(row["credits"]),
        int(row["capacity"]),
        row["term"].strip().lower(),
        row["day"].strip(),
        row["start"].strip(),
        row["end"].strip()
    ))


# --------------------------------------------------
# 12. LOAD PREREQUISITES
# --------------------------------------------------

prerequisites = read_csv("prerequisites.csv")

for row in prerequisites:

    cursor.execute("""
        INSERT INTO prerequisites
        (course_code, requires, minimum_grade)
        VALUES (?, ?, ?)
    """, (
        row["course_code"].strip(),
        row["requires"].strip(),
        int(row["minimum_grade"])
    ))


# --------------------------------------------------
# 13. LOAD ENROLMENTS
# --------------------------------------------------

enrolments = read_csv("enrolments.csv")

for row in enrolments:

    status = row["status"].strip().lower()

    grade_text = row["grade"].strip()

    if grade_text == "":
        grade = None
    else:
        grade = int(grade_text)

    # Completed courses must have a grade.
    if status == "completed" and grade is None:
        raise ValueError(
            f"Completed enrolment has no grade: "
            f"{row['student_id']} - {row['course_code']}"
        )

    # Current enrolments must not have a grade.
    if status == "enrolled" and grade is not None:
        raise ValueError(
            f"Current enrolment has a grade: "
            f"{row['student_id']} - {row['course_code']}"
        )

    cursor.execute("""
        INSERT INTO enrolments
        (student_id, course_code, status, grade)
        VALUES (?, ?, ?, ?)
    """, (
        row["student_id"].strip(),
        row["course_code"].strip(),
        status,
        grade
    ))


# --------------------------------------------------
# 14. LOAD CURRENT NUMBERS
# --------------------------------------------------

current_numbers = read_csv("current_numbers.csv")

for row in current_numbers:

    cursor.execute("""
        INSERT INTO current_numbers
        (course_code, enrolled_now)
        VALUES (?, ?)
    """, (
        row["course_code"].strip(),
        int(row["enrolled_now"])
    ))


# --------------------------------------------------
# 15. SAVE DATABASE
# --------------------------------------------------

connection.commit()


# --------------------------------------------------
# 16. CHECK ROW COUNTS
# --------------------------------------------------

tables = [
    "students",
    "courses",
    "prerequisites",
    "enrolments",
    "current_numbers"
]

print("\nTASK 2 - DATABASE CREATED")
print("=" * 50)

for table in tables:

    cursor.execute(f"SELECT COUNT(*) FROM {table}")

    count = cursor.fetchone()[0]

    print(f"{table}: {count} rows")


print("\nDatabase location:")
print(DB_PATH)

print("\nTask 2 completed successfully.")


# --------------------------------------------------
# 17. CLOSE DATABASE
# --------------------------------------------------

connection.close()