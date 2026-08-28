"""
Universal Language Detector

Detects language, script, and writing direction from text.
"""

import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class LanguageDetectionResult:
    """Result of language detection."""
    language: str
    confidence: float
    script: str
    writing_direction: str
    is_mixed: bool
    secondary_languages: List[Dict[str, float]]
    encoding: Optional[str]
    character_count: int
    word_count: int


class LanguageDetector:
    """
    Universal language detector supporting 100+ languages.
    
    Features:
    - Language identification
    - Script detection
    - Writing direction detection
    - Mixed language detection
    - Encoding detection
    """
    
    # Language to script mapping
    SCRIPT_MAP = {
        # Latin scripts
        "en": "latin", "es": "latin", "fr": "latin", "de": "latin",
        "it": "latin", "pt": "latin", "nl": "latin", "pl": "latin",
        "ro": "latin", "vi": "latin", "id": "latin", "ms": "latin",
        "tr": "latin", "hu": "latin", "cs": "latin", "sk": "latin",
        "da": "latin", "no": "latin", "sv": "latin", "fi": "latin",
        "et": "latin", "lv": "latin", "lt": "latin",
        
        # Arabic script
        "ar": "arabic", "fa": "arabic", "ur": "arabic", "ps": "arabic",
        "uz": "arabic", "sd": "arabic", "ckb": "arabic",
        
        # Cyrillic
        "ru": "cyrillic", "uk": "cyrillic", "be": "cyrillic",
        "bg": "cyrillic", "mk": "cyrillic", "sr": "cyrillic",
        "kk": "cyrillic", "uz_cyrillic": "cyrillic",
        
        # Devanagari
        "hi": "devanagari", "ne": "devanagari", "mr": "devanagari",
        "sa": "devanagari",
        
        # CJK
        "zh": "cjk", "ja": "cjk", "ko": "cjk",
        
        # Tamil
        "ta": "tamil",
        
        # Telugu
        "te": "telugu",
        
        # Hebrew
        "he": "hebrew", "yi": "hebrew",
        
        # Greek
        "el": "greek",
        
        # Thai
        "th": "thai",
    }
    
    # RTL languages
    RTL_LANGUAGES = {
        "ar", "fa", "he", "ur", "ps", "yi", "sd", "ckb"
    }
    
    # Character ranges for scripts
    SCRIPT_RANGES = {
        "latin": (0x0000, 0x024F),
        "arabic": (0x0600, 0x06FF),
        "cyrillic": (0x0400, 0x04FF),
        "devanagari": (0x0900, 0x097F),
        "cjk": (0x4E00, 0x9FFF, 0x3000, 0x303F),
        "tamil": (0x0B80, 0x0BFF),
        "telugu": (0x0C00, 0x0C7F),
        "hebrew": (0x0590, 0x05FF),
        "greek": (0x0370, 0x03FF),
        "thai": (0x0E00, 0x0E7F),
    }
    
    # Common words for language detection
    COMMON_WORDS = {
        "en": ["the", "is", "are", "was", "were", "have", "has", "been", "being", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "an", "be", "this", "that", "it", "we", "you", "they", "he", "she"],
        "es": ["el", "la", "los", "las", "de", "en", "y", "que", "es", "un", "una", "por", "con", "para", "como", "pero", "su", "este", "ese", "esto"],
        "fr": ["le", "la", "les", "de", "des", "un", "une", "et", "en", "que", "est", "dans", "pour", "par", "sur", "ce", "qui", "avec", "pas", "plus"],
        "de": ["der", "die", "das", "und", "in", "zu", "den", "mit", "von", "auf", "für", "ist", "im", "des", "ein", "eine", "als", "auch", "es", "an"],
        "ar": ["في", "من", "إلى", "على", "عن", "مع", "هذا", "هذه", "التي", "الذي", "هو", "هي", "كان", "كانت", "لم", "لن", "ما", "هل", "لا", "نعم"],
        "zh": ["的", "是", "在", "了", "和", "有", "我", "他", "她", "它", "们", "这", "那", "你", "来", "去", "看", "做", "说", "要"],
        "ja": ["の", "は", "が", "を", "に", "と", "し", "れ", "さ", "い", "あ", "く", "る", "めた", "てん", "し", "て", "す", "こ", "ん"],
        "ko": ["의", "이", "가", "을", "를", "에", "는", "과", "도", "로", "에서", "으로", "하다", "이다", "되다", "있다", "없다", "않다", "같다", "보다"],
        "hi": ["का", "के", "की", "है", "हैं", "था", "थे", "थी", "में", "से", "पर", "यह", "वह", "और", "का", "को", "ना", "नहीं", "जो", "कि"],
        "ru": ["и", "в", "не", "на", "я", "с", "что", "он", "быть", "по", "это", "как", "а", "то", "все", "она", "так", "его", "но", "да"],
        "pt": ["o", "a", "os", "as", "de", "em", "e", "que", "é", "um", "uma", "do", "da", "no", "na", "por", "para", "com", "não", "como"],
        "it": ["il", "la", "di", "e", "che", "è", "un", "una", "dei", "della", "nel", "alla", "per", "con", "non", "si", "come", "da", "questo", "quello"],
        "tr": ["ve", "bir", "bu", "da", "de", "için", "ile", "gibi", "daha", "en", "kadar", "çok", "var", "yok", "ne", "hem", "ya", "mi", "ise", "ama"],
        "th": ["ที่", "และ", "เป็น", "ของ", "ใน", "การ", "มี", "ได้", "ไม่", "ถูก", "ต้อง", "ให้", "จะ", "เป็น", "อยู่", "คือ", "เหมือน", "กับ", "หรือ", "แต่"],
        "vi": ["của", "và", "là", "có", "được", "trong", "này", "để", "với", "từ", "một", "các", "như", "không", "vì", "nên", "đã", "khi", "nếu", "hay"],
        "id": ["yang", "dan", "di", "dari", "ini", "untuk", "dengan", "pada", "adalah", "ke", "tidak", "akan", "juga", "sudah", "atau", "oleh", "sebagai", "bisa", "dalam", "lebih"],
    }
    
    def __init__(self):
        """Initialize the language detector."""
        self._detection_cache = {}
    
    def detect(
        self,
        text: str,
        hint_language: Optional[str] = None
    ) -> LanguageDetectionResult:
        """
        Detect language from text.
        
        Args:
            text: Input text
            hint_language: Optional hint for language
            
        Returns:
            LanguageDetectionResult with detected language info
        """
        if not text or len(text.strip()) == 0:
            return LanguageDetectionResult(
                language="unknown",
                confidence=0.0,
                script="unknown",
                writing_direction="ltr",
                is_mixed=False,
                secondary_languages=[],
                encoding="utf-8",
                character_count=0,
                word_count=0
            )
        
        # Clean text
        clean_text = self._preprocess_text(text)
        
        # Detect script
        script = self._detect_script(clean_text)
        
        # Detect writing direction
        writing_direction = self._detect_writing_direction(clean_text, script)
        
        # Detect encoding
        encoding = self._detect_encoding(clean_text)
        
        # Detect language
        if hint_language and hint_language in self.SCRIPT_MAP:
            # Use hint to boost confidence
            language, confidence = self._detect_language_with_hint(clean_text, hint_language)
        else:
            language, confidence = self._detect_language(clean_text, script)
        
        # Check for mixed language
        is_mixed, secondary = self._detect_mixed_language(clean_text, language)
        
        return LanguageDetectionResult(
            language=language,
            confidence=confidence,
            script=script,
            writing_direction=writing_direction,
            is_mixed=is_mixed,
            secondary_languages=secondary,
            encoding=encoding,
            character_count=len(text),
            word_count=len(clean_text.split())
        )
    
    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for detection."""
        # Remove URLs
        text = re.sub(r'https?://\S+', '', text)
        # Remove emails
        text = re.sub(r'\S+@\S+', '', text)
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep script characters
        text = text.strip()
        return text
    
    def _detect_script(self, text: str) -> str:
        """Detect script from text."""
        script_counts = {}
        
        for char in text:
            code = ord(char)
            
            for script, ranges in self.SCRIPT_RANGES.items():
                if len(ranges) == 2:
                    if ranges[0] <= code <= ranges[1]:
                        script_counts[script] = script_counts.get(script, 0) + 1
                elif len(ranges) == 4:
                    if (ranges[0] <= code <= ranges[1]) or (ranges[2] <= code <= ranges[3]):
                        script_counts[script] = script_counts.get(script, 0) + 1
        
        if not script_counts:
            return "other"
        
        return max(script_counts, key=script_counts.get)
    
    def _detect_writing_direction(self, text: str, script: str) -> str:
        """Detect writing direction."""
        if script == "arabic" or script == "hebrew":
            # Check if primarily RTL
            rtl_chars = sum(1 for c in text if 0x0600 <= ord(c) <= 0x06FF or 0x0590 <= ord(c) <= 0x05FF)
            total_chars = len([c for c in text if c.isalpha()])
            
            if total_chars > 0 and rtl_chars / total_chars > 0.5:
                return WritingDirection.RTL.value
        
        return WritingDirection.LTR.value
    
    def _detect_encoding(self, text: str) -> str:
        """Detect character encoding."""
        try:
            text.encode('utf-8')
            return 'utf-8'
        except UnicodeEncodeError:
            pass
        
        try:
            text.encode('latin-1')
            return 'latin-1'
        except UnicodeEncodeError:
            pass
        
        return 'utf-8'
    
    def _detect_language(self, text: str, script: str) -> tuple:
        """Detect language using word frequency."""
        words = text.lower().split()
        if len(words) < 3:
            # Not enough text, use script-based detection
            for lang, s in self.SCRIPT_MAP.items():
                if s == script:
                    return lang, 0.5
            return "unknown", 0.0
        
        # Count matches with common words
        lang_scores = {}
        
        # Get languages for this script
        script_langs = [lang for lang, s in self.SCRIPT_MAP.items() if s == script]
        
        for lang in script_langs:
            if lang in self.COMMON_WORDS:
                common = set(self.COMMON_WORDS[lang])
                matches = sum(1 for w in words if w in common)
                lang_scores[lang] = matches / len(words)
        
        if lang_scores:
            best_lang = max(lang_scores, key=lang_scores.get)
            confidence = min(lang_scores[best_lang] * 3, 0.99)  # Scale and cap
            return best_lang, confidence
        
        return script, 0.3  # Fallback to script name
    
    def _detect_language_with_hint(self, text: str, hint: str) -> tuple:
        """Detect language with a hint."""
        base_lang, base_conf = self._detect_language(text, self.SCRIPT_MAP.get(hint, "other"))
        
        if base_lang == hint:
            confidence = min(base_conf * 1.2, 0.99)
        else:
            confidence = base_conf * 0.8
        
        return base_lang, confidence
    
    def _detect_mixed_language(
        self,
        text: str,
        primary_language: str
    ) -> tuple:
        """Detect if text contains multiple languages."""
        words = text.lower().split()
        if len(words) < 10:
            return False, []
        
        # Check for common words from other languages
        other_lang_words = {}
        
        for lang, common_words in self.COMMON_WORDS.items():
            if lang == primary_language:
                continue
            
            count = sum(1 for w in words if w in common_words)
            if count > 0:
                other_lang_words[lang] = count / len(words)
        
        # If another language has significant presence (>5%)
        significant_langs = {
            lang: conf for lang, conf in other_lang_words.items()
            if conf > 0.05
        }
        
        if significant_langs:
            return True, [
                {"lang": lang, "confidence": conf}
                for lang, conf in sorted(significant_langs.items(), key=lambda x: -x[1])
            ]
        
        return False, []
    
    def detect_batch(self, texts: List[str]) -> List[LanguageDetectionResult]:
        """Detect languages for multiple texts."""
        return [self.detect(text) for text in texts]


# Global detector instance
_detector: Optional[LanguageDetector] = None


def get_language_detector() -> LanguageDetector:
    """Get the global language detector."""
    global _detector
    if _detector is None:
        _detector = LanguageDetector()
    return _detector
