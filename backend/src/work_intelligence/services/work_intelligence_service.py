"""
Work Intelligence Service

Central service that orchestrates all AI Work Intelligence components.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    WorkIntelligenceRequest,
    WorkIntelligenceResponse,
    IntentAnalysisRequest,
    DocumentClassificationRequest,
    RecommendationRequest,
    QuestionGenerationRequest,
    ActionDefinition,
    IntentAnalysisResponse,
    DocumentClassificationResponse,
    RecommendationResponse,
    QuestionGenerationResponse,
)
from src.work_intelligence.services.intent_engine import get_intent_engine
from src.work_intelligence.services.document_classifier import get_document_classifier
from src.work_intelligence.services.action_registry import get_action_registry
from src.work_intelligence.services.recommendation_engine import get_recommendation_engine
from src.work_intelligence.services.question_generator import get_question_generator
from src.models.document import Document
from src.core.logging import logger


class WorkIntelligenceService:
    """
    Central orchestrator for AI Work Intelligence.
    
    Combines:
    - Intent Analysis
    - Document Classification
    - Action Recommendations
    - Question Generation
    
    To provide a unified "AI coworker" experience.
    """

    def __init__(self, db: Session):
        """Initialize the work intelligence service."""
        self.db = db
        self.intent_engine = get_intent_engine(db)
        self.document_classifier = get_document_classifier(db)
        self.action_registry = get_action_registry()
        self.recommendation_engine = get_recommendation_engine(db)
        self.question_generator = get_question_generator(db)

    async def process(
        self,
        request: WorkIntelligenceRequest
    ) -> WorkIntelligenceResponse:
        """
        Process a work intelligence request.
        
        Args:
            request: Work intelligence request
            
        Returns:
            Comprehensive work intelligence response
        """
        response = WorkIntelligenceResponse(
            suggested_actions=[],
            all_actions=self.action_registry.get_all_actions()
        )
        
        # 1. Intent Analysis (if not skipped)
        if not request.intent_only:
            intent_request = IntentAnalysisRequest(
                message=request.message,
                conversation_history=request.conversation_history,
                document_id=request.document_id,
                workspace_id=request.workspace_id
            )
            response.intent = await self.intent_engine.analyze(intent_request)
        
        # 2. Document Classification (if not skipped and document_id provided)
        if not request.classify_only and request.document_id:
            classify_request = DocumentClassificationRequest(
                document_id=request.document_id
            )
            response.classification = await self.document_classifier.classify(classify_request)
        
        # 3. Recommendations (if not skipped)
        if not request.recommend_only:
            recommend_request = RecommendationRequest(
                document_id=request.document_id,
                workspace_id=request.workspace_id,
                context={
                    "intent": response.intent.dict() if response.intent else None,
                    "classification": response.classification.dict() if response.classification else None,
                }
            )
            response.recommendations = await self.recommendation_engine.recommend(recommend_request)
        
        # 4. Question Generation (if not skipped and document_id provided)
        if not request.generate_questions_only and request.document_id:
            # Get document type from classification if available
            doc_type = None
            if response.classification:
                doc_type = response.classification.classification.document_type
            
            question_request = QuestionGenerationRequest(
                document_id=request.document_id,
                document_type=doc_type,
                max_questions=5
            )
            response.questions = await self.question_generator.generate(question_request)
        
        # 5. Build suggested actions from intent and recommendations
        response.suggested_actions = self._build_suggested_actions(response)
        
        # 6. Determine suggested workflow
        response.suggested_workflow = self._determine_workflow(response)
        
        return response

    def _build_suggested_actions(
        self,
        response: WorkIntelligenceResponse
    ) -> List[ActionDefinition]:
        """Build suggested actions from analysis results."""
        actions = []
        seen_ids = set()
        
        # Add from recommendations (highest priority)
        if response.recommendations:
            for rec in response.recommendations.recommendations[:3]:
                action = self.action_registry.get_action(rec.action_id)
                if action and rec.action_id not in seen_ids:
                    actions.append(action)
                    seen_ids.add(rec.action_id)
        
        # Add from intent recommendations
        if response.intent:
            for action_id in response.intent.recommended_actions[:2]:
                action = self.action_registry.get_action(action_id)
                if action and action_id not in seen_ids:
                    actions.append(action)
                    seen_ids.add(action_id)
        
        # Add from classification suggestions
        if response.classification:
            for action_id in response.classification.suggested_actions[:2]:
                action = self.action_registry.get_action(action_id)
                if action and action_id not in seen_ids:
                    actions.append(action)
                    seen_ids.add(action_id)
        
        return actions

    def _determine_workflow(
        self,
        response: WorkIntelligenceResponse
    ) -> Optional[str]:
        """Determine the best workflow based on context."""
        # Use intent recommendation if available
        if response.intent and response.intent.recommended_workflow:
            return response.intent.recommended_workflow
        
        # Use classification recommendation if available
        if response.classification:
            workflows = response.classification.relevant_workflows
            if workflows:
                return workflows[0]
        
        # Use recommendation workflow if available
        if response.recommendations:
            for rec in response.recommendations.recommendations:
                if rec.workflow_id:
                    return rec.workflow_id
        
        return None

    async def quick_analyze(
        self,
        document_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Quick analysis of a document.
        
        Args:
            document_id: Document ID
            user_id: User ID
            
        Returns:
            Quick analysis results
        """
        # Classify document
        classify_request = DocumentClassificationRequest(document_id=document_id)
        classification = await self.document_classifier.classify(classify_request)
        
        # Get recommendations
        recommend_request = RecommendationRequest(
            document_id=document_id,
            max_recommendations=5
        )
        recommendations = await self.recommendation_engine.recommend(recommend_request)
        
        # Generate questions
        question_request = QuestionGenerationRequest(
            document_id=document_id,
            document_type=classification.classification.document_type,
            max_questions=5
        )
        questions = await self.question_generator.generate(question_request)
        
        return {
            "classification": classification.dict(),
            "recommendations": recommendations.dict(),
            "questions": questions.dict(),
            "suggested_actions": [
                self.action_registry.get_action(rec.action_id)
                for rec in recommendations.recommendations[:5]
            ]
        }


def get_work_intelligence_service(db: Session) -> WorkIntelligenceService:
    """Get work intelligence service instance."""
    return WorkIntelligenceService(db)
