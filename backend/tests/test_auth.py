def test_register_and_login(client):
    r = client.post(
        "/auth/register",
        json={"full_name": "Alice", "email": "alice@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "alice@example.com"
    assert body["role"] == "customer"

    r = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Passw0rd!"},
    )
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens


def test_duplicate_registration_rejected(client):
    payload = {"full_name": "Bob", "email": "bob@example.com", "password": "Passw0rd!"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 400


def test_weak_password_rejected(client):
    r = client.post(
        "/auth/register",
        json={"full_name": "Weak", "email": "weak@example.com", "password": "short"},
    )
    assert r.status_code == 422


def test_wrong_password_rejected(client):
    client.post(
        "/auth/register",
        json={"full_name": "Carl", "email": "carl@example.com", "password": "Passw0rd!"},
    )
    r = client.post(
        "/auth/login",
        json={"email": "carl@example.com", "password": "WrongPassword1"},
    )
    assert r.status_code == 401


def test_refresh_token_issues_new_access_token(client):
    client.post(
        "/auth/register",
        json={"full_name": "Dana", "email": "dana@example.com", "password": "Passw0rd!"},
    )
    login = client.post(
        "/auth/login", json={"email": "dana@example.com", "password": "Passw0rd!"}
    )
    refresh_token = login.json()["refresh_token"]

    r = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_customer_cannot_access_admin_routes(client):
    client.post(
        "/auth/register",
        json={"full_name": "Eve", "email": "eve@example.com", "password": "Passw0rd!"},
    )
    login = client.post(
        "/auth/login", json={"email": "eve@example.com", "password": "Passw0rd!"}
    )
    token = login.json()["access_token"]

    r = client.get(
        "/auth/admin/users/list", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 403


def test_missing_token_rejected(client):
    r = client.get("/auth/me")
    assert r.status_code == 401
