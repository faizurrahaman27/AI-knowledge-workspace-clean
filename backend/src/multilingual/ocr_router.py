"""
OCR Language Router

Routes OCR requests to appropriate language packs.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

from src.multilingual.registry import get_language_registry
from src.core.logging import logger

logger = logging.getLogger(__name__)


@dataclass
class OCRLanguagePack:
    """OCR language pack configuration."""
    language: str
    tesseract_lang: str  # Tesseract language code
    requires_extra: bool  # Requires extra language pack
    preprocess_steps: List[str]  # Preprocessing steps
    confidence_boost: float  # Confidence boost for this language


class OCRLanguageRouter:
    """
    Router for OCR language packs.
    
    Determines which OCR language packs to use based on:
    - Detected script
    - Document content hints
    - User preferences
    """
    
    # Tesseract language codes mapping
    TESSERACT_LANG_MAP = {
        "en": "eng",
        "ar": "ara",
        "zh": "chi_sim+chi_tra",  # Simplified + Traditional
        "ja": "jpn",
        "ko": "kor",
        "hi": "hin",
        "es": "spa",
        "fr": "fra",
        "de": "deu",
        "pt": "por",
        "ru": "rus",
        "it": "ita",
        "tr": "tur",
        "vi": "vie",
        "th": "tha",
        "bn": "ben",
        "ta": "tam",
        "te": "tel",
        "uk": "ukr",
        "pl": "pol",
        "nl": "nld",
        "el": "gre",
        "cs": "ces",
        "ro": "ron",
        "hu": "hun",
        "sv": "swe",
        "he": "heb",
        "fa": "fas",
        "ur": "urd",
    }
    
    # Preprocessing steps per script
    PREPROCESS_MAP = {
        "latin": ["grayscale", "threshold"],
        "arabic": ["binarize", "deskew", "denoise"],
        "cyrillic": ["grayscale", "threshold"],
        "devanagari": ["binarize", "deskew"],
        "cjk": ["binarize", "resize_2x"],
        "tamil": ["binarize", "enhance"],
        "telugu": ["binarize", "enhance"],
        "hebrew": ["binarize", "deskew"],
        "thai": ["binarize", "enhance"],
    }
    
    def __init__(self):
        """Initialize the OCR language router."""
        self.registry = get_language_registry()
    
    def determine_language_packs(
        self,
        text_hint: Optional[str] = None,
        detected_languages: Optional[List[str]] = None,
        script_hint: Optional[str] = None
    ) -> List[OCRLanguagePack]:
        """
        Determine which OCR language packs to use.
        
        Args:
            text_hint: Optional text sample for detection
            detected_languages: Pre-detected languages
            script_hint: Script type hint
            
        Returns:
            List of language packs to use
        """
        packs = []
        
        # If languages detected, use those
        if detected_languages:
            for lang in detected_languages:
                pack = self._create_language_pack(lang)
                if pack:
                    packs.append(pack)
            return packs
        
        # If script hint provided, use all languages for that script
        if script_hint:
            languages = self.registry.get_by_script(script_hint)
            for lang in languages:
                if lang.has_ocr:
                    pack = self._create_language_pack(lang.code)
                    if pack:
                        packs.append(pack)
            return packs
        
        # Default to common languages
        common_langs = ["en", "es", "fr", "de", "pt", "it", "ru", "ar", "zh", "ja", "ko", "hi"]
        
        for lang in common_langs:
            pack = self._create_language_pack(lang)
            if pack:
                packs.append(pack)
        
        return packs
    
    def _create_language_pack(self, language: str) -> Optional[OCRLanguagePack]:
        """Create language pack for OCR."""
        lang_info = self.registry.get(language)
        
        if not lang_info or not lang_info.has_ocr:
            return None
        
        return OCRLanguagePack(
            language=language,
            tesseract_lang=self.TESSERACT_LANG_MAP.get(language, language),
            requires_extra=self._requires_extra_pack(language),
            preprocess_steps=self.PREPROCESS_MAP.get(lang_info.script_type, ["grayscale"]),
            confidence_boost=1.0 if language in ["en", "es", "fr", "de", "zh", "ja"] else 0.9
        )
    
    def _requires_extra_pack(self, language: str) -> bool:
        """Check if language requires extra Tesseract pack."""
        # Languages that need extra installation
        extra_packs = ["zh", "ja", "ko", "ar", "hi", "ta", "te", "th", "bn"]
        return language in extra_packs
    
    def get_tesseract_config(
        self,
        packs: List[OCRLanguagePack]
    ) -> Dict[str, Any]:
        """
        Get Tesseract configuration for language packs.
        
        Args:
            packs: Language packs to use
            
        Returns:
            Configuration dict for Tesseract
        """
        # Combine all language codes
        lang_codes = "+".join([p.tesseract_lang for p in packs])
        
        # Build preprocessing pipeline
        preprocess_steps = []
        for pack in packs:
            preprocess_steps.extend(pack.preprocess_steps)
        
        # Deduplicate preprocessing steps while preserving order
        seen = set()
        unique_preprocess = []
        for step in preprocess_steps:
            if step not in seen:
                seen.add(step)
                unique_preprocess.append(step)
        
        return {
            "lang": lang_codes,
            "oem": 3,  # LSTM neural network
            "psm": 3,  # Fully automatic page segmentation
            "preprocess": unique_preprocess
        }
    
    def get_language_packs_for_document(
        self,
        document_bytes: bytes,
        mime_type: str
    ) -> List[OCRLanguagePack]:
        """
        Determine language packs for a document.
        
        Args:
            document_bytes: Document bytes
            mime_type: MIME type
            
        Returns:
            List of language packs
        """
        # Default to common languages based on document type
        if mime_type.startswith("image/"):
            # Image - use common OCR languages
            packs = self.determine_language_packs(
                detected_languages=["en", "es", "fr", "de", "ar", "zh", "ja", "ko", "hi"]
            )
        elif mime_type == "application/pdf":
            # PDF - try to detect from first bytes or use defaults
            packs = self.determine_language_packs(
                detected_languages=["en"]
            )
        else:
            # Default
            packs = self.determine_language_packs(
                detected_languages=["en"]
            )
        
        return packs
    
    def estimate_processing_time(
        self,
        packs: List[OCRLanguagePack],
        page_count: int = 1
    ) -> int:
        """
        Estimate OCR processing time in seconds.
        
        Args:
            packs: Language packs
            page_count: Number of pages
            
        Returns:
            Estimated seconds
        """
        # Base time per page
        base_time = 2
        
        # Add time for each language pack
        pack_time = 0.5 * len(packs)
        
        # Add time for complex scripts
        for pack in packs:
            if pack.language in ["zh", "ja", "ko"]:
                pack_time += 2
            elif pack.language in ["ar", "hi", "ta"]:
                pack_time += 1
        
        return int((base_time + pack_time) * page_count)


# Global router instance
_router: Optional[OCRLanguageRouter] = None


def get_ocr_language_router() -> OCRLanguageRouter:
    """Get the global OCR language router."""
    global _router
    if _router is None:
        _router = OCRLanguageRouter()
    return _router
