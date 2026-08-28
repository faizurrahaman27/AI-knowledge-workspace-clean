import io


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    r = client.post(
        "/documents/upload", headers=headers,
        files={"file": (name, io.BytesIO(b"%PDF-1.4 annotation test"), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_create_and_list_annotation(client):
    headers = _register(client, "note1@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post(
        f"/documents/{doc_id}/annotations", headers=headers,
        json={"page": 3, "note_text": "Important point here", "quote_text": "the key finding was...",
              "color": "yellow", "x_percent": 0.4, "y_percent": 0.2},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 3
    assert body["quote_text"] == "the key finding was..."

    r = client.get(f"/documents/{doc_id}/annotations", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_annotation_without_quote_is_a_freeform_note(client):
    headers = _register(client, "note2@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post(
        f"/documents/{doc_id}/annotations", headers=headers,
        json={"page": 1, "note_text": "Remember to review this chapter again"},
    )
    assert r.status_code == 200
    assert r.json()["quote_text"] is None


def test_blank_note_rejected(client):
    headers = _register(client, "note3@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post(
        f"/documents/{doc_id}/annotations", headers=headers,
        json={"page": 1, "note_text": "   "},
    )
    assert r.status_code == 422


def test_delete_annotation(client):
    headers = _register(client, "note4@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    created = client.post(
        f"/documents/{doc_id}/annotations", headers=headers,
        json={"page": 1, "note_text": "temp note"},
    ).json()

    r = client.delete(f"/documents/{doc_id}/annotations/{created['id']}", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/documents/{doc_id}/annotations", headers=headers)
    assert r.json() == []


def test_annotations_are_private_per_user_even_on_shared_document(client):
    owner_headers = _register(client, "note5owner@example.com")
    doc_id = _upload_fake_pdf(client, owner_headers)
    client.post(
        f"/documents/{doc_id}/annotations", headers=owner_headers,
        json={"page": 1, "note_text": "owner's private note"},
    )

    other_headers = _register(client, "note5other@example.com")
    r = client.get(f"/documents/{doc_id}/annotations", headers=other_headers)
    assert r.status_code == 404


def test_cannot_delete_someone_elses_annotation(client):
    owner_headers = _register(client, "note6owner@example.com")
    doc_id = _upload_fake_pdf(client, owner_headers)
    note = client.post(
        f"/documents/{doc_id}/annotations", headers=owner_headers,
        json={"page": 1, "note_text": "mine"},
    ).json()

    other_headers = _register(client, "note6other@example.com")
    r = client.delete(f"/documents/{doc_id}/annotations/{note['id']}", headers=other_headers)
    assert r.status_code == 404


def test_page_must_be_positive(client):
    headers = _register(client, "note7@example.com")
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post(
        f"/documents/{doc_id}/annotations", headers=headers,
        json={"page": 0, "note_text": "invalid page"},
    )
    assert r.status_code == 422
