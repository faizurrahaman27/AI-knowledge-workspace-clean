import io

import pytest


@pytest.fixture(autouse=True)
def _stub_pdf_text(client, monkeypatch):
    """See test_agent_and_multidoc_chat.py's identical fixture for why
    this needs to depend on `client` rather than just being autouse."""
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
    fake_pdf = b"%PDF-1.4 activity test content"
    r = client.post(
        "/documents/upload",
        headers=headers,
        files={"file": (name, io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_study_mode_logs_activity(client):
    headers = _register(client, "activity1@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    client.post("/study/", headers=headers, json={"document_id": doc_id, "mode": "summary"})

    r = client.get("/activity/history", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["mode"] == "summary"
    assert r.json()[0]["document_id"] == doc_id


def test_suggestions_exclude_studied_documents(client):
    headers = _register(client, "activity2@example.com")
    studied_doc = _upload_fake_pdf(client, headers, "studied.pdf")
    unstudied_doc = _upload_fake_pdf(client, headers, "unstudied.pdf")

    client.post("/study/", headers=headers, json={"document_id": studied_doc, "mode": "quiz"})

    r = client.get("/activity/suggestions", headers=headers)
    assert r.status_code == 200
    suggested_ids = [s["document_id"] for s in r.json()]
    assert unstudied_doc in suggested_ids
    assert studied_doc not in suggested_ids


def test_activity_is_scoped_per_user(client):
    headers_a = _register(client, "activityA@example.com")
    headers_b = _register(client, "activityB@example.com")

    doc_a = _upload_fake_pdf(client, headers_a, "a.pdf")
    client.post("/study/", headers=headers_a, json={"document_id": doc_a, "mode": "summary"})

    r = client.get("/activity/history", headers=headers_b)
    assert r.status_code == 200
    assert r.json() == []
