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
# READ AND CHUNK HANDBOOK FILES
# --------------------------------------------------

documents = []

# Number of words in each searchable chunk.
# Smaller chunks make retrieval more focused than
# embedding one entire handbook file.
CHUNK_SIZE = 150

for file_path in sorted(HANDBOOK_DIR.glob("*.md")):

    text = file_path.read_text(
        encoding="utf-8"
    ).strip()

    if not text:
        continue

    words = text.split()

    for start in range(0, len(words), CHUNK_SIZE):

        chunk = " ".join(
            words[start:start + CHUNK_SIZE]
        ).strip()

        if chunk:

            documents.append({
                "filename": file_path.name,
                "text": chunk
            })


print(
    f"Loaded {len(documents)} handbook chunks."
)


# --------------------------------------------------
# CREATE VECTORS
# --------------------------------------------------

if documents:

    texts = [
        document["text"]
        for document in documents
    ]

    document_vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

else:

    document_vectors = np.empty(
        (0, 384),
        dtype=np.float32
    )


# --------------------------------------------------
# SEARCH FUNCTION
# --------------------------------------------------

def search(question, k=3):
    """
    Search the handbook using semantic/vector similarity.

    Returns the best matching handbook chunks with:
    - file
    - text
    - similarity score
    """

    if not documents:

        return []

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
            "text": documents[index]["text"],
            "score": round(
                float(scores[index]),
                3
            )
        })

    return results


# --------------------------------------------------
# TEST SEARCH
# --------------------------------------------------

if __name__ == "__main__":

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
    print("TASK 7 - HANDBOOK VECTOR SEARCH TEST")
    print("=" * 70)


    passed = 0


    # --------------------------------------------------
    # RUN ALL FIVE TESTS
    # --------------------------------------------------

    for number, test in enumerate(
        tests,
        start=1
    ):

        print()
        print(
            f"TEST {number}: {test['rule']}"
        )
        print("-" * 70)

        print("Question:")
        print(test["question"])

        print()
        print("Top 3 results:")

        results = search(
            test["question"],
            k=3
        )

        if not results:

            print("No handbook results found.")
            print("RESULT: FAIL")
            continue

        for position, result in enumerate(
            results,
            start=1
        ):

            print(
                f"{position}. "
                f"{result['file']} "
                f"{result['score']}"
            )

            print(
                f"   Text: {result['text'][:200]}..."
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
                "The vector search ranked a different "
                "handbook file first."
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
            "All five handbook vector searches passed."
        )

    else:

        print(
            "Some searches need better questions, "
            "chunks, or handbook content."
        )

    print("=" * 70)
