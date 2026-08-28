"""
Notebook Service

Manages AI Notebook for user notes and AI responses.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from src.knowledge.interaction_models import KnowledgeNote, NoteType
from src.core.logging import logger


class NotebookService:
    """
    Service for managing AI Notebook notes.
    
    Notes can be:
    - User-created notes
    - AI-generated responses
    - Derived from knowledge (summaries, concepts, etc.)
    """
    
    def __init__(self, db: Session):
        """Initialize the notebook service."""
        self.db = db
    
    def create_note(
        self,
        user_id: int,
        content: str,
        title: Optional[str] = None,
        note_type: str = NoteType.USER.value,
        workspace_id: Optional[int] = None,
        source_document_id: Optional[int] = None,
        source_concept_id: Optional[int] = None,
        source_question_id: Optional[int] = None,
        source_flashcard_id: Optional[int] = None,
        citations: Optional[List[Dict]] = None,
        ai_generated: bool = False,
        ai_model: Optional[str] = None,
        ai_provider: Optional[str] = None,
        format_type: str = "markdown"
    ) -> KnowledgeNote:
        """
        Create a new note.
        
        Args:
            user_id: User ID
            content: Note content (markdown)
            title: Optional title
            note_type: Type of note
            workspace_id: Optional workspace
            source_document_id: Source document if derived
            source_concept_id: Source concept if derived
            source_question_id: Source question if derived
            source_flashcard_id: Source flashcard if derived
            citations: Linked knowledge citations
            ai_generated: Whether AI generated
            ai_model: AI model used
            ai_provider: AI provider used
            format_type: Content format
            
        Returns:
            Created note
        """
        note = KnowledgeNote(
            user_id=user_id,
            title=title,
            content=content,
            note_type=note_type,
            workspace_id=workspace_id,
            source_document_id=source_document_id,
            source_concept_id=source_concept_id,
            source_question_id=source_question_id,
            source_flashcard_id=source_flashcard_id,
            citations=citations,
            ai_generated=ai_generated,
            ai_model=ai_model,
            ai_provider=ai_provider,
            format_type=format_type,
        )
        
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        
        logger.info(f"Created note {note.id} for user {user_id}")
        
        return note
    
    def get_note(self, note_id: int, user_id: int) -> Optional[KnowledgeNote]:
        """Get a note by ID."""
        return self.db.query(KnowledgeNote).filter(
            KnowledgeNote.id == note_id,
            KnowledgeNote.user_id == user_id
        ).first()
    
    def update_note(
        self,
        note_id: int,
        user_id: int,
        content: Optional[str] = None,
        title: Optional[str] = None,
        citations: Optional[List[Dict]] = None
    ) -> Optional[KnowledgeNote]:
        """Update a note."""
        note = self.get_note(note_id, user_id)
        
        if not note:
            return None
        
        if content is not None:
            note.content = content
        
        if title is not None:
            note.title = title
        
        if citations is not None:
            note.citations = citations
        
        note.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(note)
        
        return note
    
    def delete_note(self, note_id: int, user_id: int) -> bool:
        """Delete a note."""
        note = self.get_note(note_id, user_id)
        
        if not note:
            return False
        
        self.db.delete(note)
        self.db.commit()
        
        return True
    
    def pin_note(self, note_id: int, user_id: int, pinned: bool = True) -> Optional[KnowledgeNote]:
        """Pin or unpin a note."""
        note = self.get_note(note_id, user_id)
        
        if not note:
            return None
        
        note.is_pinned = pinned
        note.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(note)
        
        return note
    
    def get_notes(
        self,
        user_id: int,
        workspace_id: Optional[int] = None,
        note_type: Optional[str] = None,
        pinned_only: bool = False,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeNote]:
        """
        Get notes for a user.
        
        Args:
            user_id: User ID
            workspace_id: Optional workspace filter
            note_type: Optional type filter
            pinned_only: Only pinned notes
            include_archived: Include archived notes
            limit: Maximum results
            offset: Result offset
            
        Returns:
            List of notes
        """
        query = self.db.query(KnowledgeNote).filter(
            KnowledgeNote.user_id == user_id
        )
        
        if workspace_id:
            query = query.filter(KnowledgeNote.workspace_id == workspace_id)
        
        if note_type:
            query = query.filter(KnowledgeNote.note_type == note_type)
        
        if pinned_only:
            query = query.filter(KnowledgeNote.is_pinned == True)
        
        if not include_archived:
            query = query.filter(KnowledgeNote.is_archived == False)
        
        return query.order_by(
            KnowledgeNote.is_pinned.desc(),
            KnowledgeNote.updated_at.desc()
        ).limit(limit).offset(offset).all()
    
    def get_recent_notes(
        self,
        user_id: int,
        limit: int = 10
    ) -> List[KnowledgeNote]:
        """Get recent notes."""
        return self.db.query(KnowledgeNote).filter(
            KnowledgeNote.user_id == user_id,
            KnowledgeNote.is_archived == False
        ).order_by(
            KnowledgeNote.updated_at.desc()
        ).limit(limit).all()
    
    def search_notes(
        self,
        user_id: int,
        query: str,
        limit: int = 20
    ) -> List[KnowledgeNote]:
        """Search notes by content."""
        search_pattern = f"%{query}%"
        
        return self.db.query(KnowledgeNote).filter(
            KnowledgeNote.user_id == user_id,
            or_(
                KnowledgeNote.title.ilike(search_pattern),
                KnowledgeNote.content.ilike(search_pattern)
            )
        ).order_by(
            KnowledgeNote.updated_at.desc()
        ).limit(limit).all()
    
    def archive_note(self, note_id: int, user_id: int) -> Optional[KnowledgeNote]:
        """Archive a note."""
        note = self.get_note(note_id, user_id)
        
        if not note:
            return None
        
        note.is_archived = True
        note.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(note)
        
        return note
    
    def convert_to_note(
        self,
        user_id: int,
        content: str,
        source_type: str,
        source_id: int,
        source_data: Dict[str, Any]
    ) -> KnowledgeNote:
        """
        Convert AI response or knowledge item to a note.
        
        Args:
            user_id: User ID
            content: Note content
            source_type: Type of source (ai_response, flashcard, question, etc.)
            source_id: Source ID
            source_data: Additional source data
            
        Returns:
            Created note
        """
        note_type_map = {
            "ai_response": NoteType.AI_RESPONSE.value,
            "flashcard": NoteType.CONCEPT.value,
            "question": NoteType.CONCEPT.value,
            "summary": NoteType.SUMMARY.value,
        }
        
        note_type = note_type_map.get(source_type, NoteType.USER.value)
        
        return self.create_note(
            user_id=user_id,
            content=content,
            title=source_data.get("title"),
            note_type=note_type,
            source_flashcard_id=source_id if source_type == "flashcard" else None,
            source_question_id=source_id if source_type == "question" else None,
            ai_generated=True,
            citations=source_data.get("citations")
        )
