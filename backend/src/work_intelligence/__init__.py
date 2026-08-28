"""
AI Work Intelligence Layer

Transforms the AI Knowledge Workspace from "AI that answers questions"
into "AI that completes work."

Modules:
- Intent Engine: Analyzes user intent from messages and context
- Document Classifier: Classifies uploaded documents
- Action Registry: Plugin architecture for AI-powered actions
- Recommendation Engine: Generates intelligent action recommendations
- Question Generator: Generates suggested questions
- Workflow Executor: Executes dynamic action workflows
- Work Intelligence Service: Central orchestrator
"""

from src.work_intelligence.schemas import (
    # Enums
    DocumentType,
    IntentCategory,
    ActionCategory,
    OutputType,
    WorkflowStatus,
    # Intent Engine
    IntentAnalysisRequest,
    IntentAnalysisResponse,
    DetectedIntent,
    # Document Classifier
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    DocumentClassification,
    # Action Registry
    ActionDefinition,
    ActionExecutionRequest,
    ActionExecutionResponse,
    # Recommendations
    RecommendationRequest,
    RecommendationResponse,
    Recommendation,
    # Questions
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    GeneratedQuestion,
    # Workflow
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    WorkflowStepStatus,
    # Unified
    WorkIntelligenceRequest,
    WorkIntelligenceResponse,
)

from src.work_intelligence.services.work_intelligence_service import (
    WorkIntelligenceService,
    get_work_intelligence_service,
)

from src.work_intelligence.services.intent_engine import (
    IntentEngine,
    get_intent_engine,
)

from src.work_intelligence.services.document_classifier import (
    DocumentClassifier,
    get_document_classifier,
)

from src.work_intelligence.services.action_registry import (
    ActionRegistry,
    get_action_registry,
)

from src.work_intelligence.services.recommendation_engine import (
    RecommendationEngine,
    get_recommendation_engine,
)

from src.work_intelligence.services.question_generator import (
    QuestionGenerator,
    get_question_generator,
)

from src.work_intelligence.services.workflow_executor import (
    WorkflowExecutor,
    get_workflow_executor,
)

__all__ = [
    # Schemas
    "DocumentType",
    "IntentCategory",
    "ActionCategory",
    "OutputType",
    "WorkflowStatus",
    "IntentAnalysisRequest",
    "IntentAnalysisResponse",
    "DetectedIntent",
    "DocumentClassificationRequest",
    "DocumentClassificationResponse",
    "DocumentClassification",
    "ActionDefinition",
    "ActionExecutionRequest",
    "ActionExecutionResponse",
    "RecommendationRequest",
    "RecommendationResponse",
    "Recommendation",
    "QuestionGenerationRequest",
    "QuestionGenerationResponse",
    "GeneratedQuestion",
    "WorkflowExecutionRequest",
    "WorkflowExecutionResponse",
    "WorkflowStepStatus",
    "WorkIntelligenceRequest",
    "WorkIntelligenceResponse",
    # Services
    "WorkIntelligenceService",
    "get_work_intelligence_service",
    "IntentEngine",
    "get_intent_engine",
    "DocumentClassifier",
    "get_document_classifier",
    "ActionRegistry",
    "get_action_registry",
    "RecommendationEngine",
    "get_recommendation_engine",
    "QuestionGenerator",
    "get_question_generator",
    "WorkflowExecutor",
    "get_workflow_executor",
]
