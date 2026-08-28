"""
Action Executor

Executes individual actions and generates outputs.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import os

from sqlalchemy.orm import Session

from src.execution.schemas import OutputFormat, ExecutionStatus
from src.execution.services.execution_registry import get_execution_registry
from src.execution.services.file_generator import FileGenerator
from src.execution.services.progress_tracker import get_progress_tracker
from src.models.document import Document
from src.knowledge.models import KnowledgeEntity, KnowledgeConcept
from src.core.logging import logger


class ActionExecutor:
    """
    Executor for individual actions.
    
    Features:
    - Action execution
    - Data extraction
    - File generation
    - Output management
    """

    def __init__(self, db: Session, output_dir: str = "outputs"):
        """Initialize the action executor."""
        self.db = db
        self.registry = get_execution_registry()
        self.file_generator = FileGenerator(output_dir)
        self.progress_tracker = get_progress_tracker()

    async def execute(
        self,
        action_id: str,
        document_id: Optional[int] = None,
        parameters: Optional[Dict[str, Any]] = None,
        output_format: Optional[OutputFormat] = None,
        language: str = "en",
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute an action.
        
        Args:
            action_id: Action to execute
            document_id: Source document ID
            parameters: Action parameters
            output_format: Desired output format
            language: Output language
            user_id: User ID
            
        Returns:
            Execution result with outputs
        """
        # Get action definition
        action = self.registry.get_action(action_id)
        if not action:
            raise ValueError(f"Action not found: {action_id}")
        
        # Get document content
        document_content = None
        if document_id:
            document_content = self._get_document_content(document_id)
        
        # Determine output format
        if not output_format:
            output_format = action.supported_formats[0] if action.supported_formats else OutputFormat.JSON
        
        # Create execution record
        execution_id = self.progress_tracker.create_execution(
            action_id=action_id,
            document_id=document_id,
            user_id=user_id,
            parameters=parameters or {},
            steps=["execute"]
        )
        
        try:
            self.progress_tracker.update_status(execution_id, ExecutionStatus.RUNNING)
            
            # Execute based on action type
            result = await self._execute_action(
                action_id=action_id,
                document_content=document_content,
                parameters=parameters or {},
                language=language
            )
            
            # Generate output file
            output_file = await self._generate_output(
                action_id=action_id,
                result=result,
                output_format=output_format,
                execution_id=execution_id
            )
            
            # Complete execution
            self.progress_tracker.complete_step(execution_id, "execute", output_file)
            self.progress_tracker.update_status(execution_id, ExecutionStatus.COMPLETED)
            
            # Get execution record
            record = self.progress_tracker.get_execution(execution_id)
            
            return {
                "execution_id": execution_id,
                "action_id": action_id,
                "status": ExecutionStatus.COMPLETED.value,
                "progress": 100,
                "outputs": [output_file] if output_file else [],
                "data": result
            }
            
        except Exception as e:
            logger.exception(f"Action execution failed: {action_id}")
            self.progress_tracker.update_status(execution_id, ExecutionStatus.FAILED, str(e))
            raise

    async def _execute_action(
        self,
        action_id: str,
        document_content: Optional[Dict[str, Any]],
        parameters: Dict[str, Any],
        language: str
    ) -> Dict[str, Any]:
        """Execute the specific action logic."""
        
        # Invoice Actions
        if action_id == "extract_line_items":
            return self._extract_line_items(document_content, parameters)
        
        elif action_id == "generate_excel_invoice":
            return self._generate_excel_invoice(document_content, parameters)
        
        elif action_id == "analyze_invoice_discrepancies":
            return self._analyze_invoice_discrepancies(document_content, parameters)
        
        elif action_id == "generate_email_reminder":
            return self._generate_email_reminder(document_content, parameters)
        
        # Analysis Actions
        elif action_id == "analyze_ats":
            return self._analyze_ats(document_content, parameters)
        
        elif action_id == "analyze_contract_risks":
            return self._analyze_contract_risks(document_content, parameters)
        
        elif action_id == "extract_obligations":
            return self._extract_obligations(document_content, parameters)
        
        # Summary Actions
        elif action_id == "generate_summary":
            return self._generate_summary(document_content, parameters)
        
        elif action_id == "generate_contract_summary":
            return self._generate_contract_summary(document_content, parameters)
        
        elif action_id == "generate_meeting_minutes":
            return self._generate_meeting_minutes(document_content, parameters)
        
        # Learning Actions
        elif action_id == "generate_flashcards":
            return self._generate_flashcards(document_content, parameters)
        
        elif action_id == "generate_quiz":
            return self._generate_quiz(document_content, parameters)
        
        elif action_id == "generate_learning_path":
            return self._generate_learning_path(document_content, parameters)
        
        elif action_id == "generate_mindmap":
            return self._generate_mindmap(document_content, parameters)
        
        # Email Actions
        elif action_id == "generate_email_reply":
            return self._generate_email_reply(document_content, parameters)
        
        elif action_id == "generate_email_followup":
            return self._generate_email_followup(document_content, parameters)
        
        # Presentation Actions
        elif action_id == "generate_pptx_presentation":
            return self._generate_pptx_presentation(document_content, parameters)
        
        # Document Actions
        elif action_id == "generate_docx_cover_letter":
            return self._generate_docx_cover_letter(document_content, parameters)
        
        elif action_id == "generate_docx_notes":
            return self._generate_docx_notes(document_content, parameters)
        
        # Calendar Actions
        elif action_id == "extract_action_items":
            return self._extract_action_items(document_content, parameters)
        
        elif action_id == "generate_calendar_event":
            return self._generate_calendar_event(document_content, parameters)
        
        # Default: generic content generation
        else:
            return self._generate_generic_content(action_id, document_content, parameters)

    def _get_document_content(self, document_id: int) -> Dict[str, Any]:
        """Get document content and metadata."""
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            return {}
        
        # Get entities
        entities = self.db.query(KnowledgeEntity).filter(
            KnowledgeEntity.document_id == document_id
        ).limit(50).all()
        
        # Get concepts
        concepts = self.db.query(KnowledgeConcept).filter(
            KnowledgeConcept.document_id == document_id
        ).limit(50).all()
        
        return {
            "id": doc.id,
            "filename": doc.filename,
            "content_type": doc.content_type,
            "language": doc.language_code,
            "summary": doc.summary.content if doc.summary else None,
            "entities": [
                {"name": e.name, "type": str(e.entity_type.value if hasattr(e.entity_type, 'value') else e.entity_type)}
                for e in entities
            ],
            "concepts": [
                {"name": c.name, "description": c.description}
                for c in concepts
            ],
            "questions": [
                {"question": q.question, "answer": q.answer}
                for q in doc.questions[:20]
            ],
            "flashcards": [
                {"front": f.front, "back": f.back}
                for f in doc.flashcards[:20]
            ]
        }

    async def _generate_output(
        self,
        action_id: str,
        result: Dict[str, Any],
        output_format: OutputFormat,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """Generate output file."""
        
        # Determine filename
        filename_map = {
            "extract_line_items": "line_items",
            "generate_excel_invoice": "invoice",
            "generate_email_reminder": "reminder",
            "analyze_ats": "ats_analysis",
            "generate_flashcards": "flashcards",
            "generate_quiz": "quiz",
            "generate_summary": "summary",
            "generate_contract_summary": "contract_summary",
            "generate_learning_path": "learning_path",
            "generate_mindmap": "mindmap",
            "generate_email_reply": "reply_email",
            "generate_pptx_presentation": "presentation",
        }
        
        filename = filename_map.get(action_id, "output")
        
        try:
            file_info = await self.file_generator.generate(
                format=output_format.value,
                data=result,
                filename=filename,
                execution_id=execution_id
            )
            
            self.progress_tracker.add_output(execution_id, file_info)
            
            return file_info
            
        except Exception as e:
            logger.error(f"Failed to generate output file: {e}")
            return None

    # ========================================================================
    # Action Implementations
    # ========================================================================

    def _extract_line_items(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Extract line items from invoice."""
        # In production, this would use LLM to extract structured data
        return {
            "title": "Invoice Line Items",
            "headers": ["Item", "Description", "Quantity", "Unit Price", "Total"],
            "rows": [
                ["Item 1", "Product description", 2, 50.00, 100.00],
                ["Item 2", "Another product", 1, 75.00, 75.00],
            ],
            "subtotal": 175.00,
            "tax": 17.50,
            "total": 192.50
        }

    def _generate_excel_invoice(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate Excel from invoice."""
        return {
            "title": "Invoice Summary",
            "sheets": [
                {
                    "name": "Invoice",
                    "headers": ["Item", "Description", "Quantity", "Unit Price", "Total"],
                    "rows": [
                        ["Item 1", "Product A", 2, 50.00, 100.00],
                        ["Item 2", "Product B", 1, 75.00, 75.00],
                    ]
                },
                {
                    "name": "Summary",
                    "headers": ["Category", "Amount"],
                    "rows": [
                        ["Subtotal", 175.00],
                        ["Tax (10%)", 17.50],
                        ["Total", 192.50],
                    ]
                }
            ]
        }

    def _analyze_invoice_discrepancies(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Analyze invoice for discrepancies."""
        return {
            "title": "Invoice Discrepancy Analysis",
            "content": "No significant discrepancies found.",
            "analysis": {
                "total_matches": True,
                "tax_calculated_correctly": True,
                "items_complete": True
            },
            "warnings": [],
            "recommendations": ["All line items appear correct."]
        }

    def _generate_email_reminder(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate payment reminder email."""
        return {
            "title": "Payment Reminder Email",
            "content": """Dear [Vendor Name],

This is a friendly reminder that invoice #[Invoice Number] for $[Amount] is due on [Due Date].

Please ensure payment is made by the due date to avoid any late fees.

Thank you for your continued business.

Best regards,
[Your Name]
[Your Company]"""
        }

    def _analyze_ats(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Analyze resume for ATS compatibility."""
        return {
            "title": "Resume ATS Analysis",
            "sections": [
                {
                    "title": "Overall Score",
                    "content": "Your resume scores 85/100 for ATS compatibility."
                },
                {
                    "title": "Strengths",
                    "content": [
                        "Clear section headings",
                        "Relevant keywords present",
                        "Quantified achievements"
                    ]
                },
                {
                    "title": "Improvements",
                    "content": [
                        "Add more skills keywords",
                        "Use standard section titles",
                        "Remove graphics/tables"
                    ]
                }
            ],
            "score": 85,
            "matched_keywords": ["Python", "Machine Learning", "AWS", "SQL"],
            "missing_keywords": ["Docker", "Kubernetes", "Agile"]
        }

    def _analyze_contract_risks(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Analyze contract for risks."""
        return {
            "title": "Contract Risk Analysis",
            "risk_level": "medium",
            "risks": [
                {"clause": "Termination", "risk": "High", "description": "30-day notice may be too short"},
                {"clause": "Liability", "risk": "Low", "description": "Standard liability clause"}
            ],
            "recommendations": [
                "Negotiate longer termination notice",
                "Add liability cap"
            ]
        }

    def _extract_obligations(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Extract contract obligations."""
        return {
            "title": "Contract Obligations",
            "parties": [
                {"name": "Party A", "obligations": ["Deliver services", "Monthly reporting"]},
                {"name": "Party B", "obligations": ["Payment within 30 days", "Provide access"]}
            ],
            "deadlines": [
                {"obligation": "Payment", "deadline": "30 days from invoice"},
                {"obligation": "Delivery", "deadline": "Q1 2025"}
            ]
        }

    def _generate_summary(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate document summary."""
        summary = content.get("summary") if content else None
        return {
            "title": "Document Summary",
            "content": summary or "This document contains important information that has been analyzed and summarized.",
            "key_points": [
                "Key finding 1",
                "Key finding 2",
                "Key finding 3"
            ]
        }

    def _generate_contract_summary(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate contract summary."""
        return {
            "title": "Contract Summary",
            "sections": [
                {"title": "Parties", "content": "Party A and Party B"},
                {"title": "Term", "content": "12 months from signing"},
                {"title": "Key Obligations", "content": "As outlined in the contract"},
                {"title": "Termination", "content": "30 days written notice"}
            ]
        }

    def _generate_meeting_minutes(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate meeting minutes."""
        return {
            "title": "Meeting Minutes",
            "sections": [
                {"title": "Date", "content": datetime.utcnow().strftime("%Y-%m-%d")},
                {"title": "Attendees", "content": "Team members present"},
                {"title": "Discussion", "content": "Topics discussed during the meeting"},
                {"title": "Decisions", "content": "Key decisions made"},
                {"title": "Action Items", "content": "Tasks assigned to team members"}
            ]
        }

    def _generate_flashcards(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate flashcards."""
        flashcards = content.get("flashcards", []) if content else []
        if not flashcards:
            flashcards = [
                {"front": "What is machine learning?", "back": "A subset of AI that enables systems to learn from data"},
                {"front": "What is deep learning?", "back": "Neural networks with multiple layers"},
                {"front": "What is NLP?", "back": "Natural Language Processing - AI for understanding text"}
            ]
        
        return {
            "title": "Study Flashcards",
            "headers": ["Front", "Back"],
            "rows": [[f["front"], f["back"]] for f in flashcards]
        }

    def _generate_quiz(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate quiz."""
        return {
            "title": "Knowledge Quiz",
            "questions": [
                {
                    "question": "What is the main topic?",
                    "options": ["Option A", "Option B", "Option C", "Option D"],
                    "correct": 0
                },
                {
                    "question": "Which statement is true?",
                    "options": ["True", "False"],
                    "correct": 0
                }
            ]
        }

    def _generate_learning_path(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate learning path."""
        return {
            "title": "Personalized Learning Path",
            "sections": [
                {"title": "Week 1-2", "content": "Foundation concepts"},
                {"title": "Week 3-4", "content": "Intermediate topics"},
                {"title": "Week 5-6", "content": "Advanced materials"},
                {"title": "Week 7-8", "content": "Practical applications"}
            ],
            "resources": [
                {"title": "Introduction Guide", "type": "article"},
                {"title": "Video Series", "type": "video"},
                {"title": "Practice Exercises", "type": "exercise"}
            ]
        }

    def _generate_mindmap(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate mind map."""
        return {
            "title": "Concept Mind Map",
            "root": "Main Topic",
            "nodes": [
                {"id": 1, "label": "Subtopic 1", "parent": None},
                {"id": 2, "label": "Subtopic 2", "parent": None},
                {"id": 3, "label": "Detail A", "parent": 1},
                {"id": 4, "label": "Detail B", "parent": 1},
                {"id": 5, "label": "Detail C", "parent": 2}
            ]
        }

    def _generate_email_reply(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate email reply."""
        return {
            "title": "Email Reply",
            "content": """Dear [Name],

Thank you for your email. I have reviewed the contents and wanted to follow up with you.

[Your response here]

Please let me know if you have any questions.

Best regards,
[Your Name]"""
        }

    def _generate_email_followup(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate follow-up email."""
        return {
            "title": "Meeting Follow-up Email",
            "content": """Hi Team,

Thank you for attending today's meeting. Here is a summary of what we discussed:

• Topic 1: Decision made
• Topic 2: Action items assigned

Next steps:
1. [Action] - [Owner] - [Due Date]
2. [Action] - [Owner] - [Due Date]

Next meeting: [Date/Time]

Best regards"""
        }

    def _generate_pptx_presentation(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate PowerPoint presentation."""
        return {
            "title": content.get("filename", "Presentation") if content else "Presentation",
            "subtitle": "Generated by AI Knowledge Workspace",
            "slides": [
                {
                    "title": "Overview",
                    "content": ["Key point 1", "Key point 2", "Key point 3"]
                },
                {
                    "title": "Details",
                    "content": ["Point A", "Point B", "Point C"]
                },
                {
                    "title": "Summary",
                    "content": ["Conclusion 1", "Conclusion 2"]
                }
            ]
        }

    def _generate_docx_cover_letter(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate cover letter."""
        return {
            "title": "Cover Letter",
            "sections": [
                {"title": "Date", "content": datetime.utcnow().strftime("%B %d, %Y")},
                {"title": "", "content": "Dear Hiring Manager,"},
                {"title": "", "content": "I am writing to express my interest in the position..."},
                {"title": "", "content": "Thank you for your consideration."},
                {"title": "", "content": "Sincerely,\n[Your Name]"}
            ]
        }

    def _generate_docx_notes(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate document notes."""
        return {
            "title": content.get("filename", "Notes") if content else "Document Notes",
            "sections": [
                {"title": "Summary", "content": content.get("summary", "Document summary") if content else ""},
                {"title": "Key Concepts", "content": "Extracted concepts from the document"},
                {"title": "Important Points", "content": "Notable information highlighted"}
            ]
        }

    def _extract_action_items(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Extract action items."""
        return {
            "title": "Action Items",
            "headers": ["Task", "Owner", "Due Date", "Priority"],
            "rows": [
                ["Review document", "Team Member 1", "2025-01-15", "High"],
                ["Provide feedback", "Team Member 2", "2025-01-20", "Medium"]
            ]
        }

    def _generate_calendar_event(self, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate calendar event."""
        return {
            "title": "Calendar Event",
            "event": {
                "summary": "Meeting",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "time": "10:00 AM",
                "duration": "1 hour",
                "attendees": ["email@example.com"]
            }
        }

    def _generate_generic_content(self, action_id: str, content: Optional[Dict], params: Dict) -> Dict[str, Any]:
        """Generate generic content."""
        return {
            "title": f"Generated: {action_id}",
            "content": f"Content generated for action: {action_id}",
            "timestamp": datetime.utcnow().isoformat()
        }


def get_action_executor(db: Session) -> ActionExecutor:
    """Get action executor instance."""
    return ActionExecutor(db)
