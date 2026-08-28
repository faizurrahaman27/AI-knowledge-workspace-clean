import os
from uuid import uuid4

from fastapi import UploadFile, HTTPException

from src.core.logging import logger
from src.utils.ocr import extract_text_from_image
from src.utils.language import detect_language
from src.utils.llm import chat_completion

SCAN_DIR = "uploads/scans"

ALLOWED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


def _summarize_scan(extracted_text: str) -> str:
    """
    Produces a short, spoken-friendly summary of what's useful in the
    scanned content -- this is the text that gets read aloud by the
    frontend's voice-output feature.
    """
    if not extracted_text.strip():
        return "I couldn't find any readable text in this image."

    prompt = f"""
You are describing a scanned document/photo to someone who cannot see it.

Read the extracted text below and give a short (3-6 sentence), plain-spoken
summary of what it is and the most useful/important information in it
(e.g. for a receipt: total amount, date, merchant; for a note: the key
points; for an ID: what kind of document it is and key fields present --
do not read out full ID numbers aloud).

Do not use Markdown. Write it as natural spoken sentences.

Extracted text:
{extracted_text}
"""

    return chat_completion([{"role": "user", "content": prompt}], temperature=0.3)


def analyze_scan(file: UploadFile, language_code: str | None = None):
    original_name = os.path.basename(file.filename or "scan.jpg")
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type '{ext}'. Allowed: {sorted(ALLOWED_IMAGE_TYPES)}",
        )

    os.makedirs(SCAN_DIR, exist_ok=True)
    temp_path = os.path.join(SCAN_DIR, f"{uuid4()}{ext}")

    with open(temp_path, "wb") as f:
        f.write(file.file.read())

    try:
        if language_code:
            # User told us the language up front (frontend picker) --
            # skip straight to a targeted, more accurate single-language pass.
            extracted_text = extract_text_from_image(temp_path, language_code=language_code)
            detected_code, detected_name = language_code, None
        else:
            # Pass 1: broad multi-language OCR to figure out what we're
            # even looking at.
            first_pass_text = extract_text_from_image(temp_path)
            detected_code, detected_name = detect_language(first_pass_text)

            # Pass 2: if we're confident it's a specific non-English
            # language, re-run OCR targeted at just that language --
            # Tesseract is more accurate with 1 language than with the
            # broad combined set, so this second pass is usually cleaner
            # than the first.
            if detected_code != "en" and len(first_pass_text.strip()) > 15:
                extracted_text = extract_text_from_image(temp_path, language_code=detected_code)
            else:
                extracted_text = first_pass_text
    except Exception:
        logger.exception("OCR failed for scanned image")
        raise HTTPException(
            status_code=422,
            detail="Could not read text from this image. Try a clearer photo.",
        )
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    if detected_name is None:
        detected_code, detected_name = detect_language(extracted_text)

    summary = _summarize_scan(extracted_text)

    return {
        "extracted_text": extracted_text.strip(),
        "summary": summary.strip(),
        "language_code": detected_code,
        "language_name": detected_name,
    }
