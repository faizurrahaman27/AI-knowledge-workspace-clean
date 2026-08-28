"""
Autonomous agent planning: the LLM decides, turn by turn, which tool to
call next (or that it's done), based on the user's free-text request and
the results of whatever it has called so far.

This is genuinely different from api/agent.py's `full_study_pack`, which
runs a FIXED sequence (summary -> questions -> flashcards -> quiz ->
mindmap) every single time regardless of what was asked. Here the model
chooses: "just quiz me on chapter 3" might call search_document once then
generate_quiz and stop; "summarize this and make flashcards" calls two
different tools; a narrow question might call search_document and answer
directly. The sequence isn't hardcoded anywhere in this file -- it
emerges from what the model decides.

Uses Groq's OpenAI-compatible function-calling API. NOT implemented for
LLM_PROVIDER=ollama: reliable multi-turn tool calling needs a model
trained for it, and small locally-hosted models are inconsistent at it in
practice -- raising a clear error here is more honest than silently
producing a broken or infinite-looping agent.
"""

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.core.settings import settings
from src.core.logging import logger

from src.services.document_service import get_owned_document
from src.utils.vector_store import hybrid_search, get_document_chunks_sample
from src.utils.embeddings import generate_embeddings
from src.utils.reranker import rerank
from src.utils.llm import _groq_client, generate_study_content, generate_mindmap

MAX_STEPS = 6

SYSTEM_PROMPT = """You are an autonomous study assistant with tools. Given the \
user's request, decide which tool(s) to call, in which order, to fulfill it \
-- call only what's actually needed for THIS request, not every tool every \
time. When you have enough information to answer, respond normally (no \
tool call) with your final answer in Markdown. You may call multiple tools \
across multiple turns if the request genuinely needs it (e.g. searching \
for two different things before comparing them)."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_document",
            "description": "Semantic + keyword search over the document for passages relevant to a query. Use this to find specific facts before answering, summarizing a specific part, or before generating study material about a specific topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "What to search for"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_document",
            "description": "Generates a whole-document summary. Use when the user asks for a summary/overview, not for a narrow factual question.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_quiz",
            "description": "Generates multiple-choice quiz questions from the whole document. Use when the user asks to be quizzed/tested.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_flashcards",
            "description": "Generates flashcards (Q/A pairs) from the whole document. Use when the user asks for flashcards or memorization aids.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_mindmap",
            "description": "Generates a topic mind map (as a description) from the whole document. Use when the user asks for a mind map, concept map, or structural overview.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _execute_tool(document_id: int, name: str, args: dict) -> str:
    if name == "search_document":
        query = args.get("query", "")
        query_embedding = generate_embeddings([query])[0]
        docs, metas = hybrid_search(
            query_embedding=query_embedding, query_text=query,
            document_id=document_id, n_results=20,
        )
        docs, metas, _scores = rerank(question=query, documents=docs, metadatas=metas, top_k=5)
        if not docs:
            return "No relevant passages found for that query."
        return "\n\n".join(f"[Page {m.get('page')}] {d}" for d, m in zip(docs, metas))

    chunks, metadatas = get_document_chunks_sample(document_id, max_chunks=30)
    if not chunks:
        return "This document has no processed content yet."
    context = "\n\n".join(f"[Page {m.get('page')}] {c}" for c, m in zip(chunks, metadatas))

    if name == "summarize_document":
        return generate_study_content(context=context, mode="summary")
    if name == "generate_quiz":
        return generate_study_content(context=context, mode="quiz")
    if name == "generate_flashcards":
        return generate_study_content(context=context, mode="flashcards")
    if name == "generate_mindmap":
        return generate_mindmap(context=context)

    return f"Unknown tool '{name}'."


def run_autonomous_agent(db: Session, document_id: int, current_user, request_text: str) -> dict:
    if settings.LLM_PROVIDER != "groq":
        raise HTTPException(
            status_code=400,
            detail="The autonomous agent needs real function-calling support "
            "and is only implemented for LLM_PROVIDER=groq. Switch providers "
            "in backend/.env to use it.",
        )

    get_owned_document(db, document_id, current_user)  # ownership check, raises 404

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": request_text},
    ]

    trace = []
    client = _groq_client()

    for step in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            temperature=0,
        )
        message = response.choices[0].message

        if not message.tool_calls:
            trace.append({"step": step, "type": "final_answer"})
            return {"answer": message.content or "", "trace": trace, "incomplete": False}

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            name = tool_call.function.name
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            try:
                result = _execute_tool(document_id, name, args)
            except Exception:
                logger.exception("Autonomous agent tool '%s' failed for document_id=%s", name, document_id)
                result = f"Tool '{name}' failed to run."

            trace.append({
                "step": step, "type": "tool_call", "tool": name,
                "arguments": args, "result_preview": result[:300],
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    logger.info("Autonomous agent hit MAX_STEPS=%d for document_id=%s", MAX_STEPS, document_id)
    return {
        "answer": "I wasn't able to finish within the step limit. Here's what I found along the way "
        "-- you can ask a more specific follow-up.",
        "trace": trace,
        "incomplete": True,
    }
