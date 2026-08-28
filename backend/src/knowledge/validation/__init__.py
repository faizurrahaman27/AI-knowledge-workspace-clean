"""
Knowledge Validation Module

Services for validating, quality-assuring, and auditing extracted knowledge.
"""

from src.knowledge.validation.base import BaseValidationService
from src.knowledge.validation.citation_service import CitationMappingService
from src.knowledge.validation.confidence_service import ConfidenceScoringService
from src.knowledge.validation.entity_resolver import EntityResolutionService
from src.knowledge.validation.duplicate_detector import DuplicateDetectionService
from src.knowledge.validation.canonicalizer import CanonicalizationService
from src.knowledge.validation.consistency_service import ConsistencyValidationService
from src.knowledge.validation.quality_service import QualityScoringService
from src.knowledge.validation.version_service import KnowledgeVersionService
from src.knowledge.validation.audit_service import AuditService

__all__ = [
    "BaseValidationService",
    "CitationMappingService",
    "ConfidenceScoringService",
    "EntityResolutionService",
    "DuplicateDetectionService",
    "CanonicalizationService",
    "ConsistencyValidationService",
    "QualityScoringService",
    "KnowledgeVersionService",
    "AuditService",
]
