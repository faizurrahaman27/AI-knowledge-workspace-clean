import io

import pytest


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    r = client.post(
        "/documents/upload", headers=headers,
        files={"file": (name, io.BytesIO(b"%PDF-1.4 autonomous agent test"), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


@pytest.fixture(autouse=True)
def _stub_pdf_text(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_pages_from_pdf",
        lambda path: [{"page": 1, "text": "Bayes theorem relates conditional probabilities."}],
    )


def _script(steps):
    import openai  # the stub shadowing the real package, via conftest's sys.path insert
    openai.TOOL_CALL_SCRIPT.clear()
    openai.TOOL_CALL_SCRIPT.extend(steps)


def test_agent_answers_directly_with_no_tool_calls(client):
    headers = _register(client, "auto1@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    _script([{"content": "Direct answer, no tools needed."}])

    r = client.post("/agent/auto", headers=headers, json={"document_id": doc_id, "request_text": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["answer"] == "Direct answer, no tools needed."
    assert body["incomplete"] is False
    assert body["trace"] == [{"step": 0, "type": "final_answer"}]


def test_agent_calls_one_tool_then_finishes(client):
    headers = _register(client, "auto2@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    _script([
        {"tool_calls": [("search_document", {"query": "Bayes theorem"})]},
        {"content": "Based on the search, here's the explanation."},
    ])

    r = client.post(
        "/agent/auto", headers=headers,
        json={"document_id": doc_id, "request_text": "explain Bayes theorem"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["incomplete"] is False
    tool_steps = [t for t in body["trace"] if t["type"] == "tool_call"]
    assert len(tool_steps) == 1
    assert tool_steps[0]["tool"] == "search_document"
    assert "Bayes" in tool_steps[0]["result_preview"]


def test_agent_calls_multiple_different_tools(client):
    headers = _register(client, "auto3@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    _script([
        {"tool_calls": [("summarize_document", {})]},
        {"tool_calls": [("generate_flashcards", {})]},
        {"content": "Here's your summary and flashcards."},
    ])

    r = client.post(
        "/agent/auto", headers=headers,
        json={"document_id": doc_id, "request_text": "summarize this and make flashcards"},
    )
    assert r.status_code == 200
    tools_called = [t["tool"] for t in r.json()["trace"] if t["type"] == "tool_call"]
    assert tools_called == ["summarize_document", "generate_flashcards"]


def test_agent_stops_at_max_steps_and_reports_incomplete(client):
    headers = _register(client, "auto4@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    from src.utils.autonomous_agent import MAX_STEPS
    # Script more tool-call steps than MAX_STEPS allows -- the loop must
    # stop and report incomplete rather than looping forever.
    _script([{"tool_calls": [("search_document", {"query": "x"})]}] * (MAX_STEPS + 3))

    r = client.post(
        "/agent/auto", headers=headers,
        json={"document_id": doc_id, "request_text": "keep going forever"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["incomplete"] is True
    assert len([t for t in body["trace"] if t["type"] == "tool_call"]) == MAX_STEPS


def test_agent_rejects_document_you_dont_own(client):
    owner_headers = _register(client, "auto5owner@example.com")
    doc_id = _upload_fake_pdf(client, owner_headers)

    other_headers = _register(client, "auto5other@example.com")
    r = client.post(
        "/agent/auto", headers=other_headers,
        json={"document_id": doc_id, "request_text": "anything"},
    )
    assert r.status_code == 404


def test_agent_unavailable_on_ollama_provider(client, monkeypatch):
    from src.core.settings import settings
    monkeypatch.setattr(settings, "LLM_PROVIDER", "ollama")

    headers = _register(client, "auto6@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post("/agent/auto", headers=headers, json={"document_id": doc_id, "request_text": "hi"})
    assert r.status_code == 400
    assert "groq" in r.json()["detail"].lower()


def test_agent_handles_unknown_tool_result_gracefully(client):
    headers = _register(client, "auto7@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    # A malformed/unexpected tool name from the model shouldn't crash the
    # whole request -- it should surface as a tool result and let the
    # loop continue.
    _script([
        {"tool_calls": [("not_a_real_tool", {})]},
        {"content": "Recovered after an unknown tool."},
    ])

    r = client.post("/agent/auto", headers=headers, json={"document_id": doc_id, "request_text": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert body["incomplete"] is False
    assert "Unknown tool" in body["trace"][0]["result_preview"]
