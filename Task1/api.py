from pathlib import Path
import sqlite3
import json

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from rules import (
    fees_block,
    prerequisite_block,
    capacity_block,
    clash_block,
    credit_block
)


# --------------------------------------------------
# APP
# --------------------------------------------------

app = FastAPI(
    title="Course Enrolment Assistant",
    description="API for checking course enrolment rules"
)


# --------------------------------------------------
# DATABASE
# --------------------------------------------------

DB_PATH = Path(__file__).resolve().parent / "enrolment.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# --------------------------------------------------
# CONSISTENT ERROR RESPONSE
# --------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": exc.status_code,
            "error": exc.detail
        }
    )


# --------------------------------------------------
# 1. GET STUDENT
# --------------------------------------------------

@app.get("/students/{student_id}")
def get_student(student_id: str):

    connection = get_connection()

    try:
        row = connection.execute("""
            SELECT
                student_id,
                name,
                year,
                programme,
                fees_status
            FROM students
            WHERE student_id = ?
        """, (student_id,)).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail=f"Student '{student_id}' not found"
            )

        return {
            "status": 200,
            "data": dict(row)
        }

    finally:
        connection.close()


# --------------------------------------------------
# 2. GET STUDENT ENROLMENTS
# --------------------------------------------------

@app.get("/students/{student_id}/enrolments")
def get_student_enrolments(student_id: str):

    connection = get_connection()

    try:
        student = connection.execute("""
            SELECT student_id
            FROM students
            WHERE student_id = ?
        """, (student_id,)).fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail=f"Student '{student_id}' not found"
            )

        rows = connection.execute("""
            SELECT
                e.course_code,
                c.title,
                c.credits,
                e.status,
                e.grade
            FROM enrolments AS e
            JOIN courses AS c
                ON c.course_code = e.course_code
            WHERE e.student_id = ?
            ORDER BY e.course_code
        """, (student_id,)).fetchall()

        return {
            "status": 200,
            "data": {
                "student_id": student_id,
                "enrolments": [dict(row) for row in rows]
            }
        }

    finally:
        connection.close()


# --------------------------------------------------
# 3. GET ALL COURSES
# --------------------------------------------------

@app.get("/courses")
def get_courses():

    connection = get_connection()

    try:
        rows = connection.execute("""
            SELECT
                c.course_code,
                c.title,
                c.credits,
                c.capacity,
                c.term,
                c.day,
                c.start,
                c.end,
                COALESCE(n.enrolled_now, 0) AS enrolled_now
            FROM courses AS c
            LEFT JOIN current_numbers AS n
                ON n.course_code = c.course_code
            ORDER BY c.course_code
        """).fetchall()

        courses = []

        for row in rows:
            course = dict(row)

            course["full"] = (
                course["enrolled_now"] >= course["capacity"]
            )

            courses.append(course)

        return {
            "status": 200,
            "data": courses
        }

    finally:
        connection.close()


# --------------------------------------------------
# 4. GET ONE COURSE
# --------------------------------------------------

@app.get("/courses/{course_code}")
def get_course(course_code: str):

    connection = get_connection()

    try:
        course = connection.execute("""
            SELECT
                c.course_code,
                c.title,
                c.credits,
                c.capacity,
                c.term,
                c.day,
                c.start,
                c.end,
                COALESCE(n.enrolled_now, 0) AS enrolled_now
            FROM courses AS c
            LEFT JOIN current_numbers AS n
                ON n.course_code = c.course_code
            WHERE c.course_code = ?
        """, (course_code,)).fetchone()

        if course is None:
            raise HTTPException(
                status_code=404,
                detail=f"Course '{course_code}' not found"
            )

        prerequisites = connection.execute("""
            SELECT
                requires,
                minimum_grade
            FROM prerequisites
            WHERE course_code = ?
            ORDER BY requires
        """, (course_code,)).fetchall()

        result = dict(course)

        result["full"] = (
            result["enrolled_now"] >= result["capacity"]
        )

        result["prerequisites"] = [
            dict(row) for row in prerequisites
        ]

        return {
            "status": 200,
            "data": result
        }

    finally:
        connection.close()


# --------------------------------------------------
# 5. CHECK ENROLMENT
# --------------------------------------------------

@app.get("/check/{student_id}/{course_code}")
def check_enrolment(
    student_id: str,
    course_code: str
):

    connection = get_connection()

    try:
        student = connection.execute("""
            SELECT student_id
            FROM students
            WHERE student_id = ?
        """, (student_id,)).fetchone()

        if student is None:
            raise HTTPException(
                status_code=404,
                detail=f"Student '{student_id}' not found"
            )

        course = connection.execute("""
            SELECT course_code
            FROM courses
            WHERE course_code = ?
        """, (course_code,)).fetchone()

        if course is None:
            raise HTTPException(
                status_code=404,
                detail=f"Course '{course_code}' not found"
            )

    finally:
        connection.close()

    # Run ALL FIVE rules
    results = {
        "fees": fees_block(student_id),
        "prerequisite": prerequisite_block(
            student_id,
            course_code
        ),
        "capacity": capacity_block(course_code),
        "clash": clash_block(
            student_id,
            course_code
        ),
        "credit": credit_block(
            student_id,
            course_code
        )
    }

    reasons = [
        reason
        for reason in results.values()
        if reason is not None
    ]

    return {
        "status": 200,
        "data": {
            "student_id": student_id,
            "course_code": course_code,
            "allowed": len(reasons) == 0,
            "rules": results,
            "reasons": reasons
        }
    }


# --------------------------------------------------
# 6. GET REQUEST
# --------------------------------------------------

@app.get("/requests/{request_id}")
def get_request(request_id: str):

    requests_dir = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "requests"
    )

    request_file = requests_dir / f"{request_id}.json"

    if not request_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Request '{request_id}' not found"
        )

    try:
        with open(
            request_file,
            "r",
            encoding="utf-8"
        ) as file:

            request_data = json.load(file)

        return {
            "status": 200,
            "data": request_data
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Invalid JSON in request '{request_id}'"
        )