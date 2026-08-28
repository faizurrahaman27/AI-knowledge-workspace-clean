"""
Lightweight language detection for uploaded documents.

Uses `langdetect` (a pure-Python, offline port of Google's language-detection
library -- no model download, no network call), so it's cheap to run at
ingestion time on a sample of the extracted text.
"""

from functools import lru_cache

LANGUAGE_NAMES = {
    "en": "English", "hi": "Hindi", "es": "Spanish", "fr": "French",
    "de": "German", "zh-cn": "Chinese", "ar": "Arabic", "pt": "Portuguese",
    "ru": "Russian", "ja": "Japanese", "te": "Telugu", "ta": "Tamil",
    "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati", "kn": "Kannada",
    "ml": "Malayalam", "pa": "Punjabi", "ur": "Urdu", "it": "Italian",
    "ko": "Korean", "tr": "Turkish", "vi": "Vietnamese", "id": "Indonesian",
    "nl": "Dutch", "pl": "Polish", "th": "Thai",
}

# BCP-47 tags for the Web Speech API (SpeechSynthesis voice matching /
# SpeechRecognition input language) -- langdetect's codes aren't always
# valid BCP-47 on their own (e.g. "zh-cn" needs normalizing to "zh-CN").
# Whether a given tag actually has an installed voice/recognizer is up to
# the user's OS/browser -- this only picks the correct tag to ask for.
SPEECH_LANG_TAGS = {
    "en": "en-US", "hi": "hi-IN", "es": "es-ES", "fr": "fr-FR",
    "de": "de-DE", "zh-cn": "zh-CN", "ar": "ar-SA", "pt": "pt-PT",
    "ru": "ru-RU", "ja": "ja-JP", "te": "te-IN", "ta": "ta-IN",
    "bn": "bn-IN", "mr": "mr-IN", "gu": "gu-IN", "kn": "kn-IN",
    "ml": "ml-IN", "pa": "pa-IN", "ur": "ur-PK", "it": "it-IT",
    "ko": "ko-KR", "tr": "tr-TR", "vi": "vi-VN", "id": "id-ID",
    "nl": "nl-NL", "pl": "pl-PL", "th": "th-TH",
}

# Tesseract OCR language codes (ISO 639-2/T, NOT the same alphabet as the
# 639-1 codes above -- Tesseract's own naming convention). Only used when
# the language pack is actually installed (see docker/Dockerfile.backend,
# which installs tesseract-ocr-all); falls back to English detection
# gracefully if a pack is missing rather than hard-failing OCR entirely.
TESSERACT_LANG_CODES = {
    "en": "eng", "hi": "hin", "es": "spa", "fr": "fra",
    "de": "deu", "zh-cn": "chi_sim", "ar": "ara", "pt": "por",
    "ru": "rus", "ja": "jpn", "te": "tel", "ta": "tam",
    "bn": "ben", "mr": "mar", "gu": "guj", "kn": "kan",
    "ml": "mal", "pa": "pan", "ur": "urd", "it": "ita",
    "ko": "kor", "tr": "tur", "vi": "vie", "id": "ind",
    "nl": "nld", "pl": "pol", "th": "tha",
}


def get_speech_tag(language_code: str) -> str:
    return SPEECH_LANG_TAGS.get(language_code, "en-US")


def get_tesseract_code(language_code: str) -> str:
    return TESSERACT_LANG_CODES.get(language_code, "eng")


def detect_language(sample_text: str) -> tuple[str, str]:
    """
    Returns (iso_code, display_name). Falls back to ("en", "English") if
    the text is too short/ambiguous to classify confidently -- that's a
    safe default for a mostly-English document set, and avoids a hard
    failure blocking document upload.
    """
    from langdetect import detect, LangDetectException

    text = (sample_text or "").strip()

    if len(text) < 20:
        return "en", "English"

    try:
        code = detect(text)
    except LangDetectException:
        return "en", "English"

    return code, LANGUAGE_NAMES.get(code, code.upper())
