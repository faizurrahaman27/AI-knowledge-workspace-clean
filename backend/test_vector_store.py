from src.utils.vector_store import (
    add_embeddings,
    search_embeddings,
)

from src.utils.embeddings import generate_embeddings

chunks = [
    "Python is a programming language.",
    "FastAPI is used for APIs.",
    "Artificial Intelligence is changing the world."
]

embeddings = generate_embeddings(chunks)

ids = [
    "1",
    "2",
    "3"
]

add_embeddings(
    ids=ids,
    documents=chunks,
    embeddings=embeddings
)

query = generate_embeddings(
    ["Tell me about Python"]
)[0]

results = search_embeddings(query)

print(results)