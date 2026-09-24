
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np


# ==================================================
# PATH CONFIGURATION
# ==================================================

# Get the directory where this Python file is located.
BASE_DIR = Path(__file__).resolve().parent.parent

HANDBOOK_DIR = BASE_DIR / "data" / "handbook"


# ==================================================
# LOAD SENTENCE TRANSFORMER SEARCH MODEL
 # ==================================================

print("Loading search model...")

# Load the BGE-small embedding model.
#
# This model converts text into numerical vectors
# called embeddings. Similar meanings produce vectors
# that are close to each other.
model = SentenceTransformer(
    "BAAI/bge-small-en-v1.5"
)

print("Search model loaded.")


# ==================================================
# READ AND CHUNK HANDBOOK FILES
# ==================================================

# This list stores all searchable handbook chunks.
#
# Each item will contain:
# - filename
# - text
documents = []


# Number of words in each searchable chunk.
#
# We split large handbook documents into smaller pieces
# so that search can return a more specific section
# instead of returning an entire handbook file.
CHUNK_SIZE = 150


# Find all Markdown handbook files.
#
# sorted() keeps the file processing order consistent.
for file_path in sorted(HANDBOOK_DIR.glob("*.md")):

    # Read the complete handbook file as UTF-8 text.
    text = file_path.read_text(
        encoding="utf-8"
    ).strip()

    # Skip empty files.
    if not text:
        continue

    # Split the document into individual words.
    words = text.split()


    # Create chunks of CHUNK_SIZE words.
    #
    # Example:
    # If a file contains 450 words and CHUNK_SIZE = 150,
    # it will create 3 searchable chunks.
    for start in range(0, len(words), CHUNK_SIZE):

        # Select the current group of words
        # and combine them back into a text string.
        chunk = " ".join(
            words[start:start + CHUNK_SIZE]
        ).strip()


        # Store only non-empty chunks.
        if chunk:

            documents.append({
                "filename": file_path.name,
                "text": chunk
            })


# Display the total number of searchable chunks.
print(
    f"Loaded {len(documents)} handbook chunks."
)


# ==================================================
# CREATE EMBEDDINGS / VECTORS
# ==================================================

# Check whether at least one handbook chunk exists.
if documents:

    # Extract only the text from each document chunk.
    texts = [
        document["text"]
        for document in documents
    ]


    # Convert every handbook chunk into an embedding vector.
    #
    # normalize_embeddings=True converts vectors to
    # unit length. This allows us to use a dot product
    # as cosine similarity later during search.
    document_vectors = model.encode(
        texts,
        normalize_embeddings=True
    )

else:

    # If there are no documents, create an empty
    # NumPy array with the expected embedding size.
    #
    # BAAI/bge-small-en-v1.5 produces 384-dimensional
    # embeddings.
    document_vectors = np.empty(
        (0, 384),
        dtype=np.float32
    )


# ==================================================
# SEMANTIC SEARCH FUNCTION
# ==================================================

def search(question, k=3):
    """
    Search the handbook using semantic/vector similarity.

    Parameters:
        question: User's question as a string.
        k: Number of top matching chunks to return.

    Returns:
        A list containing the best matching handbook
        chunks along with their similarity scores.
    """

    # If there are no handbook documents,
    # there is nothing to search.
    if not documents:
        return []


    # Convert the user's question into an embedding.
    #
    # The prefix tells the BGE model that this text
    # is a search query and should be matched against
    # relevant passages.
    question_vector = model.encode(
        [
            f"Represent this sentence for searching "
            f"relevant passages: {question}"
        ],
        normalize_embeddings=True
    )[0]


    # Calculate similarity between the question vector
    # and every handbook chunk vector.
    #
    # Because both vectors are normalized,
    # their dot product is equivalent to cosine similarity.
    scores = np.dot(
        document_vectors,
        question_vector
    )


    # Sort the document indexes from highest similarity
    # score to lowest similarity score.
    ranked_indexes = np.argsort(
        scores
    )[::-1]


    # Store the final search results.
    results = []


    # Take only the top k matching documents.
    for index in ranked_indexes[:k]:

        results.append({
            # Name of the handbook file.
            "file": documents[index]["filename"],

            # Text of the matching handbook chunk.
            "text": documents[index]["text"],

            # Similarity score rounded to 3 decimal places.
            "score": round(
                float(scores[index]),
                3
            )
        })


    # Return the ranked search results.
    return results


