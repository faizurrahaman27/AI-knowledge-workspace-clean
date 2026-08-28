def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_create_team_makes_creator_owner(client):
    headers = _register(client, "owner@example.com")
    r = client.post("/teams/", headers=headers, json={"name": "Acme Corp"})
    assert r.status_code == 200
    assert r.json()["role"] == "owner"


def test_list_my_teams(client):
    headers = _register(client, "owner2@example.com")
    client.post("/teams/", headers=headers, json={"name": "Team A"})
    r = client.get("/teams/", headers=headers)
    assert r.status_code == 200
    assert any(t["name"] == "Team A" for t in r.json())


def test_invite_and_accept_flow(client):
    owner_headers = _register(client, "inviter@example.com")
    team = client.post("/teams/", headers=owner_headers, json={"name": "Invite Co"}).json()

    r = client.post(
        f"/teams/{team['id']}/invite",
        headers=owner_headers,
        json={"email": "invitee@example.com", "role": "member"},
    )
    assert r.status_code == 200

    # The invitee needs an account before accepting.
    invitee_headers = _register(client, "invitee@example.com")

    from src.db.database import SessionLocal
    from src.models.team import TeamInvite

    db = SessionLocal()
    invite = db.query(TeamInvite).filter(TeamInvite.email == "invitee@example.com").first()
    assert invite is not None
    db.close()

    # Simulate having the raw token from the invite link (hash-only storage,
    # same pattern as password reset -- generate one and overwrite the hash
    # directly since the raw token itself is never persisted).
    from src.core.security import generate_reset_token
    raw_token, hashed = generate_reset_token()
    db = SessionLocal()
    invite = db.query(TeamInvite).filter(TeamInvite.email == "invitee@example.com").first()
    invite.token_hash = hashed
    db.commit()
    db.close()

    r = client.post(
        "/teams/accept-invite",
        headers=invitee_headers,
        json={"email": "invitee@example.com", "token": raw_token},
    )
    assert r.status_code == 200

    r = client.get(f"/teams/{team['id']}/members", headers=invitee_headers)
    assert r.status_code == 200
    emails = [m["email"] for m in r.json()]
    assert "invitee@example.com" in emails
    assert "inviter@example.com" in emails


def test_non_admin_cannot_invite(client):
    owner_headers = _register(client, "owner3@example.com")
    team = client.post("/teams/", headers=owner_headers, json={"name": "Locked Co"}).json()

    # A random other user (not a member at all) tries to invite someone.
    outsider_headers = _register(client, "outsider@example.com")
    r = client.post(
        f"/teams/{team['id']}/invite",
        headers=outsider_headers,
        json={"email": "someone@example.com"},
    )
    assert r.status_code == 403


def test_accept_invite_rejects_wrong_email(client):
    owner_headers = _register(client, "owner4@example.com")
    team = client.post("/teams/", headers=owner_headers, json={"name": "Strict Co"}).json()
    client.post(
        f"/teams/{team['id']}/invite",
        headers=owner_headers,
        json={"email": "target@example.com"},
    )

    wrong_user_headers = _register(client, "wrong@example.com")

    from src.core.security import generate_reset_token
    from src.db.database import SessionLocal
    from src.models.team import TeamInvite

    raw_token, hashed = generate_reset_token()
    db = SessionLocal()
    invite = db.query(TeamInvite).filter(TeamInvite.email == "target@example.com").first()
    invite.token_hash = hashed
    db.commit()
    db.close()

    r = client.post(
        "/teams/accept-invite",
        headers=wrong_user_headers,
        json={"email": "target@example.com", "token": raw_token},
    )
    assert r.status_code == 403
