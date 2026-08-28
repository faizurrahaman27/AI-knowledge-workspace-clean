import io

import pytest


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# --- SSRF protection (website ingestion) ------------------------------

def test_url_validation_rejects_localhost():
    from src.utils.web_extract import _validate_public_url, UrlIngestionError
    with pytest.raises(UrlIngestionError):
        _validate_public_url("http://localhost:8000/admin")


def test_url_validation_rejects_loopback_ip():
    from src.utils.web_extract import _validate_public_url, UrlIngestionError
    with pytest.raises(UrlIngestionError):
        _validate_public_url("http://127.0.0.1/secret")


def test_url_validation_rejects_cloud_metadata_endpoint():
    from src.utils.web_extract import _validate_public_url, UrlIngestionError
    with pytest.raises(UrlIngestionError):
        _validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_url_validation_rejects_non_http_scheme():
    from src.utils.web_extract import _validate_public_url, UrlIngestionError
    with pytest.raises(UrlIngestionError):
        _validate_public_url("file:///etc/passwd")


def test_url_validation_accepts_public_domain(monkeypatch):
    from src.utils import web_extract

    monkeypatch.setattr(
        web_extract.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("93.184.216.34", 0))],
    )
    result = web_extract._validate_public_url("https://example.com/article")
    assert result == "https://example.com/article"


def test_url_validation_rejects_private_ip_via_dns_rebinding(monkeypatch):
    from src.utils import web_extract
    from src.utils.web_extract import UrlIngestionError

    monkeypatch.setattr(
        web_extract.socket, "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("10.0.0.5", 0))],
    )
    with pytest.raises(UrlIngestionError):
        web_extract._validate_public_url("https://sneaky-lookalike.example.com/")


# --- GitHub URL parsing -------------------------------------------------

def test_github_blob_url_converts_to_raw():
    from src.utils.github_extract import _to_raw_url
    raw = _to_raw_url("https://github.com/octocat/Hello-World/blob/main/README.md")
    assert raw == "https://raw.githubusercontent.com/octocat/Hello-World/main/README.md"


def test_github_raw_url_passes_through():
    from src.utils.github_extract import _to_raw_url
    url = "https://raw.githubusercontent.com/octocat/Hello-World/main/README.md"
    assert _to_raw_url(url) == url


def test_github_rejects_non_github_host():
    from src.utils.github_extract import _to_raw_url, GithubIngestionError
    with pytest.raises(GithubIngestionError):
        _to_raw_url("https://evil.com/github.com/octocat/Hello-World/blob/main/README.md")


def test_github_rejects_malformed_blob_url():
    from src.utils.github_extract import _to_raw_url, GithubIngestionError
    with pytest.raises(GithubIngestionError):
        _to_raw_url("https://github.com/octocat/Hello-World")


# --- Full ingestion flow (mocked HTTP) ----------------------------------

def test_ingest_from_url_end_to_end(client, monkeypatch):
    from src.utils import web_extract

    monkeypatch.setattr(web_extract, "_validate_public_url", lambda url: url)
    monkeypatch.setattr(
        web_extract, "fetch_and_extract_url",
        lambda url: (
            [{"page": 1, "text": "This article explains gradient descent in detail."}],
            "Gradient Descent Explained",
        ),
    )

    headers = _register(client, "urlingest@example.com")
    r = client.post("/documents/from-url", headers=headers, json={"url": "https://example.com/article"})
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "Gradient Descent Explained"
    assert body["content_type"] == "text/html"
    assert body["source_url"] == "https://example.com/article"


def test_ingest_from_url_rejects_ssrf_target(client, monkeypatch):
    headers = _register(client, "urlssrf@example.com")
    r = client.post("/documents/from-url", headers=headers, json={"url": "http://169.254.169.254/"})
    assert r.status_code == 422


def test_ingest_from_github_end_to_end(client, monkeypatch):
    from src.utils import github_extract

    monkeypatch.setattr(
        github_extract, "fetch_github_file",
        lambda url: ([{"page": 1, "text": "# My Project\n\nThis does X."}], "README.md"),
    )

    headers = _register(client, "githubingest@example.com")
    r = client.post(
        "/documents/from-github", headers=headers,
        json={"url": "https://github.com/octocat/Hello-World/blob/main/README.md"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["filename"] == "README.md"
    assert body["content_type"] == "text/plain"


def test_ingest_from_image_end_to_end(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_text_from_image",
        lambda path, language_code=None: "Total: $42.50\nDate: 2026-01-01\nStore: Example Mart",
    )

    headers = _register(client, "imageingest@example.com")
    r = client.post(
        "/documents/from-image", headers=headers,
        files={"file": ("receipt.jpg", io.BytesIO(b"fake jpeg bytes"), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["content_type"] == "image/ocr"


def test_ingest_from_image_rejects_empty_ocr_result(client, monkeypatch):
    import src.services.document_service as doc_service_mod
    monkeypatch.setattr(
        doc_service_mod, "extract_text_from_image", lambda path, language_code=None: ""
    )

    headers = _register(client, "imageempty@example.com")
    r = client.post(
        "/documents/from-image", headers=headers,
        files={"file": ("blank.jpg", io.BytesIO(b"fake jpeg bytes"), "image/jpeg")},
    )
    assert r.status_code == 422


def test_ingested_document_is_chattable(client, monkeypatch):
    """The real point of all this: an imported website/GitHub/image
    document should work through the exact same chat pipeline as a PDF."""
    from src.utils import web_extract

    monkeypatch.setattr(web_extract, "_validate_public_url", lambda url: url)
    monkeypatch.setattr(
        web_extract, "fetch_and_extract_url",
        lambda url: ([{"page": 1, "text": "Paris is the capital of France."}], "Capitals"),
    )

    headers = _register(client, "chattable@example.com")
    doc = client.post("/documents/from-url", headers=headers, json={"url": "https://example.com/capitals"}).json()

    r = client.post("/chat/", headers=headers, json={"question": "what is the capital of France?", "document_id": doc["id"]})
    assert r.status_code == 200
    assert "done" in r.text