# ==================================================
# SEARCH TESTS
# ==================================================

# Run these tests only when this file is executed
# directly.
#
# If this file is imported by another Python file,
# the tests below will not automatically execute.
if __name__ == "__main__":

    # Five test cases are used to verify that semantic
    # search can identify the correct handbook file.
    tests = [

        # ----------------------------------------------
        # TEST 1: FEES
        # ----------------------------------------------
        {
            "rule": "Fees",

            "question": (
                "student has unpaid fees "
                "and wants to enrol in a course"
            ),

            "expected": "fees.md"
        },


        # ----------------------------------------------
        # TEST 2: PREREQUISITE
        # ----------------------------------------------
        {
            "rule": "Prerequisite",

            "question": (
                "student completed the course "
                "but the grade was below the minimum"
            ),

            "expected": "prerequisites.md"
        },


        # ----------------------------------------------
        # TEST 3: CAPACITY
        # ----------------------------------------------
        {
            "rule": "Capacity",

            "question": (
                "the course is full "
                "and there are no available places"
            ),

            "expected": "capacity.md"
        },


        # ----------------------------------------------
        # TEST 4: TIMETABLE CLASH
        # ----------------------------------------------
        {
            "rule": "Clash",

            "question": (
                "student's requested course "
                "overlaps with another course"
            ),

            "expected": "timetable.md"
        },


        # ----------------------------------------------
        # TEST 5: CREDIT LIMIT
        # ----------------------------------------------
        {
            "rule": "Credit",

            "question": (
                "student would exceed "
                "the maximum credit limit"
            ),

            "expected": "credit_limit.md"
        }
    ]


    # ==================================================
    # PRINT TEST HEADER
    # ==================================================

    print()
    print("=" * 70)
    print("TASK 7 - HANDBOOK VECTOR SEARCH TEST")
    print("=" * 70)


    # Counter used to track how many tests pass.
    passed = 0


    # ==================================================
    # RUN ALL TESTS
    # ==================================================

    for number, test in enumerate(
        tests,
        start=1
    ):

        print()
        print(
            f"TEST {number}: {test['rule']}"
        )
        print("-" * 70)


        # Display the question being tested.
        print("Question:")
        print(test["question"])

        print()
        print("Top 3 results:")


        # Perform semantic search using the test question.
        results = search(
            test["question"],
            k=3
        )


        # If no results were returned,
        # mark the test as failed.
        if not results:

            print("No handbook results found.")
            print("RESULT: FAIL")

            continue


        # ==================================================
        # DISPLAY SEARCH RESULTS
        # ==================================================

        # Print each of the top 3 search results.
        for position, result in enumerate(
            results,
            start=1
        ):

            # Display ranking, filename,
            # and similarity score.
            print(
                f"{position}. "
                f"{result['file']} "
                f"{result['score']}"
            )

            # Display the first 200 characters of
            # the matching handbook text.
            print(
                f"   Text: {result['text'][:200]}..."
            )


        # ==================================================
        # VERIFY TOP RESULT
        # ==================================================

        # The first result is considered the best match
        # because it has the highest similarity score.
        first_file = results[0]["file"]


        print()

        # Display what file we expected to be ranked first.
        print(
            f"Expected first: {test['expected']}"
        )

        # Display the file actually ranked first.
        print(
            f"Actual first:   {first_file}"
        )


        # Check whether the highest-ranked file
        # matches the expected handbook file.
        if first_file == test["expected"]:

            print("RESULT: PASS")

            # Increase the successful test counter.
            passed += 1

        else:

            print("RESULT: FAIL")

            print(
                "The vector search ranked a different "
                "handbook file first."
            )


    # ==================================================
    # FINAL TEST SUMMARY
    # ==================================================

    print()
    print("=" * 70)
    print("TASK 7 FINAL SUMMARY")
    print("=" * 70)


    # Display the total number of passed tests.
    print(
        f"Passed: {passed}/{len(tests)}"
    )


    # Check whether every test passed.
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

