import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "stubs"))


def _reload_src_modules():
    for mod in list(sys.modules):
        if mod == "src" or mod.startswith("src."):
            del sys.modules[mod]


def _fresh_llm(monkeypatch, provider="groq"):
    monkeypatch.setenv("LLM_PROVIDER", provider)
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    _reload_src_modules()
    from src.utils import llm
    return llm


def test_groq_chat_completion(monkeypatch):
    llm = _fresh_llm(monkeypatch, provider="groq")
    result = llm.chat_completion([{"role": "user", "content": "hello"}])
    assert result == "stub answer"


def test_groq_chat_stream_yields_chunks(monkeypatch):
    llm = _fresh_llm(monkeypatch, provider="groq")
    chunks = list(llm._chat_stream([{"role": "user", "content": "hello"}]))
    assert "".join(chunks).strip() == "stub answer"


def test_groq_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "")
    _reload_src_modules()
    from src.utils import llm

    import pytest
    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        llm.chat_completion([{"role": "user", "content": "hello"}])


def test_ollama_provider_still_works(monkeypatch):
    llm = _fresh_llm(monkeypatch, provider="ollama")
    result = llm.chat_completion([{"role": "user", "content": "hello"}])
    assert result == "stub answer"


def test_ask_llm_streams_text(monkeypatch):
    llm = _fresh_llm(monkeypatch, provider="groq")
    chunks = list(llm.ask_llm(context="ctx", question="q?", history=""))
    assert "".join(chunks).strip() == "stub answer"


def test_classify_intent_returns_valid_label(monkeypatch):
    llm = _fresh_llm(monkeypatch, provider="groq")
    # stub always replies "stub answer", which contains no valid label,
    # so this exercises the safe fallback path.
    intent = llm.classify_intent("summarize this")
    assert intent == "question"
