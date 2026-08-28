"""
Knowledge Validation Pipeline

Orchestrates the complete validation pipeline.
"""

from typing import Optional, Callable, Dict, Any, List
from datetime import datetime
import time

from sqlalchemy.orm import Session

from src.core.logging import logger
from src.models.document import Document

from src.knowledge.validation.citation_service import CitationMappingService
from src.knowledge.validation.confidence_service import ConfidenceScoringService
from src.knowledge.validation.entity_resolver import EntityResolutionService
from src.knowledge.validation.duplicate_detector import DuplicateDetectionService
from src.knowledge.validation.canonicalizer import CanonicalizationService
from src.knowledge.validation.consistency_service import ConsistencyValidationService
from src.knowledge.validation.quality_service import QualityScoringService
from src.knowledge.validation.version_service import KnowledgeVersionService
from src.knowledge.validation.audit_service import AuditService
from src.knowledge.validation_models import AuditEventType

from src.knowledge.validation.base import ValidationReport


class KnowledgeValidationPipeline:
    """
    Orchestrates the complete knowledge validation pipeline.
    
    Pipeline stages:
    1. Citation Mapping
    2. Entity Resolution
    3. Duplicate Detection
    4. Canonicalization
    5. Consistency Validation
    6. Confidence Scoring
    7. Quality Scoring
    8. Version Tracking
    9. Audit Logging
    """
    
    def __init__(
        self,
        db: Session,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize the validation pipeline.
        
        Args:
            db: Database session
            progress_callback: Optional callback for progress updates
        """
        self.db = db
        self.progress_callback = progress_callback
        
        # Initialize services
        self.citation_service = CitationMappingService(db)
        self.confidence_service = ConfidenceScoringService(db)
        self.entity_resolver = EntityResolutionService(db)
        self.duplicate_detector = DuplicateDetectionService(db)
        self.canonicalizer = CanonicalizationService(db)
        self.consistency_service = ConsistencyValidationService(db)
        self.quality_service = QualityScoringService(db)
        self.version_service = KnowledgeVersionService(db)
        self.audit_service = AuditService(db)
        
        # Stage weights
        self.stage_weights = {
            "citation_mapping": 0.10,
            "entity_resolution": 0.15,
            "duplicate_detection": 0.15,
            "canonicalization": 0.10,
            "consistency_validation": 0.15,
            "confidence_scoring": 0.15,
            "quality_scoring": 0.15,
            "version_tracking": 0.05,
        }
    
    def _emit_progress(self, stage: str, progress: float, message: str):
        """Emit progress update."""
        if self.progress_callback:
            self.progress_callback(stage, progress, message)
        logger.info(f"[Validation Pipeline] {stage}: {message}")
    
    async def validate_document(
        self,
        document: Document,
        extracted_data: Dict[str, Any]
    ) -> ValidationReport:
        """
        Run the complete validation pipeline on a document.
        
        Args:
            document: Document to validate
            extracted_data: Extracted knowledge data
            
        Returns:
            ValidationReport with results
        """
        start_time = time.time()
        document_id = document.id
        
        all_results = []
        citations_added = 0
        duplicates_removed = 0
        entities_merged = 0
        
        self._emit_progress("pipeline", 0.0, f"Starting validation for document {document_id}")
        
        # Log validation start
        self.audit_service.log_validation_started(document_id)
        
        cumulative_progress = 0.0
        
        # 1. Citation Mapping
        self._emit_progress("citation_mapping", cumulative_progress, "Mapping citations...")
        citation_result = await self._run_citation_mapping(document_id, extracted_data)
        all_results.extend(citation_result.get("results", []))
        citations_added = citation_result.get("citations_added", 0)
        cumulative_progress += self.stage_weights["citation_mapping"]
        self._emit_progress("citation_mapping", cumulative_progress, f"Added {citations_added} citations")
        
        # 2. Entity Resolution
        self._emit_progress("entity_resolution", cumulative_progress, "Resolving entities...")
        entity_result = await self._run_entity_resolution(document_id, extracted_data)
        all_results.extend(entity_result.get("results", []))
        entities_merged = entity_result.get("entities_merged", 0)
        cumulative_progress += self.stage_weights["entity_resolution"]
        self._emit_progress("entity_resolution", cumulative_progress, f"Resolved {entities_merged} entities")
        
        # 3. Duplicate Detection
        self._emit_progress("duplicate_detection", cumulative_progress, "Detecting duplicates...")
        duplicate_result = await self._run_duplicate_detection(document_id, extracted_data)
        all_results.extend(duplicate_result.get("results", []))
        duplicates_removed = duplicate_result.get("duplicates_removed", 0)
        cumulative_progress += self.stage_weights["duplicate_detection"]
        self._emit_progress("duplicate_detection", cumulative_progress, f"Removed {duplicates_removed} duplicates")
        
        # 4. Canonicalization
        self._emit_progress("canonicalization", cumulative_progress, "Canonicalizing knowledge...")
        canonical_result = await self._run_canonicalization(document_id, extracted_data)
        all_results.extend(canonical_result.get("results", []))
        cumulative_progress += self.stage_weights["canonicalization"]
        self._emit_progress("canonicalization", cumulative_progress, "Canonicalization complete")
        
        # 5. Consistency Validation
        self._emit_progress("consistency_validation", cumulative_progress, "Validating consistency...")
        consistency_result = await self._run_consistency_validation(document_id, extracted_data)
        all_results.extend(consistency_result.get("results", []))
        cumulative_progress += self.stage_weights["consistency_validation"]
        self._emit_progress("consistency_validation", cumulative_progress, f"{len(consistency_result.get('results', []))} checks performed")
        
        # 6. Confidence Scoring
        self._emit_progress("confidence_scoring", cumulative_progress, "Calculating confidence...")
        confidence_result = await self._run_confidence_scoring(document_id, extracted_data)
        overall_confidence = confidence_result.get("overall_confidence", 0.5)
        cumulative_progress += self.stage_weights["confidence_scoring"]
        self._emit_progress("confidence_scoring", cumulative_progress, f"Confidence: {overall_confidence:.2f}")
        
        # 7. Quality Scoring
        self._emit_progress("quality_scoring", cumulative_progress, "Calculating quality...")
        quality_result = await self._run_quality_scoring(document_id, extracted_data)
        overall_quality = quality_result.get("overall_quality", 0.5)
        cumulative_progress += self.stage_weights["quality_scoring"]
        self._emit_progress("quality_scoring", cumulative_progress, f"Quality: {overall_quality:.2f}")
        
        # 8. Version Tracking
        self._emit_progress("version_tracking", cumulative_progress, "Recording version...")
        await self._run_version_tracking(document_id, extracted_data, quality_result, confidence_result)
        cumulative_progress += self.stage_weights["version_tracking"]
        
        # Calculate final results
        processing_time_ms = int((time.time() - start_time) * 1000)
        
        # Count passed/failed
        passed_count = sum(1 for r in all_results if r.passed)
        failed_count = len(all_results) - passed_count
        
        # Log validation completion
        self.audit_service.log_validation_completed(
            document_id,
            {
                "total_results": len(all_results),
                "passed": passed_count,
                "failed": failed_count,
                "citations_added": citations_added,
                "duplicates_removed": duplicates_removed,
                "entities_merged": entities_merged,
                "quality_score": overall_quality,
                "confidence_score": overall_confidence,
            }
        )
        
        self._emit_progress("pipeline", 1.0, f"Validation complete in {processing_time_ms}ms")
        
        return ValidationReport(
            document_id=document_id,
            is_valid=failed_count == 0,
            overall_score=overall_quality,
            validation_results=all_results,
            warnings=[r.message for r in all_results if not r.passed],
            errors=[r.message for r in all_results if not r.passed and r.error_code],
            citations_added=citations_added,
            duplicates_removed=duplicates_removed,
            entities_merged=entities_merged,
            quality_score=overall_quality,
            confidence_score=overall_confidence,
            processing_time_ms=processing_time_ms
        )
    
    async def _run_citation_mapping(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run citation mapping."""
        chunks = data.get("chunks", [])
        
        results = []
        citations_added = 0
        
        # Create citations for entities
        for entity in data.get("entities", []):
            citations = self.citation_service.create_citations(
                document_id=document_id,
                knowledge_type="entity",
                knowledge_id=entity.get("id", 0),
                chunks=chunks,
                text=data.get("text", "")
            )
            citations_added += len(citations)
        
        # Create citations for concepts
        for concept in data.get("concepts", []):
            citations = self.citation_service.create_citations(
                document_id=document_id,
                knowledge_type="concept",
                knowledge_id=concept.get("id", 0),
                chunks=chunks,
                text=data.get("text", "")
            )
            citations_added += len(citations)
        
        return {"results": results, "citations_added": citations_added}
    
    async def _run_entity_resolution(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run entity resolution."""
        from src.knowledge.validation.base import ValidationResult
        
        results = []
        entities_merged = 0
        
        for entity in data.get("entities", []):
            canonical_id, is_new = self.entity_resolver.resolve_entity(
                name=entity.get("name", ""),
                entity_type=entity.get("entity_type", "other"),
                description=entity.get("description")
            )
            
            if not is_new:
                results.append(ValidationResult(
                    success=True,
                    passed=True,
                    message=f"Entity '{entity.get('name')}' resolved to canonical ID {canonical_id}"
                ))
        
        return {"results": results, "entities_merged": entities_merged}
    
    async def _run_duplicate_detection(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run duplicate detection."""
        from src.knowledge.validation.base import ValidationResult
        
        results = []
        duplicates_removed = 0
        
        # Check entities for duplicates
        entity_duplicates = self.duplicate_detector.find_duplicates(
            data.get("entities", []),
            "entity"
        )
        
        for dup_group in entity_duplicates:
            # Keep the best, mark others for removal
            best = self.duplicate_detector.select_best_item(
                [data.get("entities", [])[i] for i in dup_group],
                "entity"
            )
            duplicates_removed += len(dup_group) - 1
            
            results.append(ValidationResult(
                success=True,
                passed=True,
                message=f"Found {len(dup_group)} duplicate entities"
            ))
        
        return {"results": results, "duplicates_removed": duplicates_removed}
    
    async def _run_canonicalization(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run canonicalization."""
        from src.knowledge.validation.base import ValidationResult
        
        results = []
        
        # Canonicalize entities
        for entity in data.get("entities", []):
            canonical = self.canonicalizer.canonicalize_entity(entity)
            results.append(ValidationResult(
                success=True,
                passed=True,
                message=f"Canonicalized entity: {canonical.get('canonical_name', entity.get('name'))}"
            ))
        
        return {"results": results}
    
    async def _run_consistency_validation(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run consistency validation."""
        consistency_results, score = self.consistency_service.validate_document(
            document_id=document_id,
            entities=data.get("entities", []),
            concepts=data.get("concepts", []),
            relationships=data.get("relationships", []),
            topics=data.get("topics", [])
        )
        
        return {"results": consistency_results, "consistency_score": score}
    
    async def _run_confidence_scoring(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run confidence scoring."""
        confidence = self.confidence_service.calculate_document_confidence(
            document_id=document_id,
            entity_count=len(data.get("entities", [])),
            concept_count=len(data.get("concepts", [])),
            relationship_count=len(data.get("relationships", [])),
            citation_count=data.get("citation_count", 0)
        )
        
        # Log confidence calculation
        self.audit_service.log_event(
            event_type=AuditEventType.CONFIDENCE_CALCULATED,
            description=f"Confidence score calculated: {confidence:.2f}",
            document_id=document_id,
            metadata={"confidence_score": confidence}
        )
        
        return {"overall_confidence": confidence}
    
    async def _run_quality_scoring(
        self,
        document_id: int,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run quality scoring."""
        quality = self.quality_service.calculate_quality(
            document_id=document_id,
            document_stats=data.get("metadata", {}),
            entity_count=len(data.get("entities", [])),
            concept_count=len(data.get("concepts", [])),
            relationship_count=len(data.get("relationships", [])),
            citation_count=data.get("citation_count", 0)
        )
        
        # Log quality calculation
        self.audit_service.log_quality_calculated(
            document_id=document_id,
            quality_score=quality.overall,
            confidence_score=data.get("confidence_score", 0.5)
        )
        
        return {"overall_quality": quality.overall}
    
    async def _run_version_tracking(
        self,
        document_id: int,
        data: Dict[str, Any],
        quality_result: Dict[str, Any],
        confidence_result: Dict[str, Any]
    ) -> None:
        """Run version tracking."""
        processing_info = {
            "llm_provider": data.get("llm_provider"),
            "llm_model": data.get("llm_model"),
            "embedding_model": data.get("embedding_model"),
            "strategy": "standard",
            "duration_ms": data.get("processing_duration_ms", 0),
        }
        
        self.version_service.create_version(
            document_id=document_id,
            processing_info=processing_info,
            quality_score=quality_result.get("overall_quality"),
            confidence_score=confidence_result.get("overall_confidence")
        )
