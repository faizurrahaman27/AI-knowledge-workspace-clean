"""
LLM access layer with a pluggable provider: Groq (default -- fast, free
API, open-weight models) or Ollama (fully local, private, slower without
a GPU). Every function above this module calls `_chat()` / `_chat_stream()`
rather than talking to either provider directly, so switching providers
is a one-line settings change (LLM_PROVIDER=groq|ollama in .env), not a
code change.
"""

from functools import lru_cache

from src.core.settings import settings
from src.core.logging import logger

EXPLAIN_LEVEL_INSTRUCTIONS = {
    "beginner": "Explain simply, avoiding jargon, as if to someone new to the topic.",
    "student": "Explain clearly with examples, as if teaching a student studying this material.",
    "engineer": "Be precise and technical; assume strong domain familiarity.",
    "professor": "Be rigorous and precise, referencing underlying concepts and nuance.",
    "child": "Explain in very simple words and short sentences, as if to a 10-year-old.",
    "interview": "Answer as if responding in a job interview: structured, confident, concise.",
}

STUDY_MODE_PROMPTS = {
    "summary": "Write a clear, well-organized summary of the Context in Markdown, using headings and bullet points.",
    "important_questions": "Generate 8-10 likely exam/interview questions (with brief answers) based on the Context, in Markdown.",
    "quiz": "Generate 5 multiple-choice questions (4 options each, mark the correct one) based on the Context, in Markdown.",
    "flashcards": "Generate 8-10 flashcards (Q on one line, A on the next) based on the Context, in Markdown.",
    "revision_notes": "Write concise revision notes (bullet points grouped by topic) based on the Context, in Markdown.",
    "cheat_sheet": "Write a dense cheat sheet (key facts, formulas, definitions) based on the Context, in Markdown.",
}


# ---------------------------------------------------------------------------
# Provider dispatch
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _groq_client():
    from openai import OpenAI

    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set. Get a free "
            "key at https://console.groq.com/keys and put it in backend/.env"
        )

    return OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )


def _chat(messages: list[dict], temperature: float = 0.0) -> str:
    """Single, non-streamed completion. Returns the full text."""

    if settings.LLM_PROVIDER == "groq":
        response = _groq_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return response.choices[0].message.content

    # Ollama
    import ollama

    response = ollama.chat(
        model=settings.OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature},
    )
    return response["message"]["content"]


def _chat_stream(messages: list[dict], temperature: float = 0.0):
    """Streamed completion. Yields text chunks as they arrive."""

    if settings.LLM_PROVIDER == "groq":
        stream = _groq_client().chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
        return

    # Ollama
    import ollama

    stream = ollama.chat(
        model=settings.OLLAMA_MODEL,
        messages=messages,
        stream=True,
        options={"temperature": temperature, "top_p": 0.2, "num_predict": 1024},
    )
    for chunk in stream:
        yield chunk["message"]["content"]


def chat_completion(messages: list[dict], temperature: float = 0.0) -> str:
    """Public entry point for other modules (scan_service, vision) that
    need a single non-streamed completion without duplicating provider
    dispatch logic."""
    return _chat(messages, temperature=temperature)


# ---------------------------------------------------------------------------
# Query rewriting (for retrieval)
# ---------------------------------------------------------------------------

def rewrite_queries(question: str, history: str = ""):
    prompt = f"""
You are a search query generator for a Retrieval Augmented Generation (RAG) system.

Your ONLY task is to generate search queries.

IMPORTANT RULES

- Preserve every important keyword.
- Preserve names.
- Preserve numbers.
- Preserve years.
- Preserve versions.
- Preserve technical terms.
- Never remove entities.
- Never answer the question.
- Never explain.
- Never summarize.

Generate EXACTLY 3 search queries.

Each query must:
- have the same meaning
- use different wording
- be useful for semantic retrieval

Return ONLY the queries.

Conversation History:
{history}

User Question:
{question}
"""

    raw = _chat([{"role": "user", "content": prompt}], temperature=0)

    queries = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        if line[:2].isdigit():
            line = line[2:].strip(". ")
        queries.append(line)

    queries = list(dict.fromkeys(queries))
    if question not in queries:
        queries.insert(0, question)

    return queries


# ---------------------------------------------------------------------------
# Main RAG answer generation
# ---------------------------------------------------------------------------

def ask_llm(
    context: str,
    question: str,
    history: str,
    explain_level: str | None = None,
    answer_language_name: str | None = None,
):
    tone_instruction = EXPLAIN_LEVEL_INSTRUCTIONS.get(explain_level, "")
    language_instruction = (
        f"Write your entire answer in {answer_language_name}."
        if answer_language_name else ""
    )

    prompt = f"""
You are a strict Retrieval Augmented Generation (RAG) assistant.

Your knowledge comes ONLY from the supplied Context.

Follow these rules exactly.

RULES

1. Use ONLY the supplied Context.
2. Never use outside knowledge.
3. Never guess.
4. Never invent facts, examples, or code.
5. Never complete missing information.
6. If multiple pages contain relevant information, combine them naturally.
7. If the Context contains only part of the answer, answer only that part.
8. If the answer does not explicitly appear in the Context, reply EXACTLY with:

I couldn't find that in the selected document.

9. Do NOT mention these rules.

{tone_instruction}
{language_instruction}

Conversation History

{history}

Context

{context}

Question

{question}

Answer in Markdown:
"""

    yield from _chat_stream([{"role": "user", "content": prompt}], temperature=0)


