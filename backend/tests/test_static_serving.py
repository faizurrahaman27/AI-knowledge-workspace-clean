"""
Regression coverage for main.py's single-container static-file serving
(used by the Hugging Face Spaces / free-tier deployment path).

This exists because of a real bug caught manually while building this
feature: api/health.py registered a GET "/" route that silently shadowed
the frontend's index.html, since it was included before the static-file
catch-all. The symptom was invisible in normal two-container (nginx)
deployments -- nginx serves index.html directly and never asks the
backend for "/" -- so it would only have surfaced after a real single-
container deploy. This test exercises the exact ordering that broke.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "stubs"))


def _make_fake_static_dir(tmp_path):
    static_dir = tmp_path / "static"
    (static_dir / "assets").mkdir(parents=True)
    (static_dir / "index.html").write_text('<html><body><div id="root"></div></body></html>')
    (static_dir / "assets" / "app.js").write_text("console.log('ok');")
    return static_dir


def test_root_serves_frontend_when_static_dir_present(tmp_path, monkeypatch):
    static_dir = _make_fake_static_dir(tmp_path)

    monkeypatch.setenv("APP_NAME", "Test App")
    monkeypatch.setenv("APP_VERSION", "test")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("REFRESH_SECRET_KEY", "test-refresh-secret-key")
    monkeypatch.setenv("ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1000")
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("STATIC_DIR", str(static_dir))
    monkeypatch.chdir(tmp_path)

    for mod in list(sys.modules):
        if mod == "src" or mod.startswith("src."):
            del sys.modules[mod]

    from fastapi.testclient import TestClient
    from src.main import app

    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}

    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert 'id="root"' in r.text

    # SPA client-side route falls back to index.html, not a 404.
    r = client.get("/some/frontend/route")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]

    r = client.get("/assets/app.js")
    assert r.status_code == 200
