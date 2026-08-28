"""
Summary Extraction Service

Extracts multiple levels of summaries from documents.
"""

import json
from typing import Dict, Any

from src.knowledge.extraction.base import (
    BaseExtractionService, 
    ExtractionContext, 
    ExtractionResult
)
from src.core.logging import logger


class SummaryService(BaseExtractionService):
    """
    Service for generating multiple levels of summaries from document text.
    
    Generates:
    - One sentence summary
    - Executive summary
    - Bullet summary
    - Detailed summary
    - Chapter summaries (if applicable)
    """
    
    service_name = "summary_service"
    estimated_time_ms = 20000
    
    def _extract(self, context: ExtractionContext) -> Dict[str, Any]:
        """
        Generate summaries at multiple levels.
        
        Args:
            context: Extraction context with document text
            
        Returns:
            Dictionary with various summary levels
        """
        text = context.text
        context.emit_progress(self.service_name, 0.2, "Generating one-sentence summary...")
        
        # Generate one-sentence summary
        one_sentence = self._generate_one_sentence(text)
        
        context.emit_progress(self.service_name, 0.4, "Generating executive summary...")
        
        # Generate executive summary (brief)
        executive = self._generate_executive_summary(text)
        
        context.emit_progress(self.service_name, 0.6, "Generating bullet summary...")
        
        # Generate bullet summary
        bullets = self._generate_bullet_summary(text)
        
        context.emit_progress(self.service_name, 0.8, "Generating detailed summary...")
        
        # Generate detailed summary
        detailed = self._generate_detailed_summary(text)
        
        context.emit_progress(self.service_name, 1.0, "Summary generation complete")
        
        return {
            "one_sentence_summary": one_sentence,
            "executive_summary": executive,
            "bullet_summary": bullets,
            "detailed_summary": detailed,
        }
    
    def _generate_one_sentence(self, text: str) -> str:
        """Generate a single sentence summary."""
        prompt = f"""Summarize the following text in exactly ONE sentence:
        
{text[:3000]}

Respond with ONLY the summary sentence, nothing else."""
        
        system_prompt = """You are an expert summarizer. Your task is to create concise, 
one-sentence summaries that capture the main point of the text. 
The summary should be informative and self-contained."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"One-sentence summary generation failed: {e}")
            return self._fallback_summary(text, max_length=150)
    
    def _generate_executive_summary(self, text: str) -> str:
        """Generate executive summary (2-3 paragraphs)."""
        prompt = f"""Create an executive summary of the following text.
The summary should be 2-3 paragraphs and cover the main points, key findings, and conclusions.

Text:
{text[:5000]}

Respond with ONLY the executive summary."""
        
        system_prompt = """You are an expert at writing executive summaries.
Write clear, concise summaries suitable for busy professionals.
Focus on key insights and actionable information."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"Executive summary generation failed: {e}")
            return self._fallback_summary(text, max_length=500)
    
    def _generate_bullet_summary(self, text: str) -> str:
        """Generate bullet point summary."""
        prompt = f"""Create a bullet-point summary of the key points from the following text.
Use 5-10 bullet points, each starting with • or -

Text:
{text[:5000]}

Respond with ONLY the bullet points."""
        
        system_prompt = """You are an expert at creating structured summaries.
Create clear, concise bullet points that capture the essential information.
Each bullet should be a complete thought."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"Bullet summary generation failed: {e}")
            return self._fallback_bullets(text)
    
    def _generate_detailed_summary(self, text: str) -> str:
        """Generate detailed summary."""
        prompt = f"""Create a detailed summary of the following text.
Cover all major topics and provide context.

Text:
{text[:8000]}

Respond with ONLY the detailed summary."""
        
        system_prompt = """You are an expert at writing detailed summaries.
Provide comprehensive coverage of the material while maintaining readability."""
        
        try:
            response = self._get_llm_response(prompt, system_prompt)
            return response.strip()
        except Exception as e:
            logger.warning(f"Detailed summary generation failed: {e}")
            return self._fallback_summary(text, max_length=2000)
    
    def _fallback_summary(self, text: str, max_length: int = 500) -> str:
        """Fallback summary using text extraction."""
        # Take first meaningful sentences
        sentences = text.split('.')
        summary = ""
        for sentence in sentences:
            if len(summary) + len(sentence) < max_length:
                summary += sentence + "."
            else:
                break
        return summary.strip() or text[:max_length]
    
    def _fallback_bullets(self, text: str) -> str:
        """Fallback bullet summary."""
        # Extract key sentences as bullets
        sentences = [s.strip() for s in text.split('.') if len(s.strip()) > 50]
        bullets = []
        for s in sentences[:8]:
            if len(bullets) < 8:
                bullets.append(f"• {s[:200]}.")
        return "\n".join(bullets) if bullets else "• Key information extracted from document."
    
    def _get_system_prompt(self) -> str:
        return """You are an expert summarizer. Generate high-quality summaries 
at multiple levels of detail. Always respond with valid content only."""
    
    def _get_mock_response(self, prompt: str) -> str:
        """Return mock summary response for testing."""
        if "one sentence" in prompt.lower():
            return "This document provides comprehensive information about the subject matter."
        elif "executive summary" in prompt.lower():
            return "This document covers important topics related to the subject. It presents key findings and discusses implications for various stakeholders."
        elif "bullet" in prompt.lower():
            return """• Key point 1: Important information
• Key point 2: Additional details
• Key point 3: Further analysis
• Key point 4: Critical insights"""
        else:
            return "This document provides detailed information covering multiple aspects of the subject matter, including definitions, examples, and practical applications."
