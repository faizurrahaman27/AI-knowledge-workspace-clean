"""
Visual/diagram understanding via a multimodal model -- Groq (default) or
Ollama, following the same LLM_PROVIDER dispatch as utils/llm.py.

Groq path: uses settings.GROQ_VISION_MODEL (a Llama vision-preview model)
through the OpenAI-compatible API, image sent as a base64 data URL. This
IS covered by real testing here (it's just an HTTP call, no local model
to download), unlike the Ollama path below.

Ollama path: requires `ollama pull llama3.2-vision` (or another vision
model) on the machine running the backend -- a multi-GB download. This
sandbox has no network access to pull model weights, so if you use
LLM_PROVIDER=ollama, verify this path yourself before relying on it.
"""

import base64
from functools import lru_cache

from src.core.settings import settings

DEFAULT_PROMPT = (
    "Describe this image in detail. If it's a diagram, flowchart, "
    "architecture drawing, chart, or table, explain what it shows "
    "and how the parts relate to each other, not just what's visible."
)


@lru_cache(maxsize=1)
def _groq_client():
    from openai import OpenAI

    if not settings.GROQ_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER is 'groq' but GROQ_API_KEY is not set. Get a free "
            "key at https://console.groq.com/keys and put it in backend/.env"
        )
    return OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")


def describe_visual(image_path: str, question: str | None = None) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    image_b64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = question or DEFAULT_PROMPT

    if settings.LLM_PROVIDER == "groq":
        response = _groq_client().chat.completions.create(
            model=settings.GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                }
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content

    # Ollama
    import ollama

    response = ollama.chat(
        model=settings.OLLAMA_VISION_MODEL,
        messages=[{"role": "user", "content": prompt, "images": [image_b64]}],
        options={"temperature": 0.2},
    )
    return response["message"]["content"]
