from pathlib import Path
import sqlite3


# --------------------------------------------------
# DATABASE PATH
# --------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "enrolment.db"


# --------------------------------------------------
# DATABASE CONNECTION
# -----------------------------------------------

def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# --------------------------------------------------
# 1. FEES RULE
# --------------------------------------------------

def fees_block(student_id):
    """
    Return 'fees are unpaid' if the student's fees
    are not paid. Otherwise return None.
    """

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT fees_status
            FROM students
            WHERE student_id = ?
        """, (student_id,)).fetchone()

        if row is None:
            return None

        if row["fees_status"].strip().lower() != "paid":
            return "fees are unpaid"

        return None

    finally:
        connection.close()


# --------------------------------------------------
# 2. PREREQUISITE RULE
# --------------------------------------------------

def prerequisite_block(student_id, course):
    """
    Check all prerequisites for the requested course.

    A prerequisite is satisfied only when the student
    has COMPLETED it and achieved the required grade.

    Returns a short reason if a prerequisite is missing
    or the grade is too low. Otherwise returns None.
    """

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                p.requires,
                p.minimum_grade,
                e.grade,
                e.status
            FROM prerequisites AS p
            LEFT JOIN enrolments AS e
                ON e.course_code = p.requires
                AND e.student_id = ?
            WHERE p.course_code = ?
        """, (student_id, course)).fetchall()

        for row in rows:

            # No completed prerequisite
            if row["status"] != "completed":
                return (
                    f"{row['requires']} prerequisite not completed"
                )

            # Completed but grade too low
            if row["grade"] < row["minimum_grade"]:
                return (
                    f"{row['requires']} grade "
                    f"{row['grade']}, needs "
                    f"{row['minimum_grade']}"
                )

        return None

    finally:
        connection.close()


# --------------------------------------------------
# 3. CAPACITY RULE
# --------------------------------------------------

def capacity_block(course):
    """
    Check whether the requested course is full.

    Returns 'full, X of Y' if full.
    Otherwise returns None.
    """

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT
                c.capacity,
                n.enrolled_now
            FROM courses AS c
            JOIN current_numbers AS n
                ON n.course_code = c.course_code
            WHERE c.course_code = ?
        """, (course,)).fetchone()

        if row is None:
            return None

        if row["enrolled_now"] >= row["capacity"]:
            return (
                f"full, {row['enrolled_now']} "
                f"of {row['capacity']}"
            )

        return None

    finally:
        connection.close()


# --------------------------------------------------
# 4. TIMETABLE CLASH RULE
# --------------------------------------------------

def clash_block(student_id, course):
    """
    Check whether the requested course overlaps with
    any course the student is currently taking.

    Two courses clash when:
    - they are on the same day, AND
    - their times overlap.

    Returns a reason if a clash exists.
    Otherwise returns None.
    """

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT
                requested.course_code AS requested_course,
                existing.course_code AS existing_course,
                existing_course.title AS existing_title,
                existing_course.day AS existing_day,
                existing_course.start AS existing_start,
                existing_course.end AS existing_end
            FROM courses AS requested
            JOIN courses AS existing_course
                ON existing_course.day = requested.day
            JOIN enrolments AS existing
                ON existing.course_code = existing_course.course_code
                AND existing.student_id = ?
                AND existing.status = 'enrolled'
            WHERE requested.course_code = ?

              AND requested.start < existing_course.end
              AND existing_course.start < requested.end

            LIMIT 1
        """, (student_id, course)).fetchone()

        if row is None:
            return None

        return (
            f"clashes with {row['existing_course']} "
            f"{row['existing_day']} {row['existing_start']}"
        )

    finally:
        connection.close()


# --------------------------------------------------
# 5. CREDIT LIMIT RULE
# --------------------------------------------------

def credit_block(student_id, course):
    """
    Calculate the student's current credits plus
    the credits of the requested course.

    Only courses currently being taken count.

    Maximum allowed = 60 credits.
    """

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT
                COALESCE(SUM(c.credits), 0) AS current_credits,
                requested.credits AS requested_credits
            FROM courses AS requested
            LEFT JOIN enrolments AS e
                ON e.student_id = ?
                AND e.status = 'enrolled'
            LEFT JOIN courses AS c
                ON c.course_code = e.course_code
            WHERE requested.course_code = ?
            GROUP BY requested.course_code, requested.credits
        """, (student_id, course)).fetchone()

        if row is None:
            return None

        total_credits = (
            row["current_credits"]
            + row["requested_credits"]
        )

        if total_credits > 60:
            return (
                f"would be {total_credits} credits, "
                f"limit 60"
            )

        return None

    finally:
        connection.close()


# --------------------------------------------------
# TEST ALL FIVE RULES
# --------------------------------------------------

# --------------------------------------------------
# TEST ALL SIX REQUESTS
# --------------------------------------------------

if __name__ == "__main__":

    requests = [
        ("R1", "S-104", "CS201"),
        ("R2", "S-101", "CS310"),
        ("R3", "S-103", "CS202"),
        ("R4", "S-102", "CS301"),
        ("R5", "S-105", "CS301"),
        ("R6", "S-106", "DS220"),
    ]

    print("TASK 3 - FIVE RULES TEST")
    print("=" * 60)

    for request_id, student_id, course in requests:

        print()
        print(f"{request_id}: {student_id} wants {course}")
        print("-" * 60)

        fees = fees_block(student_id)
        prerequisite = prerequisite_block(student_id, course)
        capacity = capacity_block(course)
        clash = clash_block(student_id, course)
        credit = credit_block(student_id, course)

        print("Fees:", fees)
        print("Prerequisite:", prerequisite)
        print("Capacity:", capacity)
        print("Clash:", clash)
        print("Credit limit:", credit)