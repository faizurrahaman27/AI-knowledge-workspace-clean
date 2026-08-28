"""
Collection Service

Manages knowledge collections for organizing documents, notes, flashcards, etc.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.knowledge.interaction_models import KnowledgeCollection, CollectionItem, CollectionType
from src.core.logging import logger


class CollectionService:
    """
    Service for managing knowledge collections.
    
    Collections can contain:
    - Documents
    - Notes
    - Flashcards
    - Questions
    - Concepts
    - Summaries
    """
    
    def __init__(self, db: Session):
        """Initialize the collection service."""
        self.db = db
    
    def create_collection(
        self,
        user_id: int,
        name: str,
        description: Optional[str] = None,
        collection_type: str = CollectionType.FOLDER.value,
        parent_id: Optional[int] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> KnowledgeCollection:
        """
        Create a new collection.
        
        Args:
            user_id: User ID
            name: Collection name
            description: Optional description
            collection_type: Type of collection
            parent_id: Parent collection for hierarchy
            color: Hex color
            icon: Emoji or icon name
            tags: Collection tags
            
        Returns:
            Created collection
        """
        collection = KnowledgeCollection(
            user_id=user_id,
            name=name,
            description=description,
            collection_type=collection_type,
            parent_id=parent_id,
            color=color,
            icon=icon,
            tags=tags
        )
        
        self.db.add(collection)
        self.db.commit()
        self.db.refresh(collection)
        
        logger.info(f"Created collection {collection.id}: {name}")
        
        return collection
    
    def get_collection(self, collection_id: int, user_id: int) -> Optional[KnowledgeCollection]:
        """Get a collection by ID."""
        return self.db.query(KnowledgeCollection).filter(
            KnowledgeCollection.id == collection_id,
            KnowledgeCollection.user_id == user_id
        ).first()
    
    def update_collection(
        self,
        collection_id: int,
        user_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Optional[KnowledgeCollection]:
        """Update a collection."""
        collection = self.get_collection(collection_id, user_id)
        
        if not collection:
            return None
        
        if name is not None:
            collection.name = name
        
        if description is not None:
            collection.description = description
        
        if color is not None:
            collection.color = color
        
        if icon is not None:
            collection.icon = icon
        
        if tags is not None:
            collection.tags = tags
        
        collection.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(collection)
        
        return collection
    
    def delete_collection(self, collection_id: int, user_id: int) -> bool:
        """Delete a collection and its items."""
        collection = self.get_collection(collection_id, user_id)
        
        if not collection:
            return False
        
        # Cascade delete handles items
        self.db.delete(collection)
        self.db.commit()
        
        return True
    
    def get_collections(
        self,
        user_id: int,
        parent_id: Optional[int] = None,
        collection_type: Optional[str] = None,
        favorites_only: bool = False,
        limit: int = 50,
        offset: int = 0
    ) -> List[KnowledgeCollection]:
        """Get collections for a user."""
        query = self.db.query(KnowledgeCollection).filter(
            KnowledgeCollection.user_id == user_id
        )
        
        if parent_id is not None:
            query = query.filter(KnowledgeCollection.parent_id == parent_id)
        elif not favorites_only:
            # Root collections (no parent)
            query = query.filter(KnowledgeCollection.parent_id == None)
        
        if collection_type:
            query = query.filter(KnowledgeCollection.collection_type == collection_type)
        
        if favorites_only:
            query = query.filter(KnowledgeCollection.is_favorite == True)
        
        return query.order_by(
            KnowledgeCollection.name
        ).limit(limit).offset(offset).all()
    
    def get_collection_tree(
        self,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get collection tree structure.
        
        Returns nested structure of collections.
        """
        collections = self.db.query(KnowledgeCollection).filter(
            KnowledgeCollection.user_id == user_id
        ).all()
        
        # Build tree
        root_collections = []
        collection_map = {}
        
        for collection in collections:
            collection_map[collection.id] = {
                "id": collection.id,
                "name": collection.name,
                "type": collection.collection_type,
                "color": collection.color,
                "icon": collection.icon,
                "item_count": len(collection.items),
                "children": []
            }
        
        for collection in collections:
            if collection.parent_id:
                parent = collection_map.get(collection.parent_id)
                if parent:
                    parent["children"].append(collection_map[collection.id])
            else:
                root_collections.append(collection_map[collection.id])
        
        return root_collections
    
    def add_item_to_collection(
        self,
        collection_id: int,
        user_id: int,
        item_type: str,
        item_id: int,
        notes: Optional[str] = None
    ) -> Optional[CollectionItem]:
        """Add an item to a collection."""
        # Verify collection ownership
        collection = self.get_collection(collection_id, user_id)
        if not collection:
            return None
        
        # Check if item already in collection
        existing = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.item_type == item_type,
            CollectionItem.item_id == item_id
        ).first()
        
        if existing:
            return existing
        
        # Get max order
        max_order = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id
        ).count()
        
        item = CollectionItem(
            collection_id=collection_id,
            item_type=item_type,
            item_id=item_id,
            order_index=max_order,
            notes=notes
        )
        
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        
        logger.info(f"Added {item_type}:{item_id} to collection {collection_id}")
        
        return item
    
    def remove_item_from_collection(
        self,
        collection_id: int,
        item_type: str,
        item_id: int,
        user_id: int
    ) -> bool:
        """Remove an item from a collection."""
        # Verify collection ownership
        collection = self.get_collection(collection_id, user_id)
        if not collection:
            return False
        
        item = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id,
            CollectionItem.item_type == item_type,
            CollectionItem.item_id == item_id
        ).first()
        
        if not item:
            return False
        
        self.db.delete(item)
        self.db.commit()
        
        return True
    
    def get_collection_items(
        self,
        collection_id: int,
        user_id: int,
        item_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[CollectionItem]:
        """Get items in a collection."""
        # Verify collection ownership
        collection = self.get_collection(collection_id, user_id)
        if not collection:
            return []
        
        query = self.db.query(CollectionItem).filter(
            CollectionItem.collection_id == collection_id
        )
        
        if item_type:
            query = query.filter(CollectionItem.item_type == item_type)
        
        return query.order_by(
            CollectionItem.order_index
        ).limit(limit).offset(offset).all()
    
    def toggle_favorite(
        self,
        collection_id: int,
        user_id: int
    ) -> Optional[KnowledgeCollection]:
        """Toggle favorite status."""
        collection = self.get_collection(collection_id, user_id)
        
        if not collection:
            return None
        
        collection.is_favorite = not collection.is_favorite
        collection.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(collection)
        
        return collection
    
    def get_item_collections(
        self,
        user_id: int,
        item_type: str,
        item_id: int
    ) -> List[KnowledgeCollection]:
        """Get all collections containing a specific item."""
        # Get collection IDs for this item
        item_collections = self.db.query(CollectionItem).filter(
            CollectionItem.item_type == item_type,
            CollectionItem.item_id == item_id
        ).all()
        
        collection_ids = [ic.collection_id for ic in item_collections]
        
        if not collection_ids:
            return []
        
        return self.db.query(KnowledgeCollection).filter(
            KnowledgeCollection.id.in_(collection_ids),
            KnowledgeCollection.user_id == user_id
        ).all()