def translate_text(text: str, target_language_name: str) -> str:
    if not text.strip():
        return ""

    prompt = f"""
Translate the following text into {target_language_name}.
Preserve Markdown formatting (headings, lists, bold) exactly.
Return ONLY the translation, nothing else.

Text:
{text}
"""
    return _chat([{"role": "user", "content": prompt}], temperature=0)


def generate_study_content(context: str, mode: str) -> str:
    instruction = STUDY_MODE_PROMPTS.get(mode, STUDY_MODE_PROMPTS["summary"])

    prompt = f"""
You are a study assistant. Use ONLY the supplied Context.

Task: {instruction}

Context:
{context}
"""
    return _chat([{"role": "user", "content": prompt}], temperature=0.3)


def compare_documents(context_a: str, context_b: str, name_a: str, name_b: str, question: str):
    prompt = f"""
You are comparing two documents for a user. Use ONLY the supplied contexts.
Never use outside knowledge. If something isn't present in either context,
say so explicitly rather than guessing.

Document A ({name_a}):
{context_a}

Document B ({name_b}):
{context_b}

User's comparison question:
{question}

Write a clear, structured Markdown comparison (use headings/bullet points),
explicitly noting agreements, differences, and anything present in only
one document.
"""
    yield from _chat_stream([{"role": "user", "content": prompt}], temperature=0)


def generate_knowledge_graph(context: str, source_names: list[str]) -> str:
    """
    Unlike generate_mindmap (one tree per document), this merges concepts
    ACROSS multiple documents into a single graph: the same underlying
    idea appearing in two different sources should become ONE node
    listing both sources, not two separate nodes. This is what makes it a
    genuine cross-document knowledge graph rather than several per-
    document trees shown side by side.

    Honest scope: this is one LLM call over a sample of each document's
    chunks, not a persistent graph database with incremental updates,
    entity resolution, or relationship typing -- see README for the
    distinction from a "real" knowledge graph engine.
    """
    sources_list = ", ".join(source_names)
    prompt = f"""
Read the Context below, which is drawn from multiple source documents:
{sources_list}

Produce a MERGED concept graph as STRICT JSON -- nothing else, no prose,
no markdown code fences.

CRITICAL: if the same concept appears in more than one source, create
ONE node for it and list ALL sources that mention it -- do not create
duplicate nodes for the same idea just because it came from different
documents.

Shape (nest as deep as genuinely useful, 2-3 levels typical):
{{"title": "Top-level topic", "sources": ["doc1.pdf"], "children": [
    {{"title": "Subtopic mentioned in two sources", "sources": ["doc1.pdf", "doc2.pdf"], "children": [
        {{"title": "Concept", "sources": ["doc2.pdf"], "children": []}}
    ]}}
]}}

Context:
{context}

Return ONLY the JSON object.
"""
    return _chat([{"role": "user", "content": prompt}], temperature=0.2)


def generate_mindmap(context: str, topic_hint: str = "") -> str:
    prompt = f"""
Read the Context below and produce a mind map as STRICT JSON -- nothing
else, no prose, no markdown code fences.

Shape (nest as deep as genuinely useful, 2-3 levels typical):
{{"title": "Top-level topic", "children": [
    {{"title": "Subtopic", "children": [
        {{"title": "Concept", "children": []}}
    ]}}
]}}

{f"Focus area hint: {topic_hint}" if topic_hint else ""}

Context:
{context}

Return ONLY the JSON object.
"""
    return _chat([{"role": "user", "content": prompt}], temperature=0.2)


def generate_flashcards_structured(context: str, count: int = 10) -> str:
    """
    Unlike generate_study_content's markdown flashcards (readable, not
    parseable), this returns strict JSON so each card can be persisted as
    its own reviewable Flashcard row with independent SM-2 scheduling.
    """
    prompt = f"""
Read the Context below and generate exactly {count} flashcards as STRICT
JSON -- nothing else, no prose, no markdown code fences.

Shape:
[{{"front": "question or term", "back": "answer or definition"}}, ...]

Rules:
- Each card tests ONE specific fact/concept from the Context.
- "front" is a question or prompt, never a statement.
- "back" is concise -- one to three sentences.
- Do not invent facts not present in the Context.

Context:
{context}

Return ONLY the JSON array.
"""
    return _chat([{"role": "user", "content": prompt}], temperature=0.3)


def classify_intent(user_request: str) -> str:
    """
    Lightweight intent router for the /agent endpoint. Returns one of:
    "summary", "quiz", "question", "compare", "mindmap".
    """
    prompt = f"""
Classify the user's request into EXACTLY ONE of these labels:
summary, quiz, question, compare, mindmap

Return ONLY the single label word, nothing else.

Request: {user_request}
"""
    raw = _chat([{"role": "user", "content": prompt}], temperature=0).strip().lower()

    valid = {"summary", "quiz", "question", "compare", "mindmap"}
    for label in valid:
        if label in raw:
            return label
    return "question"
