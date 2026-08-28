"""
RTL Renderer

Handles right-to-left text rendering and formatting.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class RTLConfig:
    """RTL rendering configuration."""
    enabled: bool
    base_direction: str = "rtl"
    paragraph_direction: str = "rtl"
    text_align: str = "right"
    content_flow: str = "rtl"


class RTLRenderer:
    """
    RTL (Right-to-Left) text renderer.
    
    Handles:
    - Direction detection
    - RTL/LTR embedding
    - Bidirectional text
    - Export formatting
    """
    
    # RTL language codes
    RTL_LANGUAGES = {"ar", "he", "fa", "ur", "ps", "yi", "sd", "ckb"}
    
    def __init__(self):
        """Initialize the RTL renderer."""
        pass
    
    def is_rtl_language(self, language_code: str) -> bool:
        """Check if language is RTL."""
        return language_code in self.RTL_LANGUAGES
    
    def get_config(self, language_code: str) -> RTLConfig:
        """
        Get RTL configuration for language.
        
        Args:
            language_code: Language code
            
        Returns:
            RTLConfig with rendering settings
        """
        is_rtl = self.is_rtl_language(language_code)
        
        return RTLConfig(
            enabled=is_rtl,
            base_direction="rtl" if is_rtl else "ltr",
            paragraph_direction="rtl" if is_rtl else "ltr",
            text_align="right" if is_rtl else "left",
            content_flow="rtl" if is_rtl else "ltr"
        )
    
    def wrap_html(self, content: str, language_code: str) -> str:
        """
        Wrap content in HTML with RTL attributes.
        
        Args:
            content: HTML content
            language_code: Language code
            
        Returns:
            HTML with RTL attributes
        """
        config = self.get_config(language_code)
        
        if not config.enabled:
            return content
        
        return f'<html dir="{config.base_direction}" lang="{language_code}">\n{content}\n</html>'
    
    def wrap_markdown(self, content: str, language_code: str) -> str:
        """
        Wrap markdown content with RTL hints.
        
        Args:
            content: Markdown content
            language_code: Language code
            
        Returns:
            Markdown with RTL metadata
        """
        config = self.get_config(language_code)
        
        if not config.enabled:
            return content
        
        # Add metadata comment
        header = f'<!-- RTL: true | Direction: {config.base_direction} | Language: {language_code} -->\n\n'
        
        return header + content
    
    def format_pdf_metadata(
        self,
        language_code: str,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get PDF metadata for RTL.
        
        Args:
            language_code: Language code
            title: Document title
            
        Returns:
            PDF metadata dict
        """
        config = self.get_config(language_code)
        
        return {
            "Language": language_code,
            "Direction": config.base_direction,
            "TextAlign": config.text_align,
            "Creator": "AI Knowledge Workspace",
            "Title": title
        }
    
    def normalize_bidi(self, text: str) -> str:
        """
        Normalize bidirectional text.
        
        Handles mixed LTR/RTL content properly.
        
        Args:
            text: Text with potential mixed directions
            
        Returns:
            Normalized text with proper Unicode marks
        """
        # Add Unicode bidirectional marks
        # Right-to-Left Mark (RLM): U+200F
        # Left-to-Right Mark (LRM): U+200E
        # Pop Directional Formatting (PDF): U+202C
        # Right-to-Left Embedding (RLE): U+202B
        # Left-to-Right Embedding (LRE): U+202A
        
        result = []
        
        for char in text:
            code = ord(char)
            
            # Check if character is strong RTL
            if 0x0590 <= code <= 0x05FF:  # Hebrew
                result.append('\u202B')  # RLE
                result.append(char)
                result.append('\u202C')  # PDF
            elif 0x0600 <= code <= 0x06FF:  # Arabic
                result.append('\u202B')  # RLE
                result.append(char)
                result.append('\u202C')  # PDF
            else:
                result.append(char)
        
        return ''.join(result)
    
    def get_css(self, language_code: str) -> str:
        """
        Get CSS for RTL rendering.
        
        Args:
            language_code: Language code
            
        Returns:
            CSS styles string
        """
        config = self.get_config(language_code)
        
        if not config.enabled:
            return ""
        
        return f"""
/* RTL Styles for {language_code} */
[dir="rtl"] {{
    direction: {config.base_direction};
    text-align: {config.text_align};
}}

[dir="rtl"] body {{
    font-family: 'Noto Sans Arabic', 'Segoe UI', sans-serif;
}}

[dir="rtl"] .content-flow {{
    flex-direction: row-reverse;
}}

[dir="rtl"] .sidebar {{
    border-right: none;
    border-left: 1px solid #ddd;
}}

[dir="rtl"] .icon {{
    margin-right: 0;
    margin-left: 8px;
}}

[dir="rtl"] .navigation {{
    padding-left: 0;
    padding-right: 20px;
}}

[dir="rtl"] blockquote {{
    border-left: none;
    border-right: 4px solid #ccc;
    padding-right: 16px;
    padding-left: 0;
}}
"""
    
    def format_for_export(
        self,
        content: str,
        language_code: str,
        format: str = "markdown"
    ) -> str:
        """
        Format content for export based on language.
        
        Args:
            content: Content to format
            language_code: Language code
            format: Export format (markdown, html, pdf)
            
        Returns:
            Formatted content
        """
        config = self.get_config(language_code)
        
        if format == "markdown":
            return self.wrap_markdown(content, language_code)
        elif format == "html":
            return self.wrap_html(content, language_code)
        elif format == "pdf":
            # Return content with metadata
            return content
        else:
            return content


# Global renderer instance
_renderer: Optional[RTLRenderer] = None


def get_rtl_renderer() -> RTLRenderer:
    """Get the global RTL renderer."""
    global _renderer
    if _renderer is None:
        _renderer = RTLRenderer()
    return _renderer
