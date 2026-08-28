"""
Base Extraction Service

Abstract base class for all knowledge extraction services.
Provides common functionality and interface contracts.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
import time

from src.core.logging import logger


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    confidence_score: Optional[float] = None
    processing_time_ms: Optional[int] = None
    metadata: Optional[Dict] = None


@dataclass
class ExtractionContext:
    """Context passed through the extraction pipeline."""
    document_id: int
    text: str
    language_code: Optional[str] = None
    metadata: Optional[Dict] = None
    progress_callback: Optional[Callable] = None
    
    def emit_progress(self, stage: str, progress: float, message: str):
        """Emit progress update if callback is provided."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)


class BaseExtractionService(ABC):
    """
    Abstract base class for knowledge extraction services.
    
    All extraction services should inherit from this class and implement
    the extract method. This provides:
    - Consistent interface
    - Error handling
    - Performance timing
    - Progress reporting
    """
    
    service_name: str = "base_extraction"
    estimated_time_ms: int = 5000  # Estimated processing time for progress calculation
    
    def __init__(self, llm_provider=None):
        """
        Initialize the extraction service.
        
        Args:
            llm_provider: Optional LLM provider for extraction (for services that need it)
        """
        self.llm_provider = llm_provider
    
    def extract(self, context: ExtractionContext) -> ExtractionResult:
        """
        Extract knowledge from the given context.
        
        Args:
            context: Extraction context containing document information
            
        Returns:
            ExtractionResult with extracted data or error information
        """
        start_time = time.time()
        
        try:
            logger.info(f"[{self.service_name}] Starting extraction for document {context.document_id}")
            
            # Call the actual extraction logic
            data = self._extract(context)
            
            processing_time_ms = int((time.time() - start_time) * 1000)
            
            # Calculate confidence if not set by implementation
            confidence = self._calculate_confidence(data) if data else 0.0
            
            logger.info(
                f"[{self.service_name}] Completed extraction for document {context.document_id} "
                f"in {processing_time_ms}ms"
            )
            
            return ExtractionResult(
                success=True,
                data=data,
                confidence_score=confidence,
                processing_time_ms=processing_time_ms,
                metadata={"service": self.service_name}
            )
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"[{self.service_name}] Extraction failed for document {context.document_id}")
            
            return ExtractionResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time_ms,
                metadata={"service": self.service_name, "error_type": type(e).__name__}
            )
    
    @abstractmethod
    def _extract(self, context: ExtractionContext) -> Any:
        """
        Implement the actual extraction logic.
        
        This method must be implemented by subclasses.
        
        Args:
            context: Extraction context containing document information
            
        Returns:
            Extracted data in the format expected by the service
        """
        pass
    
    def _calculate_confidence(self, data: Any) -> float:
        """
        Calculate confidence score for extraction results.
        
        Override in subclasses for custom confidence calculation.
        
        Args:
            data: Extracted data
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Default implementation: assume moderate confidence if data exists
        if data is None:
            return 0.0
        if isinstance(data, (list, dict)) and len(data) == 0:
            return 0.3
        return 0.7
    
    def validate_input(self, context: ExtractionContext) -> tuple[bool, str]:
        """
        Validate input before extraction.
        
        Args:
            context: Extraction context
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not context.text or len(context.text.strip()) == 0:
            return False, "No text content provided for extraction"
        
        if len(context.text) < 50:
            return False, "Text content too short for meaningful extraction"
        
        return True, ""
    
    def get_estimated_time(self, text_length: int) -> int:
        """
        Estimate processing time based on text length.
        
        Args:
            text_length: Length of text in characters
            
        Returns:
            Estimated time in milliseconds
        """
        # Base time + proportional to text length
        base_time = self.estimated_time_ms
        per_char_time = 0.1  # ms per character
        return int(base_time + (text_length * per_char_time))


class LLMExtractionService(BaseExtractionService):
    """
    Base class for LLM-based extraction services.
    
    Provides common functionality for services that use LLMs
    for knowledge extraction.
    """
    
    def __init__(self, llm_provider=None, model: str = "llama3"):
        """
        Initialize the LLM extraction service.
        
        Args:
            llm_provider: LLM provider instance
            model: Model to use for extraction
        """
        super().__init__(llm_provider)
        self.model = model
        self.estimated_time_ms = 15000  # LLM extraction takes longer
    
    def _get_llm_response(self, prompt: str, system_prompt: str = None) -> str:
        """
        Get response from LLM provider.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLM response text
        """
        if self.llm_provider is None:
            # Return placeholder response for testing
            logger.warning(f"[{self.service_name}] No LLM provider configured, returning mock response")
            return self._get_mock_response(prompt)
        
        try:
            response = self.llm_provider.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt or self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                model=self.model
            )
            return response
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _get_system_prompt(self) -> str:
        """
        Get the system prompt for this extraction service.
        
        Override in subclasses.
        """
        return "You are a helpful AI assistant."
    
    def _get_mock_response(self, prompt: str) -> str:
        """
        Get mock response for testing when no LLM provider is available.
        
        Override in subclasses.
        """
        return "{}"
