"""
Knowledge Interaction Module

Services for AI Notebook, Collections, and user interactions.
"""

from src.knowledge.interaction.notebook_service import NotebookService
from src.knowledge.interaction.collection_service import CollectionService
from src.knowledge.interaction.explorer_service import KnowledgeExplorerService
from src.knowledge.interaction.search_service import SemanticSearchService
from src.knowledge.interaction.activity_service import RecentActivityService

__all__ = [
    "NotebookService",
    "CollectionService",
    "KnowledgeExplorerService",
    "SemanticSearchService",
    "RecentActivityService",
]
