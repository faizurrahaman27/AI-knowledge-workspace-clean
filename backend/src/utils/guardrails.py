"""
Lightweight, dependency-free guardrails for a regulated-industry RAG chatbot.

This is intentionally a heuristic, pattern-based layer rather than a second
LLM call: it is fast, has zero external cost, and is transparent/auditable,
which matters for compliance. It is a first line of defense, not a complete
safety system -- for higher-stakes deployments, pair this with a dedicated
classifier (e.g. Llama Guard) or a hosted moderation API.
"""

import re
from dataclasses import dataclass, field


# --- Prompt injection / jailbreak heuristics -------------------------------

_INJECTION_PATTERNS = [
    r"ignore (all|any|the) (previous|prior|above) instructions",
    r"disregard (all|any|the) (previous|prior|above) (instructions|rules)",
    r"you are no longer",
    r"forget (all|your) (previous )?(instructions|rules|prompt)",
    r"reveal (your|the) (system prompt|instructions)",
    r"what (is|are) your (system prompt|instructions)",
    r"act as (if you|though you)",
    r"pretend (you are|to be)",
    r"jailbreak",
    r"\bDAN\b",
    r"tell me (your|the) (secrets|confidential)",
    r"bypass (your|the) (rules|restrictions|filters)",
]

_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


# --- PII heuristics ---------------------------------------------------------

_PII_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "ssn_like": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card_like": re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str | None = None
    pii_types_found: list[str] = field(default_factory=list)
    redacted_text: str | None = None


def check_prompt_injection(user_text: str) -> GuardrailResult:
    """
    Flags user input that looks like an attempt to override system
    instructions or extract confidential/system-level information.
    """
    if _INJECTION_RE.search(user_text or ""):
        return GuardrailResult(
            allowed=False,
            reason="This message looks like an attempt to override the assistant's "
            "instructions, which isn't supported.",
        )
    return GuardrailResult(allowed=True)


def detect_pii(text: str) -> list[str]:
    found = []
    for label, pattern in _PII_PATTERNS.items():
        if pattern.search(text or ""):
            found.append(label)
    return found


def redact_pii(text: str) -> str:
    redacted = text or ""
    for label, pattern in _PII_PATTERNS.items():
        redacted = pattern.sub(f"[REDACTED_{label.upper()}]", redacted)
    return redacted


def check_user_message(user_text: str) -> GuardrailResult:
    """
    Full guardrail pass over an incoming chat message, before it is sent
    to the retriever/LLM. Blocks likely prompt-injection attempts and
    flags (without necessarily blocking) PII present in the raw question,
    which is useful for compliance logging in regulated deployments.
    """
    injection_result = check_prompt_injection(user_text)
    if not injection_result.allowed:
        return injection_result

    pii_found = detect_pii(user_text)

    return GuardrailResult(
        allowed=True,
        pii_types_found=pii_found,
        redacted_text=redact_pii(user_text) if pii_found else user_text,
    )
