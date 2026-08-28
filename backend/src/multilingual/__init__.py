"""
Multilingual Intelligence Module

Universal language support for AI Knowledge Workspace.
"""

from src.multilingual.models import (
    Language,
    LanguagePreference,
    DocumentLanguage,
    ChunkLanguage,
    TranslationCache,
    CrossLanguageMapping,
    LanguageMetric,
    WritingDirection,
    ScriptType,
)

from src.multilingual.detector import (
    LanguageDetector,
    LanguageDetectionResult,
    get_language_detector,
)

from src.multilingual.normalizer import (
    UnicodeNormalizer,
    get_unicode_normalizer,
)

from src.multilingual.registry import (
    LanguageRegistry,
    LanguageInfo,
    WritingDirection as RegWritingDirection,
    get_language_registry,
)

from src.multilingual.search import (
    CrossLanguageSearchService,
    get_cross_language_search_service,
)

from src.multilingual.generation import (
    MultilingualGenerationService,
    get_multilingual_generation_service,
)

from src.multilingual.preferences import (
    LanguagePreferenceService,
    get_language_preference_service,
)

from src.multilingual.ocr_router import (
    OCRLanguageRouter,
    OCRLanguagePack,
    get_ocr_language_router,
)

from src.multilingual.rtl_renderer import (
    RTLRenderer,
    RTLConfig,
    get_rtl_renderer,
)

__all__ = [
    # Models
    "Language",
    "LanguagePreference",
    "DocumentLanguage",
    "ChunkLanguage",
    "TranslationCache",
    "CrossLanguageMapping",
    "LanguageMetric",
    "WritingDirection",
    "ScriptType",
    # Detector
    "LanguageDetector",
    "LanguageDetectionResult",
    "get_language_detector",
    # Normalizer
    "UnicodeNormalizer",
    "get_unicode_normalizer",
    # Registry
    "LanguageRegistry",
    "LanguageInfo",
    "get_language_registry",
    # Search
    "CrossLanguageSearchService",
    "get_cross_language_search_service",
    # Generation
    "MultilingualGenerationService",
    "get_multilingual_generation_service",
    # Preferences
    "LanguagePreferenceService",
    "get_language_preference_service",
    # OCR
    "OCRLanguageRouter",
    "OCRLanguagePack",
    "get_ocr_language_router",
    # RTL
    "RTLRenderer",
    "RTLConfig",
    "get_rtl_renderer",
]
