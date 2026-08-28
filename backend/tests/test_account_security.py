def _register_and_login(client, email="secuser@example.com", password="Passw0rd!"):
    client.post(
        "/auth/register",
        json={"full_name": "Sec User", "email": email, "password": password},
    )
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()


def test_account_locks_after_repeated_failed_logins(client, monkeypatch):
    from src.core import settings as settings_mod
    monkeypatch.setattr(settings_mod.settings, "MAX_FAILED_LOGIN_ATTEMPTS", 3)

    email = "lockout@example.com"
    client.post(
        "/auth/register",
        json={"full_name": "Lock User", "email": email, "password": "Passw0rd!"},
    )

    for _ in range(3):
        r = client.post("/auth/login", json={"email": email, "password": "WrongPass1"})
        assert r.status_code == 401

    # Correct password, but account is now locked.
    r = client.post("/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert r.status_code == 423


def test_change_password_invalidates_old_access_token(client):
    tokens = _register_and_login(client)
    old_headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.get("/auth/me", headers=old_headers)
    assert r.status_code == 200

    r = client.post(
        "/auth/change-password",
        headers=old_headers,
        json={"current_password": "Passw0rd!", "new_password": "NewPassw0rd!"},
    )
    assert r.status_code == 200
    new_tokens = r.json()

    # The OLD access token must now be rejected (token_version bumped).
    r = client.get("/auth/me", headers=old_headers)
    assert r.status_code == 401

    # The NEW access token from change-password works.
    new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
    r = client.get("/auth/me", headers=new_headers)
    assert r.status_code == 200


def test_logout_everywhere_invalidates_refresh_token(client):
    tokens = _register_and_login(client, email="logout@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.post("/auth/logout-everywhere", headers=headers)
    assert r.status_code == 200

    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


def test_forgot_and_reset_password_flow(client, caplog):
    import logging
    caplog.set_level(logging.INFO)

    email = "reset@example.com"
    client.post(
        "/auth/register",
        json={"full_name": "Reset User", "email": email, "password": "Passw0rd!"},
    )

    r = client.post("/auth/forgot-password", json={"email": email})
    assert r.status_code == 200

    # Dev-mode fallback: no SMTP configured, so the reset link was logged.
    from src.db.database import SessionLocal
    from src.models.user import User

    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    assert user.reset_token_hash is not None
    db.close()

    # Simulate having the raw token from the "emailed" link by generating
    # one through the same code path and writing its hash directly, since
    # the raw token itself is never persisted (by design).
    from src.core.security import generate_reset_token
    raw_token, hashed_token = generate_reset_token()
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.reset_token_hash = hashed_token
    from datetime import datetime, timedelta, timezone
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()
    db.close()

    r = client.post(
        "/auth/reset-password",
        json={"email": email, "token": raw_token, "new_password": "BrandNew1!"},
    )
    assert r.status_code == 200

    # Old password no longer works, new one does.
    r = client.post("/auth/login", json={"email": email, "password": "Passw0rd!"})
    assert r.status_code == 401

    r = client.post("/auth/login", json={"email": email, "password": "BrandNew1!"})
    assert r.status_code == 200


def test_reset_password_rejects_wrong_token(client):
    email = "resetbad@example.com"
    client.post(
        "/auth/register",
        json={"full_name": "Bad Reset", "email": email, "password": "Passw0rd!"},
    )
    client.post("/auth/forgot-password", json={"email": email})

    r = client.post(
        "/auth/reset-password",
        json={"email": email, "token": "not-the-real-token", "new_password": "BrandNew1!"},
    )
    assert r.status_code == 400


def test_update_theme_preference(client):
    tokens = _register_and_login(client, email="theme@example.com")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    r = client.patch("/auth/theme", headers=headers, json={"theme": "light"})
    assert r.status_code == 200
    assert r.json()["theme"] == "light"

    r = client.get("/auth/me", headers=headers)
    assert r.json()["theme"] == "light"


def test_google_login_returns_clear_error_when_unconfigured(client):
    r = client.post("/auth/google", json={"id_token": "whatever"})
    assert r.status_code == 400
    assert "GOOGLE_CLIENT_ID" in r.json()["detail"]
