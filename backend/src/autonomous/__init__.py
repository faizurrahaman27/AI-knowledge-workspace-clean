"""
Autonomous Learning System Module

Comprehensive autonomous knowledge understanding system.
"""

from src.autonomous.models import (
    KnowledgeNode,
    KnowledgeEdge,
    IntelligentNotebook,
    LearningPath,
    KnowledgeInsight,
    AIMemory,
    BackgroundJob,
    DocumentVersion,
    LearningProgress,
    EntityType,
    RelationshipType,
    QuestionDifficulty,
    QuestionType,
    FlashcardType,
    JobStatus,
)

from src.autonomous.services import (
    KnowledgeGraphService,
    IntelligentNotebookService,
    LearningPathService,
    InsightService,
    BackgroundWorker,
    JobExecutor,
    JobType,
    get_background_worker,
    get_job_executor,
)

__all__ = [
    # Models
    "KnowledgeNode",
    "KnowledgeEdge",
    "IntelligentNotebook",
    "LearningPath",
    "KnowledgeInsight",
    "AIMemory",
    "BackgroundJob",
    "DocumentVersion",
    "LearningProgress",
    "EntityType",
    "RelationshipType",
    "QuestionDifficulty",
    "QuestionType",
    "FlashcardType",
    "JobStatus",
    # Services
    "KnowledgeGraphService",
    "IntelligentNotebookService",
    "LearningPathService",
    "InsightService",
    "BackgroundWorker",
    "JobExecutor",
    "JobType",
    "get_background_worker",
    "get_job_executor",
]
