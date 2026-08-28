import io

from PIL import Image


def _register(client, email, password="Passw0rd!", name="User"):
    client.post("/auth/register", json={"full_name": name, "email": email, "password": password})
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _fake_image_bytes():
    img = Image.new("RGB", (20, 20), color="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf


def test_languages_endpoint_lists_many_languages(client):
    headers = _register(client, "lang1@example.com")
    r = client.get("/scan/languages")
    assert r.status_code == 200
    codes = [l["code"] for l in r.json()]
    assert "en" in codes
    assert "hi" in codes  # Hindi
    assert "te" in codes  # Telugu
    assert len(codes) > 15  # genuinely "many languages", not a token gesture


def test_scan_without_language_hint_runs_two_pass_ocr(client, monkeypatch):
    calls = []

    def fake_extract(path, language_code=None):
        calls.append(language_code)
        if language_code is None:
            return "Bonjour, ceci est un texte en français avec assez de mots pour detecter."
        return "Bonjour (refined pass)"

    import src.services.scan_service as scan_service_mod
    monkeypatch.setattr(scan_service_mod, "extract_text_from_image", fake_extract)

    headers = _register(client, "lang2@example.com")
    r = client.post(
        "/scan/analyze", headers=headers,
        files={"file": ("scan.jpg", _fake_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()

    # First pass with no language hint, then a second targeted pass once
    # French was detected from the first pass's text.
    assert calls[0] is None
    assert calls[1] == "fr"
    assert body["language_code"] == "fr"
    assert "refined pass" in body["extracted_text"]


def test_scan_with_explicit_language_skips_detection_pass(client, monkeypatch):
    calls = []

    def fake_extract(path, language_code=None):
        calls.append(language_code)
        return "Text extracted using the requested language pack."

    import src.services.scan_service as scan_service_mod
    monkeypatch.setattr(scan_service_mod, "extract_text_from_image", fake_extract)

    headers = _register(client, "lang3@example.com")
    r = client.post(
        "/scan/analyze", headers=headers,
        files={"file": ("scan.jpg", _fake_image_bytes(), "image/jpeg")},
        data={"language_code": "te"},
    )
    assert r.status_code == 200
    # Only ONE OCR pass -- the caller already told us the language.
    assert calls == ["te"]


def test_scan_short_english_text_skips_second_pass(client, monkeypatch):
    calls = []

    def fake_extract(path, language_code=None):
        calls.append(language_code)
        return "Hi"  # too short to trust a language detection on

    import src.services.scan_service as scan_service_mod
    monkeypatch.setattr(scan_service_mod, "extract_text_from_image", fake_extract)

    headers = _register(client, "lang4@example.com")
    r = client.post(
        "/scan/analyze", headers=headers,
        files={"file": ("scan.jpg", _fake_image_bytes(), "image/jpeg")},
    )
    assert r.status_code == 200
    assert calls == [None]  # single pass only
