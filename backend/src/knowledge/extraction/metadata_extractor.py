"""
Metadata Extraction Service

Extracts general metadata and metrics from documents.
"""

import re
from typing import Dict, Any
from datetime import datetime

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.core.logging import logger


class MetadataExtractionService(BaseExtractionService):
    """
    Service for extracting general metadata from documents.
    
    Extracts:
    - Reading time
    - Difficulty estimate
    - Document statistics
    - Language info
    """
    
    service_name = "metadata_extraction"
    estimated_time_ms = 3000
    
    # Average reading speed (words per minute)
    WORDS_PER_MINUTE = 200
    
    def _extract(self, context: ExtractionContext) -> Dict[str, Any]:
        """
        Extract metadata from document.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            Dictionary with metadata
        """
        text = context.text
        
        context.emit_progress(self.service_name, 0.3, "Analyzing document metadata...")
        
        # Calculate basic statistics
        word_count = self._count_words(text)
        sentence_count = self._count_sentences(text)
        paragraph_count = self._count_paragraphs(text)
        
        # Calculate reading time
        reading_time_minutes = word_count / self.WORDS_PER_MINUTE
        
        # Estimate difficulty based on text characteristics
        difficulty_score = self._estimate_difficulty(text)
        
        # Detect document category (simple heuristic)
        document_category = self._detect_category(text)
        
        # Estimate academic subject
        academic_subject = self._detect_academic_subject(text)
        
        metadata = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "paragraph_count": paragraph_count,
            "reading_time_minutes": round(reading_time_minutes, 1),
            "difficulty_score": difficulty_score,
            "document_category": document_category,
            "academic_subject": academic_subject,
            "language": context.language_code or "en",
            "language_name": self._get_language_name(context.language_code),
        }
        
        context.emit_progress(
            self.service_name, 1.0,
            f"Extracted metadata: {word_count} words, {reading_time_minutes:.0f} min read"
        )
        
        return metadata
    
    def _count_words(self, text: str) -> int:
        """Count words in text."""
        words = re.findall(r'\b\w+\b', text)
        return len(words)
    
    def _count_sentences(self, text: str) -> int:
        """Count sentences in text."""
        sentences = re.split(r'[.!?]+', text)
        return len([s for s in sentences if s.strip()])
    
    def _count_paragraphs(self, text: str) -> int:
        """Count paragraphs in text."""
        paragraphs = text.split('\n\n')
        return len([p for p in paragraphs if p.strip()])
    
    def _estimate_difficulty(self, text: str) -> float:
        """
        Estimate document difficulty based on text characteristics.
        
        Factors:
        - Average word length (longer words = harder)
        - Sentence length
        - Presence of technical terms
        """
        words = re.findall(r'\b\w+\b', text)
        
        if not words:
            return 0.5
        
        # Calculate average word length
        avg_word_length = sum(len(w) for w in words) / len(words)
        
        # Calculate average sentence length
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        avg_sentence_length = len(words) / max(len(sentences), 1)
        
        # Technical term indicators
        technical_indicators = [
            'algorithm', 'theorem', 'proof', 'equation', 'hypothesis',
            'methodology', 'framework', 'architecture', 'implementation',
            'optimization', 'convergence', 'gradient', 'derivative'
        ]
        technical_count = sum(1 for w in words if w.lower() in technical_indicators)
        technical_ratio = technical_count / len(words)
        
        # Calculate difficulty score (0.0 to 1.0)
        difficulty = 0.3  # Base difficulty
        
        # Add difficulty based on word length
        if avg_word_length > 8:
            difficulty += 0.2
        elif avg_word_length > 6:
            difficulty += 0.1
        
        # Add difficulty based on sentence length
        if avg_sentence_length > 25:
            difficulty += 0.2
        elif avg_sentence_length > 15:
            difficulty += 0.1
        
        # Add difficulty based on technical content
        difficulty += min(technical_ratio * 2, 0.3)
        
        return min(max(difficulty, 0.1), 1.0)
    
    def _detect_category(self, text: str) -> str:
        """Detect document category based on content."""
        text_lower = text.lower()
        
        categories = {
            "technical": ["algorithm", "code", "programming", "software", "system", "api", "database"],
            "academic": ["research", "study", "paper", "analysis", "results", "method", "conclusion"],
            "business": ["company", "market", "revenue", "customer", "strategy", "business", "sales"],
            "news": ["reported", "announced", "today", "yesterday", "according to", "sources"],
            "tutorial": ["learn", "step", "how to", "guide", "example", "tutorial", "introduction"],
        }
        
        max_score = 0
        detected_category = "general"
        
        for category, keywords in categories.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected_category = category
        
        return detected_category
    
    def _detect_academic_subject(self, text: str) -> str:
        """Detect academic subject based on content."""
        text_lower = text.lower()
        
        subjects = {
            "Computer Science": ["machine learning", "algorithm", "software", "programming", "neural network", "data structure"],
            "Mathematics": ["equation", "theorem", "proof", "calculus", "algebra", "geometry", "statistics"],
            "Physics": ["force", "energy", "motion", "quantum", "relativity", "particle", "wave"],
            "Biology": ["cell", "organism", "gene", "evolution", "protein", "ecology", "species"],
            "Chemistry": ["molecule", "reaction", "bond", "element", "compound", "atomic", "periodic"],
            "Economics": ["market", "price", "demand", "supply", "gdp", "inflation", "economic"],
            "Psychology": ["behavior", "cognition", "memory", "neuroscience", "therapy", "mental"],
            "Engineering": ["design", "circuit", "voltage", "signal", "system", "mechanical", "electrical"],
        }
        
        max_score = 0
        detected_subject = "General"
        
        for subject, keywords in subjects.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > max_score:
                max_score = score
                detected_subject = subject
        
        return detected_subject if max_score >= 2 else "General"
    
    def _get_language_name(self, code: str) -> str:
        """Get language name from ISO code."""
        languages = {
            "en": "English", "es": "Spanish", "fr": "French", "de": "German",
            "it": "Italian", "pt": "Portuguese", "ru": "Russian", "zh": "Chinese",
            "ja": "Japanese", "ko": "Korean", "ar": "Arabic", "hi": "Hindi",
            "nl": "Dutch", "pl": "Polish", "tr": "Turkish", "vi": "Vietnamese",
        }
        return languages.get(code, "Unknown")
    
    def _get_system_prompt(self) -> str:
        return ""  # This service doesn't use LLM
    
    def _get_mock_response(self, prompt: str) -> str:
        return "{}"  # Not used
