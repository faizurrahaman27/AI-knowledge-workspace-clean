"""
Work Intelligence API

REST API for AI Work Intelligence Layer.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.work_intelligence.schemas import (
    WorkIntelligenceRequest,
    WorkIntelligenceResponse,
    IntentAnalysisRequest,
    IntentAnalysisResponse,
    DocumentClassificationRequest,
    DocumentClassificationResponse,
    RecommendationRequest,
    RecommendationResponse,
    QuestionGenerationRequest,
    QuestionGenerationResponse,
    ActionExecutionRequest,
    ActionExecutionResponse,
    WorkflowExecutionRequest,
    WorkflowExecutionResponse,
    ActionDefinition,
    DocumentType,
    ActionCategory,
)
from src.work_intelligence.services.work_intelligence_service import (
    get_work_intelligence_service,
    WorkIntelligenceService
)
from src.work_intelligence.services.intent_engine import get_intent_engine
from src.work_intelligence.services.document_classifier import get_document_classifier
from src.work_intelligence.services.action_registry import get_action_registry
from src.work_intelligence.services.recommendation_engine import get_recommendation_engine
from src.work_intelligence.services.question_generator import get_question_generator
from src.work_intelligence.services.workflow_executor import get_workflow_executor

router = APIRouter(prefix="/work-intelligence", tags=["Work Intelligence"])


# ============================================================================
# Work Intelligence - Unified Endpoint
# ============================================================================

@router.post("/", response_model=WorkIntelligenceResponse)
async def work_intelligence(
    request: WorkIntelligenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Complete work intelligence analysis.
    
    Analyzes user intent, classifies documents, generates recommendations
    and suggested questions in a single unified response.
    
    Use this endpoint for the "AI coworker" experience where every
    interaction provides intelligent suggestions.
    """
    service = get_work_intelligence_service(db)
    
    # Set user context
    if not request.workspace_id and not request.document_id:
        # Need to determine workspace from context
        pass
    
    result = await service.process(request)
    
    return result


