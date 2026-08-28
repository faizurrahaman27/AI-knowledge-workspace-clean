"""
Multilingual Generation Service

Preserves language in AI-generated content.
"""

from typing import Optional, List, Dict, Any, Callable
import logging

from src.multilingual.detector import get_language_detector
from src.multilingual.registry import get_language_registry
from src.core.logging import logger

logger = logging.getLogger(__name__)


class MultilingualGenerationService:
    """
    Service for preserving language in AI generation.
    
    Features:
    - Language detection from source
    - Language preservation in generation
    - Response in user's language
    - Mixed-language content handling
    """
    
    def __init__(self, llm_provider: Optional[Callable] = None):
        """
        Initialize the generation service.
        
        Args:
            llm_provider: Optional LLM provider for translation
        """
        self.llm_provider = llm_provider
        self.detector = get_language_detector()
        self.registry = get_language_registry()
    
    def detect_source_language(
        self,
        content: str,
        context_languages: Optional[List[str]] = None
    ) -> str:
        """
        Detect the primary language for generation.
        
        Args:
            content: Source content
            context_languages: Optional context languages
            
        Returns:
            Detected language code
        """
        detection = self.detector.detect(content)
        return detection.language
    
    def preserve_language(
        self,
        content: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Ensure generated content matches source language.
        
        Args:
            content: Generated content
            source_language: Source language to preserve
            
        Returns:
            Content with preserved language
        """
        if not content:
            return content
        
        # If no source language specified, detect from content
        if not source_language:
            source_language = self.detect_source_language(content)
        
        # In production, this would:
        # 1. Check if content language matches source
        # 2. Translate if necessary
        # 3. Apply language-specific formatting
        
        return content
    
    def generate_in_language(
        self,
        prompt: str,
        target_language: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate content in specific language.
        
        Args:
            prompt: Generation prompt
            target_language: Target language code
            system_prompt: Optional system prompt
            context: Optional context
            
        Returns:
            Generated content in target language
        """
        # Get language info
        lang_info = self.registry.get(target_language)
        if not lang_info:
            logger.warning(f"Unknown language: {target_language}, falling back to English")
            target_language = "en"
            lang_info = self.registry.get("en")
        
        # Build language-specific prompt
        enhanced_prompt = self._enhance_prompt_for_language(
            prompt=prompt,
            target_language=target_language,
            lang_info=lang_info
        )
        
        # Generate with LLM
        if self.llm_provider:
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt or f"Respond in {lang_info.native_name}."},
                    {"role": "user", "content": enhanced_prompt}
                ]
            )
            return response
        else:
            # Fallback - just return the prompt
            return prompt
    
    def _enhance_prompt_for_language(
        self,
        prompt: str,
        target_language: str,
        lang_info: Any
    ) -> str:
        """Enhance prompt for specific language."""
        # Add language instruction based on script type
        instructions = {
            "arabic": "\n\nPlease respond in Arabic (العربية).",
            "cjk": "\n\nPlease respond in the appropriate Chinese/Japanese/Korean script.",
            "devanagari": "\n\nPlease respond in Hindi/Devanagari script.",
            "cyrillic": "\n\nPlease respond in Russian/Cyrillic script.",
            "latin": "\n\nPlease respond in the specified language."
        }
        
        instruction = instructions.get(lang_info.script_type, "")
        
        # Add RTL instruction for RTL languages
        if lang_info.writing_direction.value == "rtl":
            instruction += " Note: This is a right-to-left language."
        
        return f"{prompt}{instruction}"
    
    def generate_flashcards(
        self,
        content: str,
        source_language: Optional[str] = None,
        count: int = 5
    ) -> List[Dict[str, str]]:
        """
        Generate flashcards preserving language.
        
        Args:
            content: Source content
            source_language: Source language
            count: Number of flashcards
            
        Returns:
            List of flashcards {front, back} in source language
        """
        if not source_language:
            source_language = self.detect_source_language(content)
        
        lang_info = self.registry.get(source_language)
        lang_name = lang_info.native_name if lang_info else "English"
        
        # Generate flashcards using LLM
        if self.llm_provider:
            prompt = f"""Generate {count} flashcards from the following content.
            Respond ONLY in {lang_name}.
            
            Content: {content[:2000]}
            
            Return as JSON array: [{{"front": "question", "back": "answer"}}, ...]"""
            
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": f"You generate flashcards in {lang_name}."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse and return
            try:
                import json
                return json.loads(response)
            except:
                return []
        
        return []
    
    def generate_summary(
        self,
        content: str,
        source_language: Optional[str] = None,
        length: str = "medium"
    ) -> str:
        """
        Generate summary preserving language.
        
        Args:
            content: Source content
            source_language: Source language
            length: Summary length (short, medium, long)
            
        Returns:
            Summary in source language
        """
        if not source_language:
            source_language = self.detect_source_language(content)
        
        lang_info = self.registry.get(source_language)
        lang_name = lang_info.native_name if lang_info else "English"
        
        length_instructions = {
            "short": "2-3 sentences",
            "medium": "1 paragraph",
            "long": "2-3 paragraphs"
        }
        
        if self.llm_provider:
            prompt = f"""Summarize the following content in {lang_name}.
            Length: {length_instructions.get(length, 'medium')}
            
            Content: {content[:5000]}"""
            
            return self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": f"You summarize texts in {lang_name}."},
                    {"role": "user", "content": prompt}
                ]
            )
        
        return content[:500]
    
    def generate_questions(
        self,
        content: str,
        source_language: Optional[str] = None,
        question_type: str = "multiple_choice",
        count: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate questions preserving language.
        
        Args:
            content: Source content
            source_language: Source language
            question_type: Type of questions
            count: Number of questions
            
        Returns:
            List of questions in source language
        """
        if not source_language:
            source_language = self.detect_source_language(content)
        
        lang_info = self.registry.get(source_language)
        lang_name = lang_info.native_name if lang_info else "English"
        
        if self.llm_provider:
            prompt = f"""Generate {count} {question_type} questions from the content.
            Respond ONLY in {lang_name}.
            
            Content: {content[:3000]}"""
            
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": f"You generate questions in {lang_name}."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            try:
                import json
                return json.loads(response)
            except:
                return []
        
        return []
    
    def translate_content(
        self,
        content: str,
        source_language: str,
        target_language: str
    ) -> str:
        """
        Translate content between languages.
        
        Args:
            content: Content to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Translated content
        """
        if source_language == target_language:
            return content
        
        if self.llm_provider:
            source_info = self.registry.get(source_language)
            target_info = self.registry.get(target_language)
            
            prompt = f"""Translate the following text from {source_info.native_name if source_info else source_language} to {target_info.native_name if target_info else target_language}.
            
            Text: {content}"""
            
            return self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": f"You translate texts accurately."},
                    {"role": "user", "content": prompt}
                ]
            )
        
        return content


# Global service instance
_generation_service: Optional[MultilingualGenerationService] = None


def get_multilingual_generation_service(
    llm_provider: Optional[Callable] = None
) -> MultilingualGenerationService:
    """Get multilingual generation service."""
    global _generation_service
    if _generation_service is None:
        _generation_service = MultilingualGenerationService(llm_provider)
    return _generation_service
