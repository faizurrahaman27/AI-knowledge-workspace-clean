"""
Base Validation Service

Abstract base class for all knowledge validation services.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import time

from src.core.logging import logger


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    success: bool
    passed: bool
    message: Optional[str] = None
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    remediation_action: Optional[str] = None
    processing_time_ms: Optional[int] = None


@dataclass
class ValidationContext:
    """Context for validation operations."""
    document_id: int
    knowledge_type: str  # entity, concept, relationship, etc.
    knowledge_id: Optional[int] = None
    text: str = ""
    source_document_id: Optional[int] = None
    progress_callback: Optional[Callable] = None
    
    def emit_progress(self, stage: str, progress: float, message: str):
        """Emit progress update."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)


@dataclass
class ValidationReport:
    """Complete validation report for a document."""
    document_id: int
    is_valid: bool
    overall_score: float
    validation_results: List[ValidationResult]
    warnings: List[str]
    errors: List[str]
    citations_added: int
    duplicates_removed: int
    entities_merged: int
    quality_score: Optional[float] = None
    confidence_score: Optional[float] = None
    processing_time_ms: int = 0


class BaseValidationService(ABC):
    """
    Abstract base class for knowledge validation services.
    
    All validation services should inherit from this class and implement
    the validate method.
    """
    
    service_name: str = "base_validation"
    estimated_time_ms: int = 1000
    
    def __init__(self):
        """Initialize the validation service."""
        pass
    
    def validate(self, context: ValidationContext) -> ValidationResult:
        """
        Validate knowledge according to service rules.
        
        Args:
            context: Validation context
            
        Returns:
            ValidationResult with validation outcome
        """
        start_time = time.time()
        
        try:
            logger.info(f"[{self.service_name}] Starting validation for {context.knowledge_type}")
            
            # Call the actual validation logic
            result = self._validate(context)
            
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                f"[{self.service_name}] Validation completed in {result.processing_time_ms}ms: "
                f"{'PASSED' if result.passed else 'FAILED'}"
            )
            
            return result
            
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"[{self.service_name}] Validation failed")
            
            return ValidationResult(
                success=False,
                passed=False,
                message=f"Validation error: {str(e)}",
                error_code="VALIDATION_ERROR",
                processing_time_ms=processing_time_ms
            )
    
    @abstractmethod
    def _validate(self, context: ValidationContext) -> ValidationResult:
        """
        Implement the actual validation logic.
        
        This method must be implemented by subclasses.
        """
        pass
    
    def get_service_name(self) -> str:
        """Get the service name."""
        return self.service_name
    
    def get_estimated_time(self) -> int:
        """Get estimated processing time."""
        return self.estimated_time_ms
