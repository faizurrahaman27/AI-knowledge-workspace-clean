from src.utils.embeddings import generate_embeddings

chunks = [
    "Python is a programming language.",
    "Artificial Intelligence is changing the world."
]

embeddings = generate_embeddings(chunks)

print(len(embeddings))
print(len(embeddings[0]))