@router.post("/quick-analyze")
async def quick_analyze(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Quick analysis of a document.
    
    Returns classification, recommendations, and questions in one call.
    """
    service = get_work_intelligence_service(db)
    
    result = await service.quick_analyze(
        document_id=document_id,
        user_id=current_user.id
    )
    
    return result


# ============================================================================
# Intent Engine Endpoints
# ============================================================================

@router.post("/intent/analyze", response_model=IntentAnalysisResponse)
async def analyze_intent(
    request: IntentAnalysisRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze user intent from message and context.
    
    Determines what the user wants to accomplish and recommends
    appropriate actions.
    """
    engine = get_intent_engine(db)
    
    # Add user context
    if not request.user_id:
        request.user_id = current_user.id
    
    result = await engine.analyze(request)
    
    return result


# ============================================================================
# Document Classifier Endpoints
# ============================================================================

@router.post("/classify", response_model=DocumentClassificationResponse)
async def classify_document(
    request: DocumentClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Classify a document and determine its type.
    
    Returns document type, suggested actions, and relevant workflows.
    """
    classifier = get_document_classifier(db)
    
    result = await classifier.classify(request)
    
    return result


@router.get("/document-types")
async def get_document_types():
    """Get all supported document types."""
    return {
        "types": [dt.value for dt in DocumentType]
    }


# ============================================================================
# Action Registry Endpoints
# ============================================================================

@router.get("/actions", response_model=List[ActionDefinition])
async def get_all_actions(
    category: Optional[ActionCategory] = None,
    document_type: Optional[str] = None,
    language: Optional[str] = None,
):
    """
    Get all available actions.
    
    Can filter by category, document type, or language.
    """
    registry = get_action_registry()
    
    if category:
        return registry.get_actions_by_category(category)
    elif document_type:
        try:
            dt = DocumentType(document_type)
            return registry.get_actions_for_document_type(dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document type")
    elif language:
        return registry.get_actions_for_languages([language])
    else:
        return registry.get_all_actions()


@router.get("/actions/{action_id}", response_model=ActionDefinition)
async def get_action(
    action_id: str,
):
    """Get a specific action by ID."""
    registry = get_action_registry()
    
    action = registry.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    
    return action


@router.post("/actions/execute", response_model=ActionExecutionResponse)
async def execute_action(
    request: ActionExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a specific action.
    
    The action will be performed on the specified document
    and the result returned.
    """
    registry = get_action_registry()
    
    result = await registry.execute_action(request, db)
    
    return result


@router.get("/actions/summary")
async def get_actions_summary():
    """Get summary of all actions."""
    registry = get_action_registry()
    return registry.get_actions_summary()


# ============================================================================
# Recommendation Engine Endpoints
# ============================================================================

@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    request: RecommendationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get AI-powered action recommendations.
    
    Returns recommended actions based on document and context.
    """
    engine = get_recommendation_engine(db)
    
    result = await engine.recommend(request)
    
    return result


# ============================================================================
# Question Generator Endpoints
# ============================================================================

@router.post("/questions/generate", response_model=QuestionGenerationResponse)
async def generate_questions(
    request: QuestionGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate suggested questions.
    
    Returns intelligent questions based on document content and type.
    """
    generator = get_question_generator(db)
    
    result = await generator.generate(request)
    
    return result


# ============================================================================
# Workflow Executor Endpoints
# ============================================================================

@router.get("/workflows")
async def get_available_workflows(
    db: Session = Depends(get_db),
):
    """Get all available workflows."""
    executor = get_workflow_executor(db)
    
    return {
        "workflows": executor.get_available_workflows()
    }


@router.post("/workflows/execute", response_model=WorkflowExecutionResponse)
async def execute_workflow(
    request: WorkflowExecutionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute a workflow.
    
    Runs a sequence of actions in order, tracking progress.
    """
    executor = get_workflow_executor(db)
    
    result = await executor.execute(request)
    
    return result


@router.get("/workflows/status/{execution_id}", response_model=WorkflowExecutionResponse)
async def get_workflow_status(
    execution_id: str,
    db: Session = Depends(get_db),
):
    """Get status of a workflow execution."""
    executor = get_workflow_executor(db)
    
    result = executor.get_execution_status(execution_id)
    if not result:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return result


@router.get("/workflows/from-action/{action_id}")
async def get_workflow_for_action(
    action_id: str,
    db: Session = Depends(get_db),
):
    """Get the workflow that contains a specific action."""
    executor = get_workflow_executor(db)
    
    workflow_id = executor.get_workflow_for_action(action_id)
    
    if not workflow_id:
        return {"workflow_id": None, "message": "Action is not part of any workflow"}
    
    workflows = executor.get_available_workflows()
    workflow = next((w for w in workflows if w["workflow_id"] == workflow_id), None)
    
    return {"workflow_id": workflow_id, "workflow": workflow}


# ============================================================================
# Context Endpoints
# ============================================================================

@router.get("/context/from-document/{document_id}")
async def get_context_from_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get context data from a document.
    
    Returns entities, concepts, and metadata for AI analysis.
    """
    from src.models.document import Document
    from src.knowledge.models import KnowledgeEntity, KnowledgeConcept
    
    # Get document
    doc = db.query(Document).filter(Document.id == document_id).first()
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get entities
    entities = db.query(KnowledgeEntity).filter(
        KnowledgeEntity.document_id == document_id
    ).limit(50).all()
    
    # Get concepts
    concepts = db.query(KnowledgeConcept).filter(
        KnowledgeConcept.document_id == document_id
    ).limit(50).all()
    
    return {
        "document_id": document_id,
        "filename": doc.filename,
        "content_type": doc.content_type,
        "language_code": doc.language_code,
        "entities": [
            {
                "name": e.name,
                "type": str(e.entity_type.value if hasattr(e.entity_type, 'value') else e.entity_type),
                "description": e.description
            }
            for e in entities
        ],
        "concepts": [
            {
                "name": c.name,
                "description": c.description
            }
            for c in concepts
        ],
        "summary": doc.summary.content if doc.summary else None
    }
