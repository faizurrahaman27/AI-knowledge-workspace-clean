"""
OCR for the "Scan" feature: photos, receipts, whiteboards, handwritten
notes, book pages, IDs. Uses Tesseract (via pytesseract) -- runs fully
offline, no API cost.

Requires the `tesseract-ocr` system package AND language data for
whatever languages you need -- see docker/Dockerfile.backend, which
installs `tesseract-ocr-all` (every bundled language pack) specifically
so this isn't English-only. Manual install:
  Ubuntu/Debian: `apt install tesseract-ocr-all`
  macOS:         `brew install tesseract-lang`
"""

from PIL import Image, ImageOps

from src.utils.language import get_tesseract_code

# A broad multi-language pass used when no language is specified and we
# have no prior hint (e.g. a fresh scan with unknown content). Tesseract
# can combine multiple languages in one pass, picking the best match per
# word -- accuracy degrades if you throw dozens in at once, so this is a
# deliberately curated "most common" set, not literally every language.
DEFAULT_OCR_LANGS = ["eng", "hin", "spa", "fra", "deu", "ara", "chi_sim", "por", "rus"]


def extract_text_from_image(file_path: str, language_code: str | None = None) -> str:
    import pytesseract

    image = Image.open(file_path)

    # Basic preprocessing: grayscale + auto-contrast tends to meaningfully
    # improve Tesseract accuracy on phone photos (uneven lighting, etc.)
    # without the complexity of a full deskew/binarization pipeline.
    image = ImageOps.exif_transpose(image)  # respect phone camera orientation
    image = image.convert("L")
    image = ImageOps.autocontrast(image)

    if language_code:
        # Caller (or the frontend's language picker) knows the language --
        # use it directly for the best accuracy.
        lang_string = get_tesseract_code(language_code)
    else:
        lang_string = "+".join(DEFAULT_OCR_LANGS)

    try:
        return pytesseract.image_to_string(image, lang=lang_string)
    except pytesseract.TesseractError:
        # A requested language pack isn't installed on this machine --
        # fall back to English rather than failing the whole scan, and
        # let the caller know via the returned text being possibly wrong
        # (detect_language() downstream will reflect the real result).
        return pytesseract.image_to_string(image, lang="eng")
