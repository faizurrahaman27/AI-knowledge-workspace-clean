import io
import json

import pytest


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    r = client.post(
        "/documents/upload", headers=headers,
        files={"file": (name, io.BytesIO(b"%PDF-1.4 kg test"), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


@pytest.fixture(autouse=True)
def _stub_pdf_text(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_pages_from_pdf",
        lambda path: [{"page": 1, "text": "Bayes theorem relates conditional probabilities to priors."}],
    )


def _stub_graph_json(monkeypatch, tree_dict):
    from src.utils import llm as llm_mod
    monkeypatch.setattr(llm_mod, "_chat", lambda messages, temperature=0.0: json.dumps(tree_dict))


def test_workspace_knowledge_graph_merges_sources(client, monkeypatch):
    headers = _register(client, "kg1@example.com")
    ws = client.post("/workspaces/", headers=headers, json={"name": "KG Test"}).json()

    doc_a = _upload_fake_pdf(client, headers, "book_a.pdf")
    doc_b = _upload_fake_pdf(client, headers, "book_b.pdf")
    client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_a})
    client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_b})

    _stub_graph_json(monkeypatch, {
        "title": "Probability",
        "sources": ["book_a.pdf", "book_b.pdf"],
        "children": [
            {"title": "Bayes' Theorem", "sources": ["book_a.pdf", "book_b.pdf"], "children": []},
        ],
    })

    r = client.post("/mindmap/workspace", headers=headers, json={"workspace_id": ws["id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Probability"
    assert set(body["children"][0]["sources"]) == {"book_a.pdf", "book_b.pdf"}


def test_workspace_knowledge_graph_requires_documents(client):
    headers = _register(client, "kg2@example.com")
    ws = client.post("/workspaces/", headers=headers, json={"name": "Empty"}).json()

    r = client.post("/mindmap/workspace", headers=headers, json={"workspace_id": ws["id"]})
    assert r.status_code == 422


def test_workspace_knowledge_graph_rejects_non_member(client, monkeypatch):
    owner_headers = _register(client, "kg3owner@example.com")
    ws = client.post("/workspaces/", headers=owner_headers, json={"name": "Private KG"}).json()
    doc_id = _upload_fake_pdf(client, owner_headers, "secret.pdf")
    client.post(f"/workspaces/{ws['id']}/documents", headers=owner_headers, json={"document_id": doc_id})

    other_headers = _register(client, "kg3other@example.com")
    r = client.post("/mindmap/workspace", headers=other_headers, json={"workspace_id": ws["id"]})
    assert r.status_code == 404


def test_workspace_knowledge_graph_handles_malformed_json(client, monkeypatch):
    headers = _register(client, "kg4@example.com")
    ws = client.post("/workspaces/", headers=headers, json={"name": "Bad JSON"}).json()
    doc_id = _upload_fake_pdf(client, headers, "doc.pdf")
    client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_id})

    from src.utils import llm as llm_mod
    monkeypatch.setattr(llm_mod, "_chat", lambda messages, temperature=0.0: "not valid json at all")

    r = client.post("/mindmap/workspace", headers=headers, json={"workspace_id": ws["id"]})
    assert r.status_code == 502
