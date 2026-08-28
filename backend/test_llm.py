from src.utils.llm import ask_llm

context = """
Python is a programming language.

FastAPI is used for APIs.

Artificial Intelligence is changing the world.
"""

question = "What is FastAPI used for?"

answer = chat(
    db=db,
    question=question,
    current_user=current_user,
)

print(answer)