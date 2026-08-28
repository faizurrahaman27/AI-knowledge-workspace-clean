import io

import pytest


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    r = client.post(
        "/documents/upload", headers=headers,
        files={"file": (name, io.BytesIO(b"%PDF-1.4 flashcard test"), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


@pytest.fixture(autouse=True)
def _stub_pdf_text(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_pages_from_pdf",
        lambda path: [{"page": 1, "text": "Photosynthesis converts light energy into chemical energy."}],
    )


@pytest.fixture(autouse=True)
def _stub_flashcard_llm(client, monkeypatch):
    """The generic Groq stub always replies 'stub answer', which isn't
    valid JSON -- give this test suite a stub that actually returns a
    parseable flashcard array, so we're testing the real JSON-extraction
    and persistence logic, not just that it fails gracefully.

    Must depend on `client` (see test_agent_and_multidoc_chat.py's
    identical pattern) so this patch survives client's fresh module reload."""
    import src.services.flashcard_service as fc_service

    def fake_generate(context, count=10):
        import json
        return json.dumps([
            {"front": "What does photosynthesis convert?", "back": "Light energy into chemical energy."},
            {"front": "What produces chemical energy in plants?", "back": "Photosynthesis."},
        ])

    monkeypatch.setattr(fc_service, "generate_flashcards_structured", fake_generate)


def test_generate_flashcards_persists_cards(client):
    headers = _register(client, "fc1@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5})
    assert r.status_code == 200
    cards = r.json()
    assert len(cards) == 2
    assert cards[0]["repetitions"] == 0
    assert cards[0]["ease_factor"] == 2.5


def test_new_cards_are_immediately_due(client):
    headers = _register(client, "fc2@example.com")
    doc_id = _upload_fake_pdf(client, headers)
    client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5})

    r = client.get("/flashcards/due", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_reviewing_good_pushes_card_out_of_due_list(client):
    headers = _register(client, "fc3@example.com")
    doc_id = _upload_fake_pdf(client, headers)
    cards = client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5}).json()
    card_id = cards[0]["id"]

    r = client.post(f"/flashcards/{card_id}/review", headers=headers, json={"grade": "good"})
    assert r.status_code == 200
    body = r.json()
    assert body["repetitions"] == 1
    assert body["interval_days"] == 1
    assert body["total_reviews"] == 1

    due = client.get("/flashcards/due", headers=headers).json()
    due_ids = [c["id"] for c in due]
    assert card_id not in due_ids


def test_reviewing_again_resets_repetitions_but_keeps_due_today(client):
    headers = _register(client, "fc4@example.com")
    doc_id = _upload_fake_pdf(client, headers)
    cards = client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5}).json()
    card_id = cards[0]["id"]

    # First review: "good" builds up repetitions/interval.
    client.post(f"/flashcards/{card_id}/review", headers=headers, json={"grade": "good"})
    r = client.post(f"/flashcards/{card_id}/review", headers=headers, json={"grade": "again"})
    body = r.json()
    assert body["repetitions"] == 0
    assert body["interval_days"] == 1
    # A lapse doesn't erase the ease factor entirely (SM-2 behavior).
    assert body["ease_factor"] >= 1.3


def test_invalid_grade_rejected(client):
    headers = _register(client, "fc5@example.com")
    doc_id = _upload_fake_pdf(client, headers)
    cards = client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5}).json()

    r = client.post(f"/flashcards/{cards[0]['id']}/review", headers=headers, json={"grade": "excellent"})
    assert r.status_code == 422  # pydantic validator rejects it before it even reaches the service


def test_flashcards_scoped_per_user(client):
    headers_a = _register(client, "fcA@example.com")
    headers_b = _register(client, "fcB@example.com")

    doc_id = _upload_fake_pdf(client, headers_a)
    cards = client.post("/flashcards/generate", headers=headers_a, json={"document_id": doc_id, "count": 5}).json()

    r = client.post(f"/flashcards/{cards[0]['id']}/review", headers=headers_b, json={"grade": "good"})
    assert r.status_code == 404


def test_delete_flashcard(client):
    headers = _register(client, "fc6@example.com")
    doc_id = _upload_fake_pdf(client, headers)
    cards = client.post("/flashcards/generate", headers=headers, json={"document_id": doc_id, "count": 5}).json()

    r = client.delete(f"/flashcards/{cards[0]['id']}", headers=headers)
    assert r.status_code == 200

    remaining = client.get(f"/flashcards/document/{doc_id}", headers=headers).json()
    assert len(remaining) == 1
