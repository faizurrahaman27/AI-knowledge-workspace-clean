"""
Research Operating System Module

Enterprise-grade AI-assisted research capabilities.
"""

from src.research.models import (
    ResearchProject,
    ResearchTask,
    ResearchEvidence,
    ResearchConflict,
    ResearchReport,
    ResearchSession,
    ResearchPlan,
    ResearchStatus,
    TaskStatus,
    EvidenceSource,
    ValidationConfidence,
)

from src.research.planner_service import ResearchPlannerService
from src.research.evidence_service import EvidenceService
from src.research.conflict_service import ConflictDetectionService
from src.research.synthesis_service import SynthesisService
from src.research.report_service import ReportGenerationService

__all__ = [
    # Models
    "ResearchProject",
    "ResearchTask",
    "ResearchEvidence",
    "ResearchConflict",
    "ResearchReport",
    "ResearchSession",
    "ResearchPlan",
    "ResearchStatus",
    "TaskStatus",
    "EvidenceSource",
    "ValidationConfidence",
    # Services
    "ResearchPlannerService",
    "EvidenceService",
    "ConflictDetectionService",
    "SynthesisService",
    "ReportGenerationService",
]
