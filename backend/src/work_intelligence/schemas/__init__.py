"""
Work Intelligence Schemas

Pydantic schemas for the AI Work Intelligence Layer.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DocumentType(str, Enum):
    """Document types that the AI can understand."""
    INVOICE = "invoice"
    CONTRACT = "contract"
    EMAIL = "email"
    RESEARCH_PAPER = "research_paper"
    RESUME = "resume"
    MEETING_NOTES = "meeting_notes"
    PRESENTATION = "presentation"
    SPREADSHEET = "spreadsheet"
    WEBSITE = "website"
    GITHUB_REPO = "github_repo"
    VIDEO = "video"
    SCANNED_DOCUMENT = "scanned_document"
    LEGAL_DOCUMENT = "legal_document"
    MEDICAL_REPORT = "medical_report"
    BUSINESS_REPORT = "business_report"
    LECTURE_NOTES = "lecture_notes"
    BOOK = "book"
    UNKNOWN = "unknown"


class IntentCategory(str, Enum):
    """Intent categories for user actions."""
    ANALYZE = "analyze"
    CREATE = "create"
    EXTRACT = "extract"
    TRANSLATE = "translate"
    COMPARE = "compare"
    SUMMARIZE = "summarize"
    EXPLAIN = "explain"
    GENERATE = "generate"
    EXPORT = "export"
    COMMUNICATE = "communicate"
    PLAN = "plan"
    REVIEW = "review"
    TRACK = "track"


class ActionCategory(str, Enum):
    """Categories for available actions."""
    DOCUMENT = "document"
    ANALYSIS = "analysis"
    CREATION = "creation"
    COMMUNICATION = "communication"
    EXPORT = "export"
    TRANSLATION = "translation"
    LEARNING = "learning"
    COLLABORATION = "collaboration"
    AUTOMATION = "automation"


class OutputType(str, Enum):
    """Output types for actions."""
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    CSV = "csv"
    PPTX = "pptx"
    EMAIL = "email"
    JSON = "json"
    IMAGE = "image"


class WorkflowStatus(str, Enum):
    """Workflow execution status."""
    QUEUED = "queued"
    PREPARING = "preparing"
    UNDERSTANDING = "understanding"
    REASONING = "reasoning"
    PROCESSING = "processing"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Intent Engine Schemas
# ============================================================================

class IntentAnalysisRequest(BaseModel):
    """Request for intent analysis."""
    message: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    user_id: Optional[int] = None


class DetectedIntent(BaseModel):
    """Detected intent from user input."""
    category: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    entities: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)


class IntentAnalysisResponse(BaseModel):
    """Response from intent analysis."""
    primary_intent: DetectedIntent
    alternative_intents: List[DetectedIntent] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    suggested_questions: List[str] = Field(default_factory=list)
    recommended_workflow: Optional[str] = None
    suggested_output_type: OutputType = OutputType.TEXT
    priority: int = Field(default=5, ge=1, le=10)


# ============================================================================
# Document Classifier Schemas
# ============================================================================

class DocumentClassificationRequest(BaseModel):
    """Request for document classification."""
    document_id: Optional[int] = None
    content: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class DocumentClassification(BaseModel):
    """Document classification result."""
    document_type: DocumentType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    subtypes: List[str] = Field(default_factory=list)
    detected_fields: Dict[str, Any] = Field(default_factory=dict)
    language: Optional[str] = None
    is_multilingual: bool = False
    requires_ocr: bool = False
    requires_special_handling: bool = False


class DocumentClassificationResponse(BaseModel):
    """Response from document classification."""
    classification: DocumentClassification
    suggested_actions: List[str] = Field(default_factory=list)
    relevant_workflows: List[str] = Field(default_factory=list)


# ============================================================================
# Action Registry Schemas
# ============================================================================

class ActionDefinition(BaseModel):
    """Definition of an available action."""
    id: str
    title: str
    description: str
    icon: str
    category: ActionCategory
    supported_document_types: List[DocumentType] = Field(default_factory=list)
    supported_languages: List[str] = Field(default_factory=list)
    required_permissions: List[str] = Field(default_factory=list)
    required_inputs: Dict[str, Any] = Field(default_factory=dict)
    estimated_duration_seconds: int = 60
    workflow_id: Optional[str] = None
    output_type: OutputType = OutputType.TEXT
    tags: List[str] = Field(default_factory=list)


class ActionExecutionRequest(BaseModel):
    """Request to execute an action."""
    action_id: str
    document_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    output_type: Optional[OutputType] = None


class ActionExecutionResponse(BaseModel):
    """Response from action execution."""
    action_id: str
    success: bool
    output: Optional[Any] = None
    output_url: Optional[str] = None
    download_filename: Optional[str] = None
    error: Optional[str] = None
    execution_time_ms: int = 0


# ============================================================================
# Recommendation Engine Schemas
# ============================================================================

class RecommendationRequest(BaseModel):
    """Request for recommendations."""
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = None
    max_recommendations: int = Field(default=5, ge=1, le=20)


class Recommendation(BaseModel):
    """A recommendation for user action."""
    action_id: str
    title: str
    description: str
    reason: str
    confidence: float = Field(ge=0.0, le=1.0)
    priority: int = Field(ge=1, le=10)
    category: ActionCategory
    workflow_id: Optional[str] = None
    estimated_duration_seconds: int = 60
    icon: str = "lightbulb"


class RecommendationResponse(BaseModel):
    """Response with recommendations."""
    recommendations: List[Recommendation]
    total_count: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Question Generator Schemas
# ============================================================================

class QuestionGenerationRequest(BaseModel):
    """Request for question generation."""
    document_id: Optional[int] = None
    content: Optional[str] = None
    document_type: Optional[DocumentType] = None
    max_questions: int = Field(default=5, ge=1, le=20)
    question_types: List[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    """A generated question."""
    question: str
    type: str
    context: str
    difficulty: str = "intermediate"
    related_action: Optional[str] = None


class QuestionGenerationResponse(BaseModel):
    """Response with generated questions."""
    questions: List[GeneratedQuestion]
    total_count: int
    document_id: Optional[int] = None


# ============================================================================
# Workflow Execution Schemas
# ============================================================================

class WorkflowStepStatus(BaseModel):
    """Status of a workflow step."""
    step_name: str
    status: WorkflowStatus
    progress_percent: int = 0
    message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowExecutionRequest(BaseModel):
    """Request to execute a workflow."""
    workflow_id: str
    document_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    output_type: Optional[OutputType] = None


class WorkflowExecutionResponse(BaseModel):
    """Response from workflow execution."""
    execution_id: str
    workflow_id: str
    status: WorkflowStatus
    steps: List[WorkflowStepStatus] = Field(default_factory=list)
    progress_percent: int = 0
    output: Optional[Any] = None
    output_url: Optional[str] = None
    download_filename: Optional[str] = None
    error: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# Work Intelligence Session Schemas
# ============================================================================

class WorkIntelligenceRequest(BaseModel):
    """Complete request for work intelligence."""
    message: Optional[str] = None
    document_id: Optional[int] = None
    workspace_id: Optional[int] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    intent_only: bool = False
    classify_only: bool = False
    recommend_only: bool = False
    generate_questions_only: bool = False


class WorkIntelligenceResponse(BaseModel):
    """Complete response from work intelligence."""
    # Intent analysis
    intent: Optional[IntentAnalysisResponse] = None
    
    # Document classification
    classification: Optional[DocumentClassificationResponse] = None
    
    # Recommendations
    recommendations: Optional[RecommendationResponse] = None
    
    # Questions
    questions: Optional[QuestionGenerationResponse] = None
    
    # Quick actions
    suggested_actions: List[ActionDefinition] = Field(default_factory=list)
    
    # Suggested workflow
    suggested_workflow: Optional[str] = None
    
    # All available actions
    all_actions: List[ActionDefinition] = Field(default_factory=list)
