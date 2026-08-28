"""
Document Classifier

Classifies uploaded documents into categories and determines
what actions can be performed on them.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re

from sqlalchemy.orm import Session

from src.work_intelligence.schemas import (
    DocumentType,
    DocumentClassification,
    DocumentClassificationRequest,
    DocumentClassificationResponse,
)
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity
from src.core.logging import logger


# Document type signatures
DOCUMENT_SIGNATURES: Dict[DocumentType, Dict[str, Any]] = {
    DocumentType.INVOICE: {
        "keywords": [
            "invoice", "bill to", "ship to", "amount due", "payment terms",
            "line item", "subtotal", "tax", "vat", "total", "invoice number",
            "due date", "account", "billing", "purchase order"
        ],
        "patterns": [
            r"invoice\s*#?\s*:?\s*\d+",
            r"amount\s*due\s*:?\s*[$€£¥]",
            r"bill\s*to\s*:",
            r"payment\s*terms",
            r"\$\s*[\d,]+\.?\d*",
        ],
        "required_keywords": ["invoice", "amount"],
    },
    DocumentType.CONTRACT: {
        "keywords": [
            "agreement", "contract", "party", "whereas", "herein", "shall",
            "terms and conditions", "signature", "effective date", "jurisdiction",
            "amendment", "termination", "liability", "indemnification"
        ],
        "patterns": [
            r"agreement\s+between",
            r"contract\s+number",
            r"party\s+(?:a|b)",
            r"herein\s+referred",
            r"witnesseth",
        ],
        "required_keywords": ["agreement", "contract"],
    },
    DocumentType.EMAIL: {
        "keywords": [
            "from", "to", "subject", "cc", "bcc", "regards", "sincerely",
            "dear", "best regards", "sent", "received", "forwarded"
        ],
        "patterns": [
            r"from:\s*.+@",
            r"to:\s*.+@",
            r"subject:\s*",
            r"sent:\s*\d{4}",
        ],
        "required_keywords": ["from", "to", "subject"],
    },
    DocumentType.RESEARCH_PAPER: {
        "keywords": [
            "abstract", "introduction", "methodology", "results", "discussion",
            "conclusion", "references", "citation", "doi", "peer review",
            "hypothesis", "experiment", "analysis", "findings", "figure",
            "table", "appendix", "acknowledgments", "bibliography"
        ],
        "patterns": [
            r"abstract\s*[:\n]",
            r"figure\s+\d+",
            r"table\s+\d+",
            r"doi\s*:?\s*10\.",
            r"references\s*[:\n]",
        ],
        "required_keywords": ["abstract", "introduction", "results"],
    },
    DocumentType.RESUME: {
        "keywords": [
            "resume", "curriculum vitae", "cv", "experience", "education",
            "skills", "certifications", "objective", "summary", "work history",
            "achievements", "references", "contact", "phone", "email"
        ],
        "patterns": [
            r"(?:work\s+)?history",
            r"education\s*[:\n]",
            r"skills\s*[:\n]",
            r"experience\s*[:\n]",
            r"\b\d{4}\s*-\s*\d{4}\b",  # Date ranges
        ],
        "required_keywords": ["experience", "education"],
    },
    DocumentType.MEETING_NOTES: {
        "keywords": [
            "meeting", "agenda", "minutes", "attendees", "action items",
            "decisions", "discussion", "notes", "present", "absent",
            "next meeting", "follow up", "deadline", "assignee"
        ],
        "patterns": [
            r"meeting\s+(?:notes|minutes)",
            r"attendees?\s*[:\n]",
            r"action\s+items?\s*[:\n]",
            r"decisions?\s*[:\n]",
            r"(?:date|time)\s*[:\n]",
        ],
        "required_keywords": ["meeting", "action items"],
    },
    DocumentType.PRESENTATION: {
        "keywords": [
            "slide", "presentation", "bullet points", "key takeaways",
            "agenda", "overview", "summary", "conclusion", "next steps",
            "questions", "speaker notes", "transition"
        ],
        "patterns": [
            r"slide\s*\d+",
            r"speaker\s+notes?",
            r"(?:bullet|key)\s+(?:point|takeaway)",
        ],
        "required_keywords": ["slide", "presentation"],
    },
    DocumentType.SPREADSHEET: {
        "keywords": [
            "data", "table", "column", "row", "cell", "total", "sum",
            "average", "count", "formula", "spreadsheet", "excel", "csv"
        ],
        "patterns": [
            r"(?:total|sum)\s*[:=]",
            r"=SUM\(",
            r"=AVERAGE\(",
            r"column\s+[a-z]",
            r"row\s+\d+",
        ],
        "required_keywords": ["data", "table"],
    },
    DocumentType.LEGAL_DOCUMENT: {
        "keywords": [
            "plaintiff", "defendant", "court", "judge", "ruling", "verdict",
            "statute", "case law", "precedent", "testimony", "evidence",
            "counsel", "motion", "petition", "hearing"
        ],
        "patterns": [
            r"case\s+(?:no|number)\s*[:#]\s*\d+",
            r"court\s+(?:of|file)\s+\w+",
            r"plaintiff\s+v(?:ersus|s)\s+\w+",
        ],
        "required_keywords": ["court", "plaintiff"],
    },
    DocumentType.MEDICAL_REPORT: {
        "keywords": [
            "patient", "diagnosis", "treatment", "symptoms", "medication",
            "prescription", "physician", "hospital", "diagnosis", "procedure",
            "vital signs", "lab results", "medical history"
        ],
        "patterns": [
            r"patient\s*[:\n]",
            r"diagnosis\s*[:\n]",
            r"treatment\s*[:\n]",
            r"(?:date|time)\s+of\s+(?:birth|visit)",
        ],
        "required_keywords": ["patient", "diagnosis"],
    },
    DocumentType.BUSINESS_REPORT: {
        "keywords": [
            "executive summary", "financial", "revenue", "profit", "loss",
            "market share", "competitors", "analysis", "recommendations",
            "kpis", "metrics", "quarterly", "annual report"
        ],
        "patterns": [
            r"executive\s+summary",
            r"revenue\s*(?:growth|decline)",
            r"quarter(?:ly)?\s+(?:results|report)",
            r"financial\s+(?:highlights|summary)",
        ],
        "required_keywords": ["executive summary", "financial"],
    },
    DocumentType.LECTURE_NOTES: {
        "keywords": [
            "lecture", "professor", "student", "course", "chapter",
            "topic", "learning objectives", "key concepts", "homework",
            "reading", "quiz", "exam", "semester"
        ],
        "patterns": [
            r"lecture\s+\d+",
            r"chapter\s+\d+",
            r"learning\s+objectives?",
            r"key\s+concepts?",
        ],
        "required_keywords": ["lecture", "course"],
    },
}


@dataclass
class ClassificationContext:
    """Context for document classification."""
    content: str
    filename: str
    content_type: Optional[str]
    entities: List[Dict[str, Any]]
    language: Optional[str]


class DocumentClassifier:
    """
    Classifier for determining document types and suggesting actions.
    
    Features:
    - Multi-criteria classification
    - Confidence scoring
    - Field extraction
    - Action suggestions
    """

    def __init__(self, db: Session):
        """Initialize the classifier."""
        self.db = db

    async def classify(
        self,
        request: DocumentClassificationRequest
    ) -> DocumentClassificationResponse:
        """
        Classify a document.
        
        Args:
            request: Classification request
            
        Returns:
            Document classification with suggested actions
        """
        # Gather document data
        context = await self._gather_document_context(
            document_id=request.document_id,
            content=request.content,
            filename=request.filename,
            content_type=request.content_type
        )
        
        # Classify document
        classification = self._classify_document(context)
        
        # Get suggested actions
        suggested_actions = self._get_suggested_actions(classification)
        
        # Get relevant workflows
        relevant_workflows = self._get_relevant_workflows(classification)
        
        return DocumentClassificationResponse(
            classification=classification,
            suggested_actions=suggested_actions,
            relevant_workflows=relevant_workflows
        )

    async def _gather_document_context(
        self,
        document_id: Optional[int],
        content: Optional[str],
        filename: Optional[str],
        content_type: Optional[str]
    ) -> ClassificationContext:
        """Gather document context from various sources."""
        context = ClassificationContext(
            content=content or "",
            filename=filename or "",
            content_type=content_type,
            entities=[],
            language=None
        )
        
        # Get document from database
        if document_id:
            doc = self.db.query(Document).filter(
                Document.id == document_id
            ).first()
            
            if doc:
                context.content_type = doc.content_type
                context.filename = doc.filename
                context.language = doc.language_code
                
                # Get extracted entities
                entities = self.db.query(KnowledgeEntity).filter(
                    KnowledgeEntity.document_id == document_id
                ).limit(30).all()
                
                context.entities = [
                    {"name": e.name, "type": str(e.entity_type.value if hasattr(e.entity_type, 'value') else e.entity_type)}
                    for e in entities
                ]
                
                # Get summary if available
                if doc.summary:
                    context.content += " " + (doc.summary.content or "")
        
        # Try to infer content from filename
        if not context.content and context.filename:
            context.content = context.filename
        
        return context

    def _classify_document(
        self,
        context: ClassificationContext
    ) -> DocumentClassification:
        """Classify the document based on content analysis."""
        scores: Dict[DocumentType, float] = {}
        content_lower = context.content.lower()
        filename_lower = context.filename.lower()
        
        # Score each document type
        for doc_type, signature in DOCUMENT_SIGNATURES.items():
            score = 0.0
            matches = []
            
            # Keyword matching
            keyword_count = 0
            for keyword in signature["keywords"]:
                if keyword in content_lower or keyword in filename_lower:
                    keyword_count += 1
            keyword_score = keyword_count / len(signature["keywords"])
            
            # Pattern matching
            pattern_count = 0
            for pattern in signature["patterns"]:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    pattern_count += 1
            pattern_score = pattern_count / max(len(signature["patterns"]), 1)
            
            # Required keywords check
            required_met = all(
                kw in content_lower or kw in filename_lower
                for kw in signature.get("required_keywords", [])
            )
            
            # Calculate final score
            if required_met:
                score = (keyword_score * 0.6) + (pattern_score * 0.4)
                matches = signature["keywords"][:5]
            else:
                score = (keyword_score * 0.6) + (pattern_score * 0.4) * 0.5
            
            scores[doc_type] = score
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            # Default to unknown
            return DocumentClassification(
                document_type=DocumentType.UNKNOWN,
                confidence=0.3,
                reasoning="No clear document type pattern detected",
                subtypes=[],
                detected_fields={},
                language=context.language,
                is_multilingual=self._is_multilingual(context.content),
                requires_ocr=self._requires_ocr(context.content_type),
                requires_special_handling=False
            )
        
        best_type = max(scores, key=scores.get)
        best_score = scores[best_type]
        
        # Generate subtypes
        subtypes = self._extract_subtypes(context, best_type)
        
        # Extract fields
        detected_fields = self._extract_fields(context, best_type)
        
        return DocumentClassification(
            document_type=best_type,
            confidence=min(best_score + 0.2, 0.95),
            reasoning=f"Document classified as {best_type.value} based on content analysis",
            subtypes=subtypes,
            detected_fields=detected_fields,
            language=context.language or "en",
            is_multilingual=self._is_multilingual(context.content),
            requires_ocr=self._requires_ocr(context.content_type),
            requires_special_handling=best_type in [
                DocumentType.SCANNED_DOCUMENT,
                DocumentType.LEGAL_DOCUMENT,
                DocumentType.MEDICAL_REPORT,
            ]
        )

    def _extract_subtypes(
        self,
        context: ClassificationContext,
        doc_type: DocumentType
    ) -> List[str]:
        """Extract document subtypes."""
        subtypes = []
        content_lower = context.content.lower()
        
        # Check for common subtypes
        if doc_type == DocumentType.INVOICE:
            if "vendor" in content_lower:
                subtypes.append("vendor_invoice")
            if "client" in content_lower:
                subtypes.append("client_invoice")
            if "proforma" in content_lower:
                subtypes.append("proforma")
            if "credit" in content_lower:
                subtypes.append("credit_note")
        
        elif doc_type == DocumentType.RESEARCH_PAPER:
            if "systematic review" in content_lower:
                subtypes.append("systematic_review")
            if "meta-analysis" in content_lower:
                subtypes.append("meta_analysis")
            if "case study" in content_lower:
                subtypes.append("case_study")
            if "literature review" in content_lower:
                subtypes.append("literature_review")
        
        elif doc_type == DocumentType.RESUME:
            if "senior" in content_lower or "lead" in content_lower:
                subtypes.append("senior_level")
            if "junior" in content_lower or "entry" in content_lower:
                subtypes.append("entry_level")
            if "academic" in content_lower or "professor" in content_lower:
                subtypes.append("academic")
        
        return subtypes

    def _extract_fields(
        self,
        context: ClassificationContext,
        doc_type: DocumentType
    ) -> Dict[str, Any]:
        """Extract relevant fields from document."""
        fields = {}
        content = context.content
        
        if doc_type == DocumentType.INVOICE:
            # Extract invoice fields
            invoice_num = re.search(r"invoice\s*#?\s*:?\s*([A-Z0-9-]+)", content, re.IGNORECASE)
            if invoice_num:
                fields["invoice_number"] = invoice_num.group(1)
            
            amount = re.search(r"(?:amount\s*due|total)[:\s]*[$€£¥]?\s*([\d,]+\.?\d*)", content, re.IGNORECASE)
            if amount:
                fields["amount"] = amount.group(1)
            
            date = re.search(r"(?:date|due\s*date)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})", content, re.IGNORECASE)
            if date:
                fields["date"] = date.group(1)
        
        elif doc_type == DocumentType.EMAIL:
            from_addr = re.search(r"from:\s*(.+?)(?:\n|$)", content)
            to_addr = re.search(r"to:\s*(.+?)(?:\n|$)", content)
            subject = re.search(r"subject:\s*(.+?)(?:\n|$)", content)
            
            if from_addr:
                fields["from"] = from_addr.group(1).strip()
            if to_addr:
                fields["to"] = to_addr.group(1).strip()
            if subject:
                fields["subject"] = subject.group(1).strip()
        
        elif doc_type == DocumentType.RESUME:
            email = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content)
            phone = re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content)
            
            if email:
                fields["email"] = email.group(0)
            if phone:
                fields["phone"] = phone.group(0)
        
        # Add entity information
        if context.entities:
            fields["entities"] = context.entities[:10]
        
        return fields

    def _get_suggested_actions(
        self,
        classification: DocumentClassification
    ) -> List[str]:
        """Get suggested actions based on document type."""
        action_map: Dict[DocumentType, List[str]] = {
            DocumentType.INVOICE: [
                "extract_line_items",
                "generate_excel",
                "generate_accounting_summary",
                "create_email",
                "translate",
            ],
            DocumentType.CONTRACT: [
                "summarize_clauses",
                "extract_obligations",
                "check_compliance",
                "generate_risk_report",
            ],
            DocumentType.EMAIL: [
                "draft_reply",
                "extract_tasks",
                "generate_summary",
                "create_calendar_event",
            ],
            DocumentType.RESEARCH_PAPER: [
                "generate_summary",
                "create_flashcards",
                "generate_quiz",
                "create_presentation",
                "build_knowledge_graph",
            ],
            DocumentType.RESUME: [
                "analyze_ats",
                "match_jobs",
                "generate_cover_letter",
                "suggest_improvements",
            ],
            DocumentType.MEETING_NOTES: [
                "extract_action_items",
                "generate_timeline",
                "create_tasks",
                "send_follow_up_email",
            ],
            DocumentType.PRESENTATION: [
                "generate_notes",
                "create_transcript",
                "extract_key_points",
            ],
            DocumentType.SPREADSHEET: [
                "analyze_data",
                "generate_charts",
                "create_summary",
            ],
            DocumentType.LEGAL_DOCUMENT: [
                "summarize",
                "extract_risks",
                "check_compliance",
            ],
            DocumentType.MEDICAL_REPORT: [
                "summarize",
                "extract_findings",
                "create_action_plan",
            ],
            DocumentType.BUSINESS_REPORT: [
                "generate_summary",
                "extract_metrics",
                "create_presentation",
                "track_kpis",
            ],
            DocumentType.LECTURE_NOTES: [
                "generate_flashcards",
                "create_quiz",
                "build_learning_path",
            ],
            DocumentType.UNKNOWN: [
                "analyze_document",
                "generate_summary",
                "suggest_actions",
            ],
        }
        
        return action_map.get(
            classification.document_type,
            ["analyze_document", "generate_summary"]
        )

    def _get_relevant_workflows(
        self,
        classification: DocumentClassification
    ) -> List[str]:
        """Get relevant workflows based on document type."""
        workflow_map: Dict[DocumentType, List[str]] = {
            DocumentType.INVOICE: ["invoice_processing", "financial_report"],
            DocumentType.CONTRACT: ["contract_review", "compliance_check"],
            DocumentType.EMAIL: ["email_processing", "task_extraction"],
            DocumentType.RESEARCH_PAPER: ["research_analysis", "study_pack"],
            DocumentType.RESUME: ["resume_analysis", "job_application"],
            DocumentType.MEETING_NOTES: ["meeting_processing", "action_items"],
            DocumentType.BUSINESS_REPORT: ["business_analysis", "report_generation"],
        }
        
        return workflow_map.get(
            classification.document_type,
            ["document_analysis"]
        )

    def _is_multilingual(self, content: str) -> bool:
        """Check if content appears multilingual."""
        if not content:
            return False
        
        # Check for multiple scripts
        scripts = set()
        for char in content[:1000]:  # Check first 1000 chars
            if '\u4e00' <= char <= '\u9fff':
                scripts.add("cjk")
            elif '\u0600' <= char <= '\u06ff':
                scripts.add("arabic")
            elif '\u0400' <= char <= '\u04ff':
                scripts.add("cyrillic")
            elif '\u0900' <= char <= '\u097f':
                scripts.add("devanagari")
            elif 'a' <= char <= 'z' or 'A' <= char <= 'Z':
                scripts.add("latin")
        
        return len(scripts) > 1

    def _requires_ocr(self, content_type: Optional[str]) -> bool:
        """Check if document likely requires OCR."""
        if not content_type:
            return False
        
        image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        pdf_types = ["application/pdf"]
        
        return content_type in image_types or content_type in pdf_types


def get_document_classifier(db: Session) -> DocumentClassifier:
    """Get document classifier instance."""
    return DocumentClassifier(db)
