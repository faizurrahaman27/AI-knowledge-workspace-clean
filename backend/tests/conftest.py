"""
Shared pytest fixtures.

Heavy ML dependencies (sentence-transformers, chromadb, PyMuPDF, ollama)
are stubbed out here so the test suite runs fast and offline. This is
appropriate for unit/integration tests of the API layer, auth, guardrails,
and chunking logic. It does NOT replace manually testing the real
retrieval quality with the real models -- see evaluation/README.md for that.
"""

import os
import sys
import tempfile

import pytest

STUBS_DIR = os.path.join(os.path.dirname(__file__), "stubs")
sys.path.insert(0, STUBS_DIR)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Fresh SQLite DB per test, isolated temp dir for uploads/chroma.
    db_path = tmp_path / "test.db"

    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("APP_VERSION", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("REFRESH_SECRET_KEY", "test-refresh-secret-key")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.chdir(tmp_path)

    # Reload settings/engine bound to the new env vars.
    for mod in list(sys.modules):
        if mod.startswith("src."):
            del sys.modules[mod]

    from fastapi.testclient import TestClient
    from src.main import app

    return TestClient(app)


@pytest.fixture()
def auth_headers(client):
    client.post(
        "/auth/register",
        json={
            "full_name": "Test User",
            "email": "test@example.com",
            "password": "Passw0rd!",
        },
    )
    response = client.post(
        "/auth/login",
        json={"email": "test@example.com", "password": "Passw0rd!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
