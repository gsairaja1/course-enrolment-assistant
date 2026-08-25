from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np


# --------------------------------------------------
# PATHS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

HANDBOOK_DIR = BASE_DIR / "data" / "handbook"


# --------------------------------------------------
# LOAD SEARCH MODEL
# --------------------------------------------------

print("Loading search model...")


model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

print("Search model loaded.")


# --------------------------------------------------
# READ HANDBOOK FILES
# --------------------------------------------------

documents = []

for file_path in sorted(HANDBOOK_DIR.glob("*.md")):

    text = file_path.read_text(
        encoding="utf-8"
    ).strip()

    if text:

        documents.append({
            "filename": file_path.name,
            "text": text
        })


print(
    f"Loaded {len(documents)} handbook files."
)


# --------------------------------------------------
# CREATE VECTORS
# --------------------------------------------------

texts = [
    document["text"]
    for document in documents
]

document_vectors = model.encode(
    texts,
    normalize_embeddings=True
)


# --------------------------------------------------
# SEARCH FUNCTION
# --------------------------------------------------

def search(question, k=3):
    """
    Search the handbook and return the best
    matching files with similarity scores.
    """

    question_vector = model.encode(
        [question],
        normalize_embeddings=True
    )[0]

    # Because both vectors are normalized,
    # dot product = cosine similarity.
    scores = np.dot(
        document_vectors,
        question_vector
    )

    ranked_indexes = np.argsort(
        scores
    )[::-1]

    results = []

    for index in ranked_indexes[:k]:

        results.append({
            "file": documents[index]["filename"],
            "score": round(
                float(scores[index]),
                2
            )
        })

    return results


# --------------------------------------------------
# TEST SEARCH
# --------------------------------------------------

if __name__ == "__main__":

    # --------------------------------------------------
    # TASK 7 - TEST ALL FIVE RULES
    # --------------------------------------------------

    tests = [
        {
            "rule": "Fees",
            "question": (
                "student has unpaid fees "
                "and wants to enrol in a course"
            ),
            "expected": "fees.md"
        },

        {
            "rule": "Prerequisite",
            "question": (
                "student completed the course "
                "but the grade was below the minimum"
            ),
            "expected": "prerequisites.md"
        },

        {
            "rule": "Capacity",
            "question": (
                "the course is full "
                "and there are no available places"
            ),
            "expected": "capacity.md"
        },

        {
            "rule": "Clash",
            "question": (
                "student's requested course "
                "overlaps with another course"
            ),
            "expected": "timetable.md"
        },

        {
            "rule": "Credit",
            "question": (
                "student would exceed "
                "the maximum credit limit"
            ),
            "expected": "credit_limit.md"
        }
    ]


    # --------------------------------------------------
    # PRINT HEADER
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("TASK 7 - HANDBOOK SEARCH TEST")
    print("=" * 70)


    passed = 0


    # --------------------------------------------------
    # RUN ALL FIVE TESTS
    # --------------------------------------------------

    for number, test in enumerate(tests, start=1):

        print()
        print(f"TEST {number}: {test['rule']}")
        print("-" * 70)

        print("Question:")
        print(test["question"])

        print()
        print("Top 3 results:")

        results = search(
            test["question"],
            k=3
        )

        for position, result in enumerate(
            results,
            start=1
        ):

            print(
                f"{position}. "
                f"{result['file']} "
                f"{result['score']}"
            )


        # --------------------------------------------------
        # CHECK WHETHER CORRECT FILE IS FIRST
        # --------------------------------------------------

        first_file = results[0]["file"]

        print()

        print(
            f"Expected first: {test['expected']}"
        )

        print(
            f"Actual first:   {first_file}"
        )


        if first_file == test["expected"]:

            print("RESULT: PASS")

            passed += 1

        else:

            print("RESULT: FAIL")

            print(
                "This question may need improvement."
            )


    # --------------------------------------------------
    # FINAL SUMMARY
    # --------------------------------------------------

    print()
    print("=" * 70)
    print("TASK 7 FINAL SUMMARY")
    print("=" * 70)

    print(
        f"Passed: {passed}/{len(tests)}"
    )

    if passed == len(tests):

        print(
            "All five handbook searches passed."
        )

    else:

        print(
            "Some searches need better questions."
        )

    print("=" * 70)