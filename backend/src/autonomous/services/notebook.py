"""
Intelligent Notebook Service

Manages intelligent notebooks with autonomous knowledge organization.
"""

import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import func

from src.autonomous.models import (
    IntelligentNotebook,
    LearningPath,
    KnowledgeNode,
    KnowledgeInsight,
)
from src.models.document import Document
from src.knowledge.models import KnowledgeConcept, KnowledgeEntity, GeneratedQuestion, KnowledgeFlashcard
from src.core.logging import logger


class IntelligentNotebookService:
    """
    Service for intelligent notebooks.
    
    Features:
    - Auto-generated summaries
    - Auto-generated timelines
    - Concept maps
    - Entity graphs
    - Topic clustering
    - Important quotations
    - Questions
    - Flashcards
    - Learning paths
    """
    
    def __init__(self, db: Session):
        """Initialize the notebook service."""
        self.db = db
    
    def create_notebook(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        document_ids: Optional[List[int]] = None
    ) -> IntelligentNotebook:
        """
        Create an intelligent notebook.
        
        Args:
            user_id: User ID
            title: Notebook title
            description: Optional description
            document_ids: Initial documents to include
            
        Returns:
            Created notebook
        """
        notebook_id = f"notebook_{uuid.uuid4().hex[:12]}"
        
        notebook = IntelligentNotebook(
            notebook_id=notebook_id,
            title=title,
            description=description,
            user_id=user_id,
            document_ids=document_ids or [],
            document_count=len(document_ids) if document_ids else 0
        )
        
        self.db.add(notebook)
        self.db.commit()
        self.db.refresh(notebook)
        
        logger.info(f"Created intelligent notebook: {notebook_id}")
        
        return notebook
    
    def update_notebook_content(
        self,
        notebook_id: str,
        auto_summary: Optional[str] = None,
        auto_timeline: Optional[List[Dict]] = None,
        auto_concept_map: Optional[Dict] = None,
        auto_quotations: Optional[List[Dict]] = None
    ) -> IntelligentNotebook:
        """Update notebook auto-generated content."""
        notebook = self.get_notebook(notebook_id)
        
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")
        
        if auto_summary is not None:
            notebook.auto_summary = auto_summary
        
        if auto_timeline is not None:
            notebook.auto_timeline = auto_timeline
        
        if auto_concept_map is not None:
            notebook.auto_concept_map = auto_concept_map
        
        if auto_quotations is not None:
            notebook.auto_quotations = auto_quotations
        
        notebook.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(notebook)
        
        return notebook
    
    def get_notebook(self, notebook_id: str) -> Optional[IntelligentNotebook]:
        """Get notebook by ID."""
        return self.db.query(IntelligentNotebook).filter(
            IntelligentNotebook.notebook_id == notebook_id
        ).first()
    
    def get_user_notebooks(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[IntelligentNotebook]:
        """Get user's notebooks."""
        return self.db.query(IntelligentNotebook).filter(
            IntelligentNotebook.user_id == user_id
        ).order_by(
            IntelligentNotebook.updated_at.desc()
        ).limit(limit).all()
    
    def add_document(
        self,
        notebook_id: str,
        document_id: int
    ) -> IntelligentNotebook:
        """Add document to notebook."""
        notebook = self.get_notebook(notebook_id)
        
        if not notebook:
            raise ValueError(f"Notebook {notebook_id} not found")
        
        # Add to document list
        doc_ids = list(notebook.document_ids or [])
        if document_id not in doc_ids:
            doc_ids.append(document_id)
            notebook.document_ids = doc_ids
            notebook.document_count = len(doc_ids)
            notebook.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(notebook)
        
        return notebook
    
    def generate_notebook_insights(
        self,
        notebook_id: str
    ) -> Dict[str, Any]:
        """Generate comprehensive insights for notebook."""
        notebook = self.get_notebook(notebook_id)
        
        if not notebook:
            return {}
        
        # Get all documents
        doc_ids = notebook.document_ids or []
        
        # Get concepts
        concepts = self.db.query(KnowledgeConcept).filter(
            KnowledgeConcept.document_id.in_(doc_ids)
        ).order_by(
            KnowledgeConcept.importance.desc()
        ).limit(50).all()
        
        # Get entities
        entities = self.db.query(KnowledgeEntity).filter(
            KnowledgeEntity.document_id.in_(doc_ids)
        ).order_by(
            KnowledgeEntity.mentions.desc()
        ).limit(50).all()
        
        # Get questions
        questions = self.db.query(GeneratedQuestion).filter(
            GeneratedQuestion.document_id.in_(doc_ids)
        ).all()
        
        # Get flashcards
        flashcards = self.db.query(KnowledgeFlashcard).filter(
            KnowledgeFlashcard.document_id.in_(doc_ids)
        ).all()
        
        # Calculate statistics
        insights = {
            "concept_count": len(concepts),
            "entity_count": len(entities),
            "question_count": len(questions),
            "flashcard_count": len(flashcards),
            "top_concepts": [
                {"name": c.name, "importance": c.importance, "difficulty": c.difficulty}
                for c in concepts[:10]
            ],
            "top_entities": [
                {"name": e.name, "type": e.entity_type, "mentions": e.mentions}
                for e in entities[:10]
            ],
            "question_types": self._count_by_type(questions, "question_type"),
            "difficulty_distribution": self._count_by_type(questions, "difficulty")
        }
        
        return insights
    
    def _count_by_type(self, items: List, attr: str) -> Dict[str, int]:
        """Count items by attribute."""
        counts = {}
        for item in items:
            value = getattr(item, attr, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
    
    def generate_timeline(
        self,
        notebook_id: str
    ) -> List[Dict[str, Any]]:
        """Generate timeline from documents."""
        notebook = self.get_notebook(notebook_id)
        
        if not notebook:
            return []
        
        doc_ids = notebook.document_ids or []
        
        # Get documents with dates
        docs = self.db.query(Document).filter(
            Document.id.in_(doc_ids)
        ).order_by(Document.created_at).all()
        
        timeline = []
        for doc in docs:
            timeline.append({
                "date": doc.created_at.isoformat() if doc.created_at else None,
                "title": doc.title,
                "document_id": doc.id,
                "type": "document"
            })
        
        # Update notebook
        notebook.auto_timeline = timeline
        notebook.updated_at = datetime.utcnow()
        self.db.commit()
        
        return timeline
    
    def generate_concept_map(
        self,
        notebook_id: str
    ) -> Dict[str, Any]:
        """Generate concept map from notebook."""
        notebook = self.get_notebook(notebook_id)
        
        if not notebook:
            return {}
        
        doc_ids = notebook.document_ids or []
        
        # Get concepts with relationships
        concepts = self.db.query(KnowledgeConcept).filter(
            KnowledgeConcept.document_id.in_(doc_ids)
        ).all()
        
        nodes = []
        edges = []
        
        for concept in concepts:
            nodes.append({
                "id": concept.id,
                "name": concept.name,
                "description": concept.description,
                "importance": concept.importance,
                "difficulty": concept.difficulty
            })
            
            # Add edges for related concepts
            related = concept.related_concepts or []
            for rel_name in related:
                # Find target concept
                target = self.db.query(KnowledgeConcept).filter(
                    KnowledgeConcept.name == rel_name
                ).first()
                
                if target:
                    edges.append({
                        "source": concept.id,
                        "target": target.id,
                        "type": "related_to"
                    })
        
        return {
            "nodes": nodes,
            "edges": edges
        }


class LearningPathService:
    """
    Service for learning paths.
    
    Features:
    - Automatic path generation
    - Prerequisite tracking
    - Progress tracking
    - Recommendations
    """
    
    def __init__(self, db: Session):
        """Initialize the learning path service."""
        self.db = db
    
    def create_learning_path(
        self,
        user_id: int,
        topic: str,
        title: Optional[str] = None,
        document_ids: Optional[List[int]] = None
    ) -> LearningPath:
        """Create a learning path for a topic."""
        path_id = f"path_{uuid.uuid4().hex[:12]}"
        
        path = LearningPath(
            path_id=path_id,
            title=title or f"Learning Path: {topic}",
            topic=topic,
            user_id=user_id,
            recommended_documents=document_ids or [],
            total_estimated_hours=len(document_ids) * 2 if document_ids else 10
        )
        
        self.db.add(path)
        self.db.commit()
        self.db.refresh(path)
        
        return path
    
    def generate_steps(
        self,
        path_id: str
    ) -> LearningPath:
        """Generate learning steps for a path."""
        path = self.get_path(path_id)
        
        if not path:
            raise ValueError(f"Learning path {path_id} not found")
        
        # Get concepts from documents
        doc_ids = path.recommended_documents or []
        
        concepts = self.db.query(KnowledgeConcept).filter(
            KnowledgeConcept.document_id.in_(doc_ids)
        ).order_by(
            KnowledgeConcept.difficulty
        ).all()
        
        # Generate steps based on difficulty
        steps = []
        current_difficulty = None
        
        for concept in concepts:
            if concept.difficulty != current_difficulty:
                current_difficulty = concept.difficulty
                step = {
                    "step": len(steps) + 1,
                    "title": f"{current_difficulty.title()} Level",
                    "description": f"Learn {current_difficulty} concepts",
                    "concepts": [],
                    "estimated_time_minutes": 30
                }
                steps.append(step)
            
            # Add concept to current step
            if steps:
                steps[-1]["concepts"].append({
                    "id": concept.id,
                    "name": concept.name,
                    "difficulty": concept.difficulty
                })
        
        path.steps = steps
        path.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(path)
        
        return path
    
    def get_path(self, path_id: str) -> Optional[LearningPath]:
        """Get learning path by ID."""
        return self.db.query(LearningPath).filter(
            LearningPath.path_id == path_id
        ).first()
    
    def update_progress(
        self,
        path_id: str,
        completed_step: int
    ) -> LearningPath:
        """Update learning path progress."""
        path = self.get_path(path_id)
        
        if not path:
            raise ValueError(f"Learning path {path_id} not found")
        
        # Add completed step
        completed = list(path.completed_steps or [])
        if completed_step not in completed:
            completed.append(completed_step)
            path.completed_steps = completed
        
        # Update current step
        path.current_step = completed_step + 1
        
        # Calculate completion percentage
        total_steps = len(path.steps or [])
        if total_steps > 0:
            path.completion_percentage = (len(completed) / total_steps) * 100
        
        path.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(path)
        
        return path


class InsightService:
    """
    Service for knowledge insights.
    
    Features:
    - Important topics
    - Connected concepts
    - Knowledge gaps
    - Learning progress
    """
    
    def __init__(self, db: Session):
        """Initialize the insight service."""
        self.db = db
    
    def generate_insights(
        self,
        user_id: int
    ) -> List[KnowledgeInsight]:
        """Generate comprehensive insights for user."""
        insights = []
        
        # Get all user nodes
        nodes = self.db.query(KnowledgeNode).filter(
            KnowledgeNode.user_id == user_id
        ).all()
        
        # Important topics
        important = [n for n in nodes if n.importance_score > 0.7]
        if important:
            insight = self._create_insight(
                user_id=user_id,
                insight_type="important_topics",
                title="Important Topics",
                description=f"Found {len(important)} high-importance topics in your workspace",
                related_nodes=important[:10],
                importance_score=0.9
            )
            insights.append(insight)
        
        # Connected concepts
        connected = [n for n in nodes if n.out_degree + n.in_degree > 5]
        if connected:
            insight = self._create_insight(
                user_id=user_id,
                insight_type="connected_concepts",
                title="Most Connected Concepts",
                description=f"Found {len(connected)} highly connected concepts",
                related_nodes=connected[:10],
                importance_score=0.8
            )
            insights.append(insight)
        
        # Knowledge gaps (nodes with low importance but many connections)
        gaps = [n for n in nodes if n.importance_score < 0.3 and n.out_degree + n.in_degree > 3]
        if gaps:
            insight = self._create_insight(
                user_id=user_id,
                insight_type="knowledge_gaps",
                title="Potential Knowledge Gaps",
                description=f"Found {len(gaps)} concepts that may need more study",
                related_nodes=gaps[:10],
                importance_score=0.7
            )
            insights.append(insight)
        
        return insights
    
    def _create_insight(
        self,
        user_id: int,
        insight_type: str,
        title: str,
        description: str,
        related_nodes: List[KnowledgeNode],
        importance_score: float = 0.5
    ) -> KnowledgeInsight:
        """Create an insight."""
        insight_id = f"insight_{uuid.uuid4().hex[:12]}"
        
        insight = KnowledgeInsight(
            insight_id=insight_id,
            user_id=user_id,
            insight_type=insight_type,
            title=title,
            description=description,
            related_node_ids=[n.id for n in related_nodes],
            importance_score=importance_score,
            confidence_score=0.8,
            generated_by="system",
            generation_method="auto_analysis"
        )
        
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        
        return insight


# Import for service
from src.autonomous.models import KnowledgeNode
