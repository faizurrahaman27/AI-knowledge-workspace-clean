import io
import json

import pytest


@pytest.fixture(autouse=True)
def _stub_pdf_text(client, monkeypatch):
    """
    The generic `client` fixture's stubbed `fitz` returns no pages (empty
    PDF), which is correct for testing "empty upload" behavior elsewhere
    but means there's nothing for the study pack to summarize. Give these
    tests real text to work with, same as a genuine PDF would produce.

    Must depend on `client` (not just run autouse) so this patch is
    applied AFTER client's fresh `src.*` module reload -- otherwise the
    reload wipes this patch out before any test body runs.
    """
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_pages_from_pdf",
        lambda path: [
            {"page": 1, "text": "The company reported strong quarterly revenue growth this year."},
            {"page": 2, "text": "Employee benefits include 20 annual leave days per year."},
        ],
    )


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    fake_pdf = b"%PDF-1.4 workspace chat test content"
    r = client.post(
        "/documents/upload",
        headers=headers,
        files={"file": (name, io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_workspace_chat_requires_document_or_workspace(client):
    headers = _register(client, "chatreq@example.com")
    r = client.post("/chat/", headers=headers, json={"question": "hello"})
    # Streaming response -- the validation error surfaces as a 400-ish
    # first event or a non-200; either way, it must not silently 200.
    assert r.status_code in (400, 422) or "Provide either" in r.text


def test_workspace_chat_searches_across_documents(client):
    headers = _register(client, "wschat@example.com")
    ws = client.post("/workspaces/", headers=headers, json={"name": "Multi"}).json()

    doc_a = _upload_fake_pdf(client, headers, "a.pdf")
    doc_b = _upload_fake_pdf(client, headers, "b.pdf")

    client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_a})
    client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_b})

    r = client.post(
        "/chat/", headers=headers,
        json={"question": "what is in these documents?", "workspace_id": ws["id"]},
    )
    assert r.status_code == 200
    events = [json.loads(l) for l in r.text.split("\n") if l.strip()]
    stages = [e.get("stage") for e in events if e.get("type") == "status"]
    assert "retrieval" in stages
    assert any(e.get("type") == "done" for e in events)


def test_workspace_chat_history_shared_across_members(client):
    owner_headers = _register(client, "wshistowner@example.com")
    team = client.post("/teams/", headers=owner_headers, json={"name": "Hist Team"}).json()
    ws = client.post(
        "/workspaces/", headers=owner_headers,
        json={"name": "Shared", "team_id": team["id"]},
    ).json()

    doc_id = _upload_fake_pdf(client, owner_headers, "hist.pdf")
    client.post(f"/workspaces/{ws['id']}/documents", headers=owner_headers, json={"document_id": doc_id})

    client.post(
        "/chat/", headers=owner_headers,
        json={"question": "first question", "workspace_id": ws["id"]},
    )

    r = client.get(f"/chat/workspace/{ws['id']}", headers=owner_headers)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert r.json()[0]["question"] == "first question"


def test_agent_study_pack_returns_all_sections(client):
    headers = _register(client, "studypack@example.com")
    doc_id = _upload_fake_pdf(client, headers, "pack.pdf")

    r = client.post(
        "/agent/study-pack", headers=headers,
        json={"document_id": doc_id, "request_text": "make me a study pack"},
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("summary", "important_questions", "flashcards", "quiz", "mindmap"):
        assert key in body
        assert body[key]  # non-empty (stub LLM always returns "stub answer")


def test_agent_study_pack_pdf_download(client):
    headers = _register(client, "studypackpdf@example.com")
    doc_id = _upload_fake_pdf(client, headers, "packpdf.pdf")

    r = client.get(f"/agent/study-pack/{doc_id}/pdf", headers=headers)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"  # real PDF magic bytes, not a stub string
    assert "attachment" in r.headers["content-disposition"]


def test_agent_study_pack_rejects_document_you_dont_own(client):
    owner_headers = _register(client, "packowner@example.com")
    doc_id = _upload_fake_pdf(client, owner_headers, "notyours.pdf")

    other_headers = _register(client, "packother@example.com")
    r = client.post(
        "/agent/study-pack", headers=other_headers,
        json={"document_id": doc_id, "request_text": "steal this"},
    )
    assert r.status_code == 404
