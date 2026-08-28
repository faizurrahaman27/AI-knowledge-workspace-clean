"""
Intent Engine

Analyzes user intent from messages, conversation history, and context.
Determines what actions the user wants to take.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    IntentCategory,
    OutputType,
    DetectedIntent,
    IntentAnalysisResponse,
    IntentAnalysisRequest,
)
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity, KnowledgeConcept
from src.core.logging import logger


# Intent patterns for classification
INTENT_PATTERNS: Dict[IntentCategory, List[str]] = {
    IntentCategory.ANALYZE: [
        r"analyze",
        r"examination",
        r"review",
        r"assess",
        r"evaluate",
        r"what does",
        r"what is",
        r"how does",
        r"explain",
    ],
    IntentCategory.CREATE: [
        r"create",
        r"generate",
        r"make",
        r"produce",
        r"build",
        r"draft",
        r"write",
    ],
    IntentCategory.EXTRACT: [
        r"extract",
        r"get",
        r"pull",
        r"find",
        r"show me",
        r"list",
        r"what are",
        r"who is",
        r"when",
        r"where",
    ],
    IntentCategory.TRANSLATE: [
        r"translate",
        r"convert",
        r"to spanish",
        r"to english",
        r"to french",
        r"to german",
        r"in arabic",
        r"in hindi",
    ],
    IntentCategory.COMPARE: [
        r"compare",
        r"difference",
        r"versus",
        r"vs",
        r"between",
        r"contrast",
    ],
    IntentCategory.SUMMARIZE: [
        r"summary",
        r"summarize",
        r"brief",
        r"overview",
        r"recap",
        r"tl;dr",
        r"short version",
    ],
    IntentCategory.EXPLAIN: [
        r"explain",
        r"what do you mean",
        r"clarify",
        r"elaborate",
        r"how does",
        r"why",
    ],
    IntentCategory.GENERATE: [
        r"generate",
        r"create",
        r"make",
        r"produce",
        r"build",
    ],
    IntentCategory.EXPORT: [
        r"export",
        r"download",
        r"save as",
        r"get the",
        r"send me",
    ],
    IntentCategory.COMMUNICATE: [
        r"email",
        r"send",
        r"reply",
        r"compose",
        r"message",
        r"contact",
    ],
    IntentCategory.PLAN: [
        r"plan",
        r"schedule",
        r"organize",
        r"timeline",
        r"roadmap",
        r"milestones",
    ],
    IntentCategory.REVIEW: [
        r"review",
        r"check",
        r"validate",
        r"verify",
        r"audit",
    ],
    IntentCategory.TRACK: [
        r"track",
        r"monitor",
        r"follow",
        r"status",
        r"progress",
    ],
}

# Action keywords mapping intents to actions
INTENT_TO_ACTIONS: Dict[IntentCategory, List[str]] = {
    IntentCategory.ANALYZE: [
        "analyze_document",
        "generate_insights",
        "extract_entities",
    ],
    IntentCategory.CREATE: [
        "generate_summary",
        "generate_presentation",
        "generate_report",
    ],
    IntentCategory.EXTRACT: [
        "extract_data",
        "extract_line_items",
        "extract_tasks",
    ],
    IntentCategory.TRANSLATE: [
        "translate_document",
        "generate_multilingual",
    ],
    IntentCategory.COMPARE: [
        "compare_documents",
        "generate_comparison",
    ],
    IntentCategory.SUMMARIZE: [
        "generate_summary",
        "generate_brief",
    ],
    IntentCategory.EXPLAIN: [
        "explain_simply",
        "explain_detailed",
    ],
    IntentCategory.GENERATE: [
        "generate_excel",
        "generate_csv",
        "generate_pdf",
        "generate_email",
    ],
    IntentCategory.EXPORT: [
        "export_document",
        "download_file",
    ],
    IntentCategory.COMMUNICATE: [
        "draft_email",
        "compose_message",
    ],
    IntentCategory.PLAN: [
        "generate_timeline",
        "create_roadmap",
    ],
    IntentCategory.REVIEW: [
        "analyze_document",
        "validate_content",
    ],
    IntentCategory.TRACK: [
        "generate_report",
        "track_progress",
    ],
}

# Intent to output type mapping
INTENT_TO_OUTPUT: Dict[IntentCategory, OutputType] = {
    IntentCategory.ANALYZE: OutputType.MARKDOWN,
    IntentCategory.CREATE: OutputType.MARKDOWN,
    IntentCategory.EXTRACT: OutputType.JSON,
    IntentCategory.TRANSLATE: OutputType.TEXT,
    IntentCategory.COMPARE: OutputType.MARKDOWN,
    IntentCategory.SUMMARIZE: OutputType.MARKDOWN,
    IntentCategory.EXPLAIN: OutputType.TEXT,
    IntentCategory.GENERATE: OutputType.PDF,
    IntentCategory.EXPORT: OutputType.CSV,
    IntentCategory.COMMUNICATE: OutputType.EMAIL,
    IntentCategory.PLAN: OutputType.MARKDOWN,
    IntentCategory.REVIEW: OutputType.MARKDOWN,
    IntentCategory.TRACK: OutputType.PDF,
}


@dataclass
class ContextData:
    """Context data for intent analysis."""
    entities: List[Dict[str, Any]] = None
    concepts: List[Dict[str, Any]] = None
    document_type: Optional[str] = None
    language: Optional[str] = None
    topics: List[str] = None
    summary: Optional[str] = None

    def __post_init__(self):
        self.entities = self.entities or []
        self.concepts = self.concepts or []
        self.topics = self.topics or []


class IntentEngine:
    """
    Engine for analyzing user intent.
    
    Analyzes:
    - User messages
    - Conversation history
    - Document context
    - Knowledge graph
    - Workspace data
    
    Determines:
    - Primary intent
    - Confidence
    - Recommended actions
    - Suggested questions
    - Output type
    """

    def __init__(self, db: Session):
        """Initialize the intent engine."""
        self.db = db

    async def analyze(
        self,
        request: IntentAnalysisRequest
    ) -> IntentAnalysisResponse:
        """
        Analyze user intent from request.
        
        Args:
            request: Intent analysis request
            
        Returns:
            Intent analysis response with detected intent and recommendations
        """
        # Get context data
        context = await self._gather_context(
            document_id=request.document_id,
            workspace_id=request.workspace_id,
            user_id=request.user_id
        )
        
        # Analyze message if provided
        message_intent = None
        if request.message:
            message_intent = self._analyze_message(request.message)
        
        # Analyze conversation history if provided
        history_intent = None
        if request.conversation_history:
            history_intent = self._analyze_history(request.conversation_history)
        
        # Combine intents
        primary_intent = message_intent or history_intent or self._create_default_intent()
        
        # Enhance with context
        primary_intent = self._enhance_with_context(primary_intent, context)
        
        # Generate alternatives
        alternative_intents = self._generate_alternatives(
            primary_intent,
            context
        )
        
        # Get recommended actions
        recommended_actions = INTENT_TO_ACTIONS.get(
            primary_intent.category,
            []
        )
        
        # Generate suggested questions
        suggested_questions = self._generate_suggested_questions(
            primary_intent.category,
            context
        )
        
        # Determine recommended workflow
        recommended_workflow = self._determine_workflow(primary_intent, context)
        
        # Determine output type
        suggested_output = INTENT_TO_OUTPUT.get(
            primary_intent.category,
            OutputType.TEXT
        )
        
        return IntentAnalysisResponse(
            primary_intent=primary_intent,
            alternative_intents=alternative_intents,
            recommended_actions=recommended_actions,
            suggested_questions=suggested_questions,
            recommended_workflow=recommended_workflow,
            suggested_output_type=suggested_output,
            priority=self._determine_priority(primary_intent)
        )

    def _analyze_message(self, message: str) -> DetectedIntent:
        """Analyze a single message for intent."""
        message_lower = message.lower()
        scores: Dict[IntentCategory, float] = {}
        
        # Score each intent category
        for category, patterns in INTENT_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    score += 1.0
            if score > 0:
                scores[category] = score / len(patterns)
        
        if not scores:
            return DetectedIntent(
                category=IntentCategory.ANALYZE,
                confidence=0.5,
                reasoning="No specific patterns detected, defaulting to analyze intent"
            )
        
        # Get highest scoring intent
        best_category = max(scores, key=scores.get)
        confidence = scores[best_category]
        
        return DetectedIntent(
            category=best_category,
            confidence=min(confidence, 0.95),
            reasoning=f"Detected {best_category.value} intent from pattern matching",
            entities=self._extract_entities_from_message(message)
        )

    def _analyze_history(
        self,
        history: List[Dict[str, str]]
    ) -> Optional[DetectedIntent]:
        """Analyze conversation history for intent."""
        if not history:
            return None
        
        # Get recent messages
        recent = history[-3:] if len(history) > 3 else history
        combined = " ".join(msg.get("content", "") for msg in recent)
        
        return self._analyze_message(combined)

    def _gather_context(
        self,
        document_id: Optional[int],
        workspace_id: Optional[int],
        user_id: Optional[int]
    ) -> ContextData:
        """Gather context data for intent analysis."""
        context = ContextData()
        
        if document_id:
            # Get document
            doc = self.db.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if doc:
                context.document_type = doc.content_type
                context.language = doc.language_code
                context.summary = doc.summary.content if doc.summary else None
                
                # Get entities
                entities = self.db.query(KnowledgeEntity).filter(
                    KnowledgeEntity.document_id == document_id
                ).limit(20).all()
                
                context.entities = [
                    {"name": e.name, "type": e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type)}
                    for e in entities
                ]
                
                # Get concepts
                concepts = self.db.query(KnowledgeConcept).filter(
                    KnowledgeConcept.document_id == document_id
                ).limit(20).all()
                
                context.concepts = [
                    {"name": c.name, "description": c.description}
                    for c in concepts
                ]
        
        return context

    def _enhance_with_context(
        self,
        intent: DetectedIntent,
        context: ContextData
    ) -> DetectedIntent:
        """Enhance intent detection with context data."""
        # Add entities from document
        if context.entities:
            entity_names = [e["name"] for e in context.entities[:5]]
            intent.entities.extend(entity_names)
        
        # Adjust confidence based on context
        if context.document_type:
            intent.context["document_type"] = context.document_type
            intent.confidence = min(intent.confidence + 0.1, 0.95)
        
        if context.language:
            intent.context["language"] = context.language
        
        return intent

    def _generate_alternatives(
        self,
        primary: DetectedIntent,
        context: ContextData
    ) -> List[DetectedIntent]:
        """Generate alternative intents."""
        alternatives = []
        
        # Add summarization as alternative if analyzing
        if primary.category == IntentCategory.ANALYZE:
            alternatives.append(DetectedIntent(
                category=IntentCategory.SUMMARIZE,
                confidence=0.4,
                reasoning="Alternative: summarize content for quick overview"
            ))
        
        # Add extraction as alternative
        if primary.category in [IntentCategory.ANALYZE, IntentCategory.CREATE]:
            alternatives.append(DetectedIntent(
                category=IntentCategory.EXTRACT,
                confidence=0.35,
                reasoning="Alternative: extract structured data from document"
            ))
        
        return alternatives[:3]  # Limit to 3 alternatives

    def _generate_suggested_questions(
        self,
        category: IntentCategory,
        context: ContextData
    ) -> List[str]:
        """Generate suggested questions based on intent."""
        questions: Dict[IntentCategory, List[str]] = {
            IntentCategory.ANALYZE: [
                "What are the main findings?",
                "Can you explain the key points?",
                "What is the significance?",
            ],
            IntentCategory.CREATE: [
                "What format do you need?",
                "Should I include examples?",
                "What tone should the output have?",
            ],
            IntentCategory.EXTRACT: [
                "What specific data do you need?",
                "Should I extract all or specific items?",
                "In what format should I return the data?",
            ],
            IntentCategory.TRANSLATE: [
                "Which language do you need?",
                "Should I preserve formatting?",
                "Is technical terminology acceptable?",
            ],
            IntentCategory.COMPARE: [
                "What aspects should I compare?",
                "Do you want a side-by-side comparison?",
                "Should I highlight similarities or differences?",
            ],
            IntentCategory.SUMMARIZE: [
                "How long should the summary be?",
                "Should I focus on specific sections?",
                "Do you want key takeaways?",
            ],
            IntentCategory.EXPLAIN: [
                "What level of detail do you need?",
                "Should I use simple language?",
                "Do you need examples?",
            ],
            IntentCategory.GENERATE: [
                "What template should I use?",
                "Should I include specific sections?",
                "What is the purpose of this document?",
            ],
            IntentCategory.EXPORT: [
                "What format do you prefer?",
                "Should I include all data or a subset?",
                "Do you need to schedule regular exports?",
            ],
            IntentCategory.COMMUNICATE: [
                "Who should receive this?",
                "What is the main message?",
                "What tone should I use?",
            ],
            IntentCategory.PLAN: [
                "What are the milestones?",
                "What is the timeline?",
                "Are there any constraints?",
            ],
            IntentCategory.REVIEW: [
                "What specific aspects should I check?",
                "Do you have criteria for review?",
                "Should I suggest improvements?",
            ],
            IntentCategory.TRACK: [
                "What metrics should I track?",
                "How often should updates be sent?",
                "Do you need visualizations?",
            ],
        }
        
        return questions.get(category, [
            "What specific information do you need?",
            "How would you like the results formatted?",
            "Do you need any follow-up actions?"
        ])

    def _determine_workflow(
        self,
        intent: DetectedIntent,
        context: ContextData
    ) -> Optional[str]:
        """Determine the recommended workflow."""
        workflow_map: Dict[IntentCategory, Dict[str, str]] = {
            IntentCategory.ANALYZE: {
                "invoice": "invoice_analysis",
                "contract": "contract_review",
                "research_paper": "research_analysis",
                "resume": "resume_analysis",
                "default": "document_analysis",
            },
            IntentCategory.CREATE: {
                "invoice": "create_report",
                "research_paper": "create_presentation",
                "default": "create_document",
            },
            IntentCategory.SUMMARIZE: {
                "default": "create_summary",
            },
            IntentCategory.GENERATE: {
                "invoice": "generate_excel",
                "research_paper": "generate_presentation",
                "default": "generate_document",
            },
        }
        
        # Get document type from context
        doc_type = context.document_type or "default"
        
        # Get workflow category map
        category_map = workflow_map.get(intent.category, {})
        
        return category_map.get(doc_type, category_map.get("default"))

    def _determine_priority(self, intent: DetectedIntent) -> int:
        """Determine priority based on intent."""
        high_priority = {
            IntentCategory.EXTRACT,
            IntentCategory.ANALYZE,
            IntentCategory.REVIEW,
        }
        
        medium_priority = {
            IntentCategory.CREATE,
            IntentCategory.GENERATE,
            IntentCategory.SUMMARIZE,
        }
        
        low_priority = {
            IntentCategory.TRANSLATE,
            IntentCategory.EXPORT,
        }
        
        if intent.category in high_priority:
            return 8
        elif intent.category in medium_priority:
            return 5
        elif intent.category in low_priority:
            return 3
        else:
            return 5

    def _extract_entities_from_message(self, message: str) -> List[str]:
        """Extract named entities from message."""
        # Simple entity extraction
        entities = []
        
        # Extract quoted strings
        quotes = re.findall(r'"([^"]+)"', message)
        entities.extend(quotes)
        
        # Extract capitalized phrases
        caps = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', message)
        entities.extend(caps[:3])  # Limit to 3
        
        return entities[:5]  # Limit to 5 entities

    def _create_default_intent(self) -> DetectedIntent:
        """Create default intent when no clear intent detected."""
        return DetectedIntent(
            category=IntentCategory.ANALYZE,
            confidence=0.3,
            reasoning="No clear intent pattern detected, defaulting to analyze"
        )


def get_intent_engine(db: Session) -> IntentEngine:
    """Get intent engine instance."""
    return IntentEngine(db)
