import io


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _upload_fake_pdf(client, headers, name="doc.pdf"):
    fake_pdf = b"%PDF-1.4 workspace test content"
    r = client.post(
        "/documents/upload",
        headers=headers,
        files={"file": (name, io.BytesIO(fake_pdf), "application/pdf")},
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_create_personal_workspace(client):
    headers = _register(client, "ws1@example.com")
    r = client.post("/workspaces/", headers=headers, json={"name": "My Research"})
    assert r.status_code == 200
    assert r.json()["owner_id"] is not None
    assert r.json()["team_id"] is None


def test_add_and_remove_document_from_workspace(client):
    headers = _register(client, "ws2@example.com")
    ws = client.post("/workspaces/", headers=headers, json={"name": "Papers"}).json()
    doc_id = _upload_fake_pdf(client, headers)

    r = client.post(f"/workspaces/{ws['id']}/documents", headers=headers, json={"document_id": doc_id})
    assert r.status_code == 200

    r = client.get(f"/workspaces/{ws['id']}/documents", headers=headers)
    assert r.status_code == 200
    assert any(d["id"] == doc_id for d in r.json())

    r = client.delete(f"/workspaces/{ws['id']}/documents/{doc_id}", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/workspaces/{ws['id']}/documents", headers=headers)
    assert r.json() == []


def test_cannot_access_someone_elses_personal_workspace(client):
    owner_headers = _register(client, "ws3owner@example.com")
    ws = client.post("/workspaces/", headers=owner_headers, json={"name": "Private"}).json()

    other_headers = _register(client, "ws3other@example.com")
    r = client.get(f"/workspaces/{ws['id']}/documents", headers=other_headers)
    assert r.status_code == 404  # not leaked as 403 -- existence isn't confirmed either


def test_team_workspace_shared_across_members(client):
    owner_headers = _register(client, "wsowner@example.com")
    team = client.post("/teams/", headers=owner_headers, json={"name": "Research Team"}).json()

    ws = client.post(
        "/workspaces/", headers=owner_headers,
        json={"name": "Shared Docs", "team_id": team["id"]},
    ).json()
    assert ws["team_id"] == team["id"]

    doc_id = _upload_fake_pdf(client, owner_headers, name="shared.pdf")
    client.post(f"/workspaces/{ws['id']}/documents", headers=owner_headers, json={"document_id": doc_id})

    # Invite + accept a second member (reusing the raw-token pattern from
    # test_teams.py, since the token itself is never persisted anywhere).
    member_headers = _register(client, "wsmember@example.com")
    client.post(
        f"/teams/{team['id']}/invite", headers=owner_headers,
        json={"email": "wsmember@example.com"},
    )

    from src.core.security import generate_reset_token
    from src.db.database import SessionLocal
    from src.models.team import TeamInvite

    raw_token, hashed = generate_reset_token()
    db = SessionLocal()
    invite = db.query(TeamInvite).filter(TeamInvite.email == "wsmember@example.com").first()
    invite.token_hash = hashed
    db.commit()
    db.close()

    client.post(
        "/teams/accept-invite", headers=member_headers,
        json={"email": "wsmember@example.com", "token": raw_token},
    )

    # The team member can now see the shared workspace's documents, even
    # though they didn't upload them.
    r = client.get(f"/workspaces/{ws['id']}/documents", headers=member_headers)
    assert r.status_code == 200
    assert any(d["id"] == doc_id for d in r.json())


def test_cannot_create_workspace_for_team_youre_not_in(client):
    headers = _register(client, "notmember@example.com")
    r = client.post("/workspaces/", headers=headers, json={"name": "Sneaky", "team_id": 99999})
    assert r.status_code == 403
