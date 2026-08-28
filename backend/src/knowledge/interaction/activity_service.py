"""
Recent Activity Service

Manages recent activity tracking and dashboard data.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.knowledge.interaction_models import (
    RecentActivity, PinnedItem, KnowledgeBookmark, KnowledgeNote
)
from src.models.document import Document
from src.core.logging import logger


class RecentActivityService:
    """
    Service for tracking and retrieving recent activity.
    
    Tracks:
    - Opened items
    - Generated items
    - Studied items
    - Uploaded items
    """
    
    def __init__(self, db: Session):
        """Initialize the activity service."""
        self.db = db
    
    def log_activity(
        self,
        user_id: int,
        activity_type: str,
        item_type: str,
        item_id: int,
        title: Optional[str] = None,
        preview: Optional[str] = None,
        workspace_id: Optional[int] = None
    ) -> RecentActivity:
        """
        Log a user activity.
        
        Args:
            user_id: User ID
            activity_type: Type of activity (opened, generated, studied, uploaded)
            item_type: Type of item (document, note, flashcard, etc.)
            item_id: Item ID
            title: Optional title
            preview: Optional preview text
            workspace_id: Optional workspace
            
        Returns:
            Created activity record
        """
        # Check for existing recent activity for this item
        existing = self.db.query(RecentActivity).filter(
            RecentActivity.user_id == user_id,
            RecentActivity.item_type == item_type,
            RecentActivity.item_id == item_id
        ).first()
        
        if existing:
            # Update timestamp
            existing.created_at = datetime.utcnow()
            if title:
                existing.title = title
            if preview:
                existing.preview = preview
            self.db.commit()
            self.db.refresh(existing)
            return existing
        
        # Create new activity
        activity = RecentActivity(
            user_id=user_id,
            activity_type=activity_type,
            item_type=item_type,
            item_id=item_id,
            title=title,
            preview=preview,
            workspace_id=workspace_id
        )
        
        self.db.add(activity)
        
        # Clean up old activities (keep last 100 per user)
        old_count = self.db.query(RecentActivity).filter(
            RecentActivity.user_id == user_id
        ).count()
        
        if old_count > 100:
            # Delete oldest activities
            self.db.query(RecentActivity).filter(
                RecentActivity.user_id == user_id
            ).order_by(
                RecentActivity.created_at.asc()
            ).limit(old_count - 100).delete()
        
        self.db.commit()
        self.db.refresh(activity)
        
        return activity
    
    def get_recent_activity(
        self,
        user_id: int,
        activity_type: Optional[str] = None,
        item_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent activities."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        query = self.db.query(RecentActivity).filter(
            RecentActivity.user_id == user_id,
            RecentActivity.created_at >= cutoff
        )
        
        if activity_type:
            query = query.filter(RecentActivity.activity_type == activity_type)
        
        if item_type:
            query = query.filter(RecentActivity.item_type == item_type)
        
        activities = query.order_by(
            RecentActivity.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": a.id,
                "activity_type": a.activity_type,
                "item_type": a.item_type,
                "item_id": a.item_id,
                "title": a.title,
                "preview": a.preview,
                "created_at": a.created_at.isoformat() if a.created_at else None
            }
            for a in activities
        ]
    
    def get_dashboard_data(
        self,
        user_id: int,
        limit: int = 10
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get dashboard data for all activity types."""
        return {
            "recently_opened": self.get_recent_activity(
                user_id, activity_type="opened", limit=limit
            ),
            "recently_generated": self.get_recent_activity(
                user_id, activity_type="generated", limit=limit
            ),
            "recently_studied": self.get_recent_activity(
                user_id, activity_type="studied", limit=limit
            ),
            "recently_uploaded": self.get_recent_activity(
                user_id, activity_type="uploaded", limit=limit
            ),
        }
    
    # =========================================================================
    # Pinned Items
    # =========================================================================
    
    def pin_item(
        self,
        user_id: int,
        item_type: str,
        item_id: int,
        title: Optional[str] = None,
        thumbnail: Optional[str] = None,
        workspace_id: Optional[int] = None
    ) -> PinnedItem:
        """Pin an item."""
        # Check if already pinned
        existing = self.db.query(PinnedItem).filter(
            PinnedItem.user_id == user_id,
            PinnedItem.item_type == item_type,
            PinnedItem.item_id == item_id
        ).first()
        
        if existing:
            return existing
        
        pinned = PinnedItem(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            title=title,
            thumbnail=thumbnail,
            workspace_id=workspace_id
        )
        
        self.db.add(pinned)
        self.db.commit()
        self.db.refresh(pinned)
        
        return pinned
    
    def unpin_item(
        self,
        user_id: int,
        item_type: str,
        item_id: int
    ) -> bool:
        """Unpin an item."""
        pinned = self.db.query(PinnedItem).filter(
            PinnedItem.user_id == user_id,
            PinnedItem.item_type == item_type,
            PinnedItem.item_id == item_id
        ).first()
        
        if not pinned:
            return False
        
        self.db.delete(pinned)
        self.db.commit()
        
        return True
    
    def get_pinned_items(
        self,
        user_id: int,
        item_type: Optional[str] = None,
        workspace_id: Optional[int] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get pinned items."""
        query = self.db.query(PinnedItem).filter(
            PinnedItem.user_id == user_id
        )
        
        if item_type:
            query = query.filter(PinnedItem.item_type == item_type)
        
        if workspace_id:
            query = query.filter(PinnedItem.workspace_id == workspace_id)
        
        pinned = query.order_by(
            PinnedItem.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": p.id,
                "item_type": p.item_type,
                "item_id": p.item_id,
                "title": p.title,
                "thumbnail": p.thumbnail,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in pinned
        ]
    
    # =========================================================================
    # Bookmarks
    # =========================================================================
    
    def add_bookmark(
        self,
        user_id: int,
        item_type: str,
        item_id: int,
        title: Optional[str] = None,
        notes: Optional[str] = None,
        collection_id: Optional[int] = None
    ) -> KnowledgeBookmark:
        """Add a bookmark."""
        bookmark = KnowledgeBookmark(
            user_id=user_id,
            item_type=item_type,
            item_id=item_id,
            title=title,
            notes=notes,
            collection_id=collection_id
        )
        
        self.db.add(bookmark)
        self.db.commit()
        self.db.refresh(bookmark)
        
        return bookmark
    
    def remove_bookmark(
        self,
        user_id: int,
        item_type: str,
        item_id: int
    ) -> bool:
        """Remove a bookmark."""
        bookmark = self.db.query(KnowledgeBookmark).filter(
            KnowledgeBookmark.user_id == user_id,
            KnowledgeBookmark.item_type == item_type,
            KnowledgeBookmark.item_id == item_id
        ).first()
        
        if not bookmark:
            return False
        
        self.db.delete(bookmark)
        self.db.commit()
        
        return True
    
    def get_bookmarks(
        self,
        user_id: int,
        collection_id: Optional[int] = None,
        item_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get bookmarks."""
        query = self.db.query(KnowledgeBookmark).filter(
            KnowledgeBookmark.user_id == user_id
        )
        
        if collection_id:
            query = query.filter(KnowledgeBookmark.collection_id == collection_id)
        
        if item_type:
            query = query.filter(KnowledgeBookmark.item_type == item_type)
        
        bookmarks = query.order_by(
            KnowledgeBookmark.position,
            KnowledgeBookmark.created_at.desc()
        ).limit(limit).all()
        
        return [
            {
                "id": b.id,
                "item_type": b.item_type,
                "item_id": b.item_id,
                "title": b.title,
                "notes": b.notes,
                "collection_id": b.collection_id,
                "created_at": b.created_at.isoformat() if b.created_at else None
            }
            for b in bookmarks
        ]
    
    # =========================================================================
    # Quick Stats
    # =========================================================================
    
    def get_activity_summary(
        self,
        user_id: int,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get activity summary for the last N days."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Count by activity type
        activities = self.db.query(
            RecentActivity.activity_type,
            func.count(RecentActivity.id).label('count')
        ).filter(
            RecentActivity.user_id == user_id,
            RecentActivity.created_at >= cutoff
        ).group_by(
            RecentActivity.activity_type
        ).all()
        
        # Count by item type
        item_counts = self.db.query(
            RecentActivity.item_type,
            func.count(RecentActivity.id).label('count')
        ).filter(
            RecentActivity.user_id == user_id,
            RecentActivity.created_at >= cutoff
        ).group_by(
            RecentActivity.item_type
        ).all()
        
        return {
            "period_days": days,
            "activity_by_type": {a.activity_type: a.count for a in activities},
            "activity_by_item": {a.item_type: a.count for a in item_counts},
            "total_activities": sum(a.count for a in activities),
            "pinned_count": self.db.query(PinnedItem).filter(
                PinnedItem.user_id == user_id
            ).count(),
            "bookmark_count": self.db.query(KnowledgeBookmark).filter(
                KnowledgeBookmark.user_id == user_id
            ).count(),
        }


# Import func for count
from sqlalchemy import func
