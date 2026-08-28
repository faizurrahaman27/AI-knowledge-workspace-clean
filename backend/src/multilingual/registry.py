"""
Language Registry

Registry of supported languages with metadata.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from enum import Enum


class WritingDirection(str, Enum):
    """Writing direction."""
    LTR = "ltr"
    RTL = "rtl"
    MIXED = "mixed"


@dataclass
class LanguageInfo:
    """Language information."""
    code: str  # ISO 639-1 code
    iso_name: str  # English name
    native_name: str  # Native name
    script_type: str
    writing_direction: WritingDirection = WritingDirection.LTR
    has_ocr: bool = False
    has_embeddings: bool = False
    has_tts: bool = False
    nlp_priority: int = 5
    related_languages: List[str] = field(default_factory=list)


class LanguageRegistry:
    """
    Registry of supported languages.
    
    Contains metadata for 100+ languages including:
    - Script information
    - Writing direction
    - NLP support flags
    - Language relationships
    """
    
    # Complete language registry
    LANGUAGES: Dict[str, LanguageInfo] = {
        # English
        "en": LanguageInfo(
            code="en", iso_name="English", native_name="English",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=1
        ),
        
        # Arabic
        "ar": LanguageInfo(
            code="ar", iso_name="Arabic", native_name="العربية",
            script_type="arabic", writing_direction=WritingDirection.RTL,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Chinese
        "zh": LanguageInfo(
            code="zh", iso_name="Chinese", native_name="中文",
            script_type="cjk", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Japanese
        "ja": LanguageInfo(
            code="ja", iso_name="Japanese", native_name="日本語",
            script_type="cjk", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Korean
        "ko": LanguageInfo(
            code="ko", iso_name="Korean", native_name="한국어",
            script_type="cjk", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Hindi
        "hi": LanguageInfo(
            code="hi", iso_name="Hindi", native_name="हिन्दी",
            script_type="devanagari", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Spanish
        "es": LanguageInfo(
            code="es", iso_name="Spanish", native_name="Español",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=1,
            related_languages=["pt", "it", "fr"]
        ),
        
        # French
        "fr": LanguageInfo(
            code="fr", iso_name="French", native_name="Français",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=1,
            related_languages=["es", "it", "pt", "ro"]
        ),
        
        # German
        "de": LanguageInfo(
            code="de", iso_name="German", native_name="Deutsch",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=1,
            related_languages=["nl", "en"]
        ),
        
        # Portuguese
        "pt": LanguageInfo(
            code="pt", iso_name="Portuguese", native_name="Português",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2,
            related_languages=["es", "fr", "it"]
        ),
        
        # Russian
        "ru": LanguageInfo(
            code="ru", iso_name="Russian", native_name="Русский",
            script_type="cyrillic", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2,
            related_languages=["uk", "be"]
        ),
        
        # Italian
        "it": LanguageInfo(
            code="it", iso_name="Italian", native_name="Italiano",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2,
            related_languages=["es", "fr", "pt"]
        ),
        
        # Turkish
        "tr": LanguageInfo(
            code="tr", iso_name="Turkish", native_name="Türkçe",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Persian/Farsi
        "fa": LanguageInfo(
            code="fa", iso_name="Persian", native_name="فارسی",
            script_type="arabic", writing_direction=WritingDirection.RTL,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Urdu
        "ur": LanguageInfo(
            code="ur", iso_name="Urdu", native_name="اردو",
            script_type="arabic", writing_direction=WritingDirection.RTL,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=2
        ),
        
        # Hebrew
        "he": LanguageInfo(
            code="he", iso_name="Hebrew", native_name="עברית",
            script_type="hebrew", writing_direction=WritingDirection.RTL,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Thai
        "th": LanguageInfo(
            code="th", iso_name="Thai", native_name="ไทย",
            script_type="thai", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Vietnamese
        "vi": LanguageInfo(
            code="vi", iso_name="Vietnamese", native_name="Tiếng Việt",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Indonesian
        "id": LanguageInfo(
            code="id", iso_name="Indonesian", native_name="Bahasa Indonesia",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Tamil
        "ta": LanguageInfo(
            code="ta", iso_name="Tamil", native_name="தமிழ்",
            script_type="tamil", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Telugu
        "te": LanguageInfo(
            code="te", iso_name="Telugu", native_name="తెలుగు",
            script_type="telugu", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=False,
            nlp_priority=3
        ),
        
        # Bengali
        "bn": LanguageInfo(
            code="bn", iso_name="Bengali", native_name="বাংলা",
            script_type="bengali", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Ukrainian
        "uk": LanguageInfo(
            code="uk", iso_name="Ukrainian", native_name="Українська",
            script_type="cyrillic", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Dutch
        "nl": LanguageInfo(
            code="nl", iso_name="Dutch", native_name="Nederlands",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3,
            related_languages=["de", "en"]
        ),
        
        # Polish
        "pl": LanguageInfo(
            code="pl", iso_name="Polish", native_name="Polski",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Greek
        "el": LanguageInfo(
            code="el", iso_name="Greek", native_name="Ελληνικά",
            script_type="greek", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Czech
        "cs": LanguageInfo(
            code="cs", iso_name="Czech", native_name="Čeština",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=3
        ),
        
        # Swedish
        "sv": LanguageInfo(
            code="sv", iso_name="Swedish", native_name="Svenska",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=4
        ),
        
        # Hungarian
        "hu": LanguageInfo(
            code="hu", iso_name="Hungarian", native_name="Magyar",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=4
        ),
        
        # Romanian
        "ro": LanguageInfo(
            code="ro", iso_name="Romanian", native_name="Română",
            script_type="latin", writing_direction=WritingDirection.LTR,
            has_ocr=True, has_embeddings=True, has_tts=True,
            nlp_priority=4,
            related_languages=["fr", "it", "es"]
        ),
    }
    
    def __init__(self):
        """Initialize the language registry."""
        self._embeddings_cache: Set[str] = set()
        self._ocr_cache: Set[str] = set()
        
        # Build capability caches
        for code, info in self.LANGUAGES.items():
            if info.has_embeddings:
                self._embeddings_cache.add(code)
            if info.has_ocr:
                self._ocr_cache.add(code)
    
    def get(self, code: str) -> Optional[LanguageInfo]:
        """Get language info by code."""
        return self.LANGUAGES.get(code)
    
    def get_all(self) -> List[LanguageInfo]:
        """Get all languages."""
        return list(self.LANGUAGES.values())
    
    def get_by_script(self, script_type: str) -> List[LanguageInfo]:
        """Get languages by script type."""
        return [
            info for info in self.LANGUAGES.values()
            if info.script_type == script_type
        ]
    
    def get_rtl_languages(self) -> List[LanguageInfo]:
        """Get all RTL languages."""
        return [
            info for info in self.LANGUAGES.values()
            if info.writing_direction == WritingDirection.RTL
        ]
    
    def get_languages_with_embeddings(self) -> List[str]:
        """Get codes of languages with embedding support."""
        return list(self._embeddings_cache)
    
    def get_languages_with_ocr(self) -> List[str]:
        """Get codes of languages with OCR support."""
        return list(self._ocr_cache)
    
    def supports_embeddings(self, code: str) -> bool:
        """Check if language has embedding support."""
        return code in self._embeddings_cache
    
    def supports_ocr(self, code: str) -> bool:
        """Check if language has OCR support."""
        return code in self._ocr_cache
    
    def is_rtl(self, code: str) -> bool:
        """Check if language is RTL."""
        info = self.LANGUAGES.get(code)
        return info.writing_direction == WritingDirection.RTL if info else False
    
    def get_related_languages(self, code: str) -> List[str]:
        """Get related languages."""
        info = self.LANGUAGES.get(code)
        return info.related_languages if info else []
    
    def search(self, query: str) -> List[LanguageInfo]:
        """Search languages by name."""
        query_lower = query.lower()
        results = []
        
        for info in self.LANGUAGES.values():
            if (query_lower in info.iso_name.lower() or 
                query_lower in info.native_name.lower() or
                query_lower in info.code.lower()):
                results.append(info)
        
        return results


# Global registry instance
_registry: Optional[LanguageRegistry] = None


def get_language_registry() -> LanguageRegistry:
    """Get the global language registry."""
    global _registry
    if _registry is None:
        _registry = LanguageRegistry()
    return _registry
