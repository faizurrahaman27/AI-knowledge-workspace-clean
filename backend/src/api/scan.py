from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel

from src.dependencies.auth import get_current_user
from src.models.user import User
from src.services.scan_service import analyze_scan
from src.utils.language import LANGUAGE_NAMES

router = APIRouter(prefix="/scan", tags=["Scan"])


class ScanResponse(BaseModel):
    extracted_text: str
    summary: str
    language_code: str
    language_name: str


class VisualUnderstandResponse(BaseModel):
    description: str


@router.get("/languages")
def list_ocr_languages():
    """Languages the Scan feature can target explicitly (see
    docker/Dockerfile.backend's tesseract-ocr-all for why these all work,
    not just English)."""
    return [{"code": code, "name": name} for code, name in sorted(LANGUAGE_NAMES.items(), key=lambda x: x[1])]


@router.post("/analyze", response_model=ScanResponse)
def scan_analyze(
    file: UploadFile = File(...),
    language_code: str | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    OCR + "what's useful here" summary for a photo: receipts, notes,
    whiteboards, book pages, IDs, etc. Returns text for the frontend's
    voice-output (Web Speech API) to read aloud.

    `language_code` is optional -- if omitted, this runs a broad
    multi-language OCR pass, detects the language from the result, then
    re-runs OCR targeted at that specific language for better accuracy.
    Pass it explicitly (from the frontend's language picker) to skip
    straight to the targeted pass when you already know the language.

    Note: this is a standalone quick-scan tool, not yet wired into the
    document RAG/chat pipeline -- see README roadmap for "scan-to-document".
    """
    return analyze_scan(file, language_code=language_code)


@router.post("/understand-visual", response_model=VisualUnderstandResponse)
def scan_understand_visual(
    file: UploadFile = File(...),
    question: str | None = Form(None),
    current_user: User = Depends(get_current_user),
):
    """
    EXPERIMENTAL / requires `ollama pull llama3.2-vision` on the server --
    not covered by the automated test suite (see utils/vision.py docstring).
    For diagrams, flowcharts, charts, and tables where OCR-only text
    extraction loses the visual structure.
    """
    import os
    import tempfile
    from src.utils.vision import describe_visual

    suffix = os.path.splitext(file.filename or "image.jpg")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file.file.read())
        tmp_path = tmp.name

    try:
        description = describe_visual(tmp_path, question)
    finally:
        os.remove(tmp_path)

    return VisualUnderstandResponse(description=description)
