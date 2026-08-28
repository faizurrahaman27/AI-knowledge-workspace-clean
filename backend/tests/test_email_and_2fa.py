import pyotp


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


# --- Email verification --------------------------------------------------

def test_new_account_starts_unverified(client):
    token = _register(client, "unverified@example.com")
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.json()["email_verified"] is False


def test_verify_email_flow(client):
    email = "verifyme@example.com"
    client.post("/auth/register", json={"full_name": "V", "email": email, "password": "Passw0rd!"})

    from src.db.database import SessionLocal
    from src.models.user import User
    from src.core.security import generate_reset_token, hash_reset_token

    # Same reasoning as the password-reset tests: the raw token is never
    # persisted (only its hash), so simulate having it from the "emailed"
    # link by generating one and overwriting the stored hash directly.
    raw_token, hashed = generate_reset_token()
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.verification_token_hash = hashed
    from datetime import datetime, timedelta, timezone
    user.verification_token_expires = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=24)
    db.commit()
    db.close()

    r = client.post("/auth/verify-email", json={"email": email, "token": raw_token})
    assert r.status_code == 200

    login_token = client.post("/auth/login", json={"email": email, "password": "Passw0rd!"}).json()["access_token"]
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {login_token}"})
    assert r.json()["email_verified"] is True


def test_verify_email_rejects_wrong_token(client):
    email = "verifybad@example.com"
    client.post("/auth/register", json={"full_name": "V", "email": email, "password": "Passw0rd!"})

    r = client.post("/auth/verify-email", json={"email": email, "token": "not-the-real-token"})
    assert r.status_code == 400


def test_google_accounts_start_pre_verified(client):
    # Can't exercise the real Google OAuth handshake without live
    # credentials, but the service function itself is directly testable.
    from src.db.database import SessionLocal
    from src.services.auth_service import login_or_register_with_google

    db = SessionLocal()
    login_or_register_with_google(db, google_sub="abc123", email="googleuser@example.com", full_name="G User")
    from src.models.user import User
    user = db.query(User).filter(User.email == "googleuser@example.com").first()
    assert user.email_verified == 1
    db.close()


# --- Two-factor authentication -------------------------------------------

def test_2fa_setup_and_login_flow(client):
    token = _register(client, "twofa@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    setup = client.post("/auth/2fa/setup", headers=headers)
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_url"].startswith("otpauth://")

    valid_code = pyotp.TOTP(secret).now()
    confirm = client.post("/auth/2fa/confirm", headers=headers, json={"code": valid_code})
    assert confirm.status_code == 200
    backup_codes = confirm.json()["backup_codes"]
    assert len(backup_codes) == 8

    # Old access token (issued before 2FA was enabled) should now be dead --
    # token_version was bumped on confirm.
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 401

    # Logging in now requires the second factor.
    login_resp = client.post("/auth/login", json={"email": "twofa@example.com", "password": "Passw0rd!"})
    assert login_resp.status_code == 200
    body = login_resp.json()
    assert body["requires_2fa"] is True
    assert body["access_token"] is None
    pending_token = body["pending_token"]

    # Wrong code rejected.
    r = client.post("/auth/2fa/verify-login", json={"pending_token": pending_token, "code": "000000"})
    assert r.status_code == 401

    # Correct code succeeds.
    new_code = pyotp.TOTP(secret).now()
    r = client.post("/auth/2fa/verify-login", json={"pending_token": pending_token, "code": new_code})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_2fa_backup_code_login(client):
    token = _register(client, "twofabackup@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    secret = client.post("/auth/2fa/setup", headers=headers).json()["secret"]
    backup_codes = client.post(
        "/auth/2fa/confirm", headers=headers, json={"code": pyotp.TOTP(secret).now()}
    ).json()["backup_codes"]

    login_resp = client.post("/auth/login", json={"email": "twofabackup@example.com", "password": "Passw0rd!"})
    pending_token = login_resp.json()["pending_token"]

    code = backup_codes[0]
    r = client.post("/auth/2fa/verify-login", json={"pending_token": pending_token, "code": code})
    assert r.status_code == 200

    # Backup codes are single-use -- the same one fails a second time.
    login_resp2 = client.post("/auth/login", json={"email": "twofabackup@example.com", "password": "Passw0rd!"})
    pending_token2 = login_resp2.json()["pending_token"]
    r = client.post("/auth/2fa/verify-login", json={"pending_token": pending_token2, "code": code})
    assert r.status_code == 401


def test_2fa_disable_requires_password(client):
    token = _register(client, "twofadisable@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    secret = client.post("/auth/2fa/setup", headers=headers).json()["secret"]
    client.post("/auth/2fa/confirm", headers=headers, json={"code": pyotp.TOTP(secret).now()})

    # Get a fresh token (the setup/confirm flow bumped token_version).
    login_resp = client.post("/auth/login", json={"email": "twofadisable@example.com", "password": "Passw0rd!"})
    pending_token = login_resp.json()["pending_token"]
    fresh_token = client.post(
        "/auth/2fa/verify-login",
        json={"pending_token": pending_token, "code": pyotp.TOTP(secret).now()},
    ).json()["access_token"]
    fresh_headers = {"Authorization": f"Bearer {fresh_token}"}

    r = client.post("/auth/2fa/disable", headers=fresh_headers, json={"password": "WrongPassword1"})
    assert r.status_code == 401

    r = client.post("/auth/2fa/disable", headers=fresh_headers, json={"password": "Passw0rd!"})
    assert r.status_code == 200

    # 2FA is off now -- login goes straight to tokens again.
    login_resp = client.post("/auth/login", json={"email": "twofadisable@example.com", "password": "Passw0rd!"})
    assert "access_token" in login_resp.json()
    assert login_resp.json().get("requires_2fa") in (False, None)
