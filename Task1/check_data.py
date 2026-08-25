from pathlib import Path
import csv
# --------------------------------------------------
# 1. FIND THE DATA FOLDER
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# --------------------------------------------------
# 2. CSV FILES
# --------------------------------------------------

FILES = [
    "students.csv",
    "courses.csv",
    "prerequisites.csv",
    "enrolments.csv",
    "current_numbers.csv"
]


# --------------------------------------------------
# 3. READ CSV FILE
# --------------------------------------------------

def read_csv(filename):
    path = DATA_DIR / filename

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        rows = list(reader)

        return reader.fieldnames, rows


# --------------------------------------------------
# 4. CHECK EMPTY VALUES
# --------------------------------------------------

def check_empty_values(filename, headers, rows):
    problems = []

    for row_number, row in enumerate(rows, start=2):

        for column in headers:

            value = row.get(column, "")

            if value is None or value.strip() == "":
                problems.append(
                    f"{filename}, row {row_number}: "
                    f"'{column}' is empty"
                )

    return problems


# --------------------------------------------------
# 5. CHECK INCONSISTENT CAPITALISATION
# --------------------------------------------------

def check_inconsistent_values(filename, headers, rows):
    problems = []

    for column in headers:

        values = []

        for row in rows:
            value = row.get(column, "")

            if value is not None and value.strip() != "":
                values.append(value.strip())

        # Group values ignoring capitalisation
        groups = {}

        for value in values:
            key = value.lower()

            if key not in groups:
                groups[key] = set()

            groups[key].add(value)

        for key, different_values in groups.items():

            if len(different_values) > 1:
                problems.append(
                    f"{filename}: column '{column}' has "
                    f"inconsistent values: {sorted(different_values)}"
                )

    return problems


# --------------------------------------------------
# 6. LOAD ALL CSV FILES
# --------------------------------------------------

data = {}

print("\nCOURSE ENROLMENT ASSISTANT")
print("TASK 1 - DATA CHECK")
print("=" * 50)

for filename in FILES:

    try:
        headers, rows = read_csv(filename)

        data[filename] = {
            "headers": headers,
            "rows": rows
        }

        print(f"{filename}: {len(rows)} rows")

    except FileNotFoundError:
        print(f"ERROR: {filename} was not found.")
    except Exception as error:
        print(f"ERROR reading {filename}: {error}")


# --------------------------------------------------
# 7. CHECK EMPTY VALUES AND INCONSISTENCIES
# --------------------------------------------------

all_problems = []

print("\n")
print("CHECKING DATA")
print("=" * 50)

for filename, information in data.items():

    headers = information["headers"]
    rows = information["rows"]

    empty_problems = check_empty_values(
        filename,
        headers,
        rows
    )

    inconsistent_problems = check_inconsistent_values(
        filename,
        headers,
        rows
    )

    all_problems.extend(empty_problems)
    all_problems.extend(inconsistent_problems)


# --------------------------------------------------
# 8. CHECK STUDENT IDs
# --------------------------------------------------

if "students.csv" in data and "enrolments.csv" in data:

    student_rows = data["students.csv"]["rows"]
    enrolment_rows = data["enrolments.csv"]["rows"]

    student_ids = set()

    for row in student_rows:

        for column in row:

            if "student" in column.lower() and "id" in column.lower():
                value = row[column].strip()

                if value:
                    student_ids.add(value)

    for row_number, row in enumerate(enrolment_rows, start=2):

        for column in row:

            if "student" in column.lower() and "id" in column.lower():

                student_id = row[column].strip()

                if student_id and student_id not in student_ids:

                    all_problems.append(
                        f"enrolments.csv, row {row_number}: "
                        f"student ID '{student_id}' does not exist "
                        f"in students.csv"
                    )


# --------------------------------------------------
# 9. CHECK COURSE CODES
# --------------------------------------------------

if "courses.csv" in data:

    course_rows = data["courses.csv"]["rows"]

    course_codes = set()

    for row in course_rows:

        for column in row:

            column_name = column.lower()

            if (
                "course" in column_name
                and "code" in column_name
            ):
                value = row[column].strip()

                if value:
                    course_codes.add(value)


    # Check enrolments
    if "enrolments.csv" in data:

        enrolment_rows = data["enrolments.csv"]["rows"]

        for row_number, row in enumerate(
            enrolment_rows,
            start=2
        ):

            for column in row:

                column_name = column.lower()

                if (
                    "course" in column_name
                    and "code" in column_name
                ):

                    course_code = row[column].strip()

                    if (
                        course_code
                        and course_code not in course_codes
                    ):

                        all_problems.append(
                            f"enrolments.csv, row {row_number}: "
                            f"course code '{course_code}' does not "
                            f"exist in courses.csv"
                        )


# --------------------------------------------------
# 10. CHECK GRADES IN ENROLMENTS
# --------------------------------------------------

if "enrolments.csv" in data:

    enrolment_rows = data["enrolments.csv"]["rows"]

    for row_number, row in enumerate(
        enrolment_rows,
        start=2
    ):

        status = ""
        grade = ""

        for column in row:

            column_name = column.lower()

            if "status" in column_name:
                status = row[column].strip().lower()

            if "grade" in column_name:
                grade = row[column].strip()


        # Completed courses should have a grade
        if "completed" in status and not grade:

            all_problems.append(
                f"enrolments.csv, row {row_number}: "
                f"completed course has no grade"
            )


        # Currently enrolled courses should not have a grade
        if "enrolled" in status and grade:

            all_problems.append(
                f"enrolments.csv, row {row_number}: "
                f"currently enrolled course has a grade"
            )


# --------------------------------------------------
# 11. PRINT FINAL REPORT
# --------------------------------------------------

print("\n")
print("FINAL DATA QUALITY REPORT")
print("=" * 50)

if len(all_problems) == 0:

    print("No problems found.")

else:

    for number, problem in enumerate(
        all_problems,
        start=1
    ):

        print(f"{number}. {problem}")


print("\n")
print("=" * 50)
print(f"TOTAL PROBLEMS FOUND: {len(all_problems)}")
print("=" * 50)