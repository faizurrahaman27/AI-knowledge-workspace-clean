"""
Unicode Normalizer

Normalizes text from different Unicode representations.
"""

import unicodedata
import re
from typing import Dict, Optional


class UnicodeNormalizer:
    """
    Unicode normalizer for multilingual text.
    
    Normalizes:
    - Arabic text
    - Indic scripts
    - CJK characters
    - Unicode composed/decomposed forms
    - Zero-width characters
    - Whitespace
    """
    
    # Arabic normalization maps
    ARABIC_NORMALIZATION: Dict[str, str] = {
        'ى': 'ي',  # Alef Maksura to Yeh
        'ە': 'ه',  # Kurdish Heh to normal Heh
        'ێ': 'ی',  # Kurdish Yeh to Arabic Yeh
        'ھ': 'ه',  # Kurdish Heh with dot above
        'ۆ': 'و',  # Kurdish Waw to Arabic Waw
        'ک': 'ك',  # Kurdish Kaf to Arabic Kaf
        'ی': 'ي',  # Persian Yeh to Arabic Yeh
    }
    
    # Zero-width characters to remove
    ZERO_WIDTH_CHARS = [
        '\u200B',  # Zero Width Space
        '\u200C',  # Zero Width Non-Joiner
        '\u200D',  # Zero Width Joiner
        '\u200E',  # Left-to-Right Mark
        '\u200F',  # Right-to-Left Mark
        '\uFEFF',  # Byte Order Mark
        '\u00AD',  # Soft Hyphen
        '\u180B',  # Mongolian Free Variation Selector 1
        '\u180C',  # Mongolian Free Variation Selector 2
        '\u180D',  # Mongolian Free Variation Selector 3
        '\u180E',  # Mongolian Vowel Separator (deprecated)
        '\u200A',  # Hair Space
        '\u2028',  # Line Separator
        '\u2029',  # Paragraph Separator
        '\u202F',  # Narrow No-Break Space
        '\u205F',  # Medium Mathematical Space
        '\u2060',  # Word Joiner
        '\u3000',  # Ideographic Space (normalizable)
    ]
    
    # Normalization form
    DEFAULT_NORMALIZATION = 'NFC'  # Canonical Decomposition, then Canonical Composition
    
    def __init__(self, normalization_form: str = 'NFC'):
        """
        Initialize the normalizer.
        
        Args:
            normalization_form: Unicode normalization form (NFC, NFD, NFKC, NFKD)
        """
        self.normalization_form = normalization_form
    
    def normalize(self, text: str, language: Optional[str] = None) -> str:
        """
        Normalize text.
        
        Args:
            text: Input text
            language: Optional language hint for specialized normalization
            
        Returns:
            Normalized text
        """
        if not text:
            return text
        
        # Step 1: Remove zero-width characters
        text = self._remove_zero_width_chars(text)
        
        # Step 2: Unicode normalization
        text = unicodedata.normalize(self.normalization_form, text)
        
        # Step 3: Language-specific normalization
        if language:
            if language in ['ar', 'fa', 'ur', 'ps']:
                text = self._normalize_arabic(text)
            elif language in ['hi', 'mr', 'ne', 'sa']:
                text = self._normalize_indic(text)
            elif language in ['zh', 'ja', 'ko']:
                text = self._normalize_cjk(text)
        
        # Step 4: Whitespace normalization
        text = self._normalize_whitespace(text)
        
        return text
    
    def _remove_zero_width_chars(self, text: str) -> str:
        """Remove zero-width and control characters."""
        for char in self.ZERO_WIDTH_CHARS:
            text = text.replace(char, '')
        
        # Remove other control characters except newlines and tabs
        text = ''.join(char for char in text if not (0x0000 <= ord(char) <= 0x001F and char not in '\t\n'))
        
        return text
    
    def _normalize_arabic(self, text: str) -> str:
        """Normalize Arabic text."""
        # Apply Arabic normalization map
        for old, new in self.ARABIC_NORMALIZATION.items():
            text = text.replace(old, new)
        
        # Remove Arabic diacritics (tashkeel) optionally
        # tashkeel_range = range(0x0610, 0x061A) + range(0x064B, 0x065F) + range(0x0670, 0x0670)
        # text = ''.join(c for c in text if ord(c) not in tashkeel_range)
        
        return text
    
    def _normalize_indic(self, text: str) -> str:
        """Normalize Indic scripts."""
        # Remove virama (halant) for half-forms if needed
        # Normalize nukta
        text = text.replace('\u093C', '')  # Nukta
        
        return text
    
    def _normalize_cjk(self, text: str) -> str:
        """Normalize CJK text."""
        # Normalize full-width to half-width for ASCII-like characters
        # This helps with some OCR outputs
        result = []
        for char in text:
            code = ord(char)
            # Full-width ASCII range (FF01-FF5E) -> ASCII (0021-007E)
            if 0xFF01 <= code <= 0xFF5E:
                result.append(chr(code - 0xFEE0))
            else:
                result.append(char)
        
        return ''.join(result)
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Trim leading/trailing whitespace per line
        lines = [line.strip() for line in text.split('\n')]
        
        return '\n'.join(lines)
    
    def normalize_batch(self, texts: list, language: Optional[str] = None) -> list:
        """Normalize multiple texts."""
        return [self.normalize(text, language) for text in texts]
    
    def get_text_stats(self, text: str) -> Dict:
        """Get statistics about text normalization."""
        original_length = len(text)
        
        # Count zero-width characters
        zero_width_count = sum(1 for char in text if char in self.ZERO_WIDTH_CHARS)
        
        # Normalize
        normalized = self.normalize(text)
        normalized_length = len(normalized)
        
        return {
            "original_length": original_length,
            "normalized_length": normalized_length,
            "zero_width_removed": zero_width_count,
            "characters_removed": original_length - normalized_length,
            "compression_ratio": normalized_length / original_length if original_length > 0 else 1.0
        }


# Global normalizer instance
_normalizer: Optional[UnicodeNormalizer] = None


def get_unicode_normalizer() -> UnicodeNormalizer:
    """Get the global Unicode normalizer."""
    global _normalizer
    if _normalizer is None:
        _normalizer = UnicodeNormalizer()
    return _normalizer
