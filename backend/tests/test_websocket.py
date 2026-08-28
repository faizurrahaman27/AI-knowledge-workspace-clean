def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


def test_websocket_rejects_missing_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws/workspace/1"):
            pass


def test_websocket_rejects_invalid_token(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/workspace/1?token=not-a-real-token"):
            pass
    assert exc_info.value.code == 4401


def test_websocket_rejects_workspace_you_cant_access(client):
    import pytest
    from starlette.websockets import WebSocketDisconnect

    token = _register(client, "wsauth@example.com")

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/workspace/99999?token=" + token):
            pass
    assert exc_info.value.code == 4403


def test_websocket_connects_and_gets_presence(client):
    token = _register(client, "wsconnect@example.com")
    ws_resp = client.post("/workspaces/", headers={"Authorization": f"Bearer {token}"}, json={"name": "Live"})
    workspace_id = ws_resp.json()["id"]

    with client.websocket_connect(f"/ws/workspace/{workspace_id}?token={token}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "presence"
        assert data["online"] == 1


def test_websocket_broadcasts_chat_to_connected_member(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_pages_from_pdf",
        lambda path: [{"page": 1, "text": "Some real extracted content for broadcasting."}],
    )

    token = _register(client, "wsbroadcast@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    ws_id = client.post("/workspaces/", headers=headers, json={"name": "Broadcast"}).json()["id"]

    import io
    doc_id = client.post(
        "/documents/upload", headers=headers,
        files={"file": ("b.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")},
    ).json()["id"]
    client.post(f"/workspaces/{ws_id}/documents", headers=headers, json={"document_id": doc_id})

    with client.websocket_connect(f"/ws/workspace/{ws_id}?token={token}") as websocket:
        websocket.receive_json()  # initial presence broadcast on connect

        r = client.post(
            "/chat/", headers=headers,
            json={"question": "broadcast test", "workspace_id": ws_id},
        )
        assert r.status_code == 200

        # The chat turn should have been pushed to the open socket.
        event = websocket.receive_json()
        assert event["type"] == "chat_message"
        assert event["question"] == "broadcast test"
