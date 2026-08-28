"""
Language Preferences Service

Manages user language preferences.
"""

from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from src.multilingual.models import LanguagePreference
from src.multilingual.registry import get_language_registry
from src.core.logging import logger


class LanguagePreferenceService:
    """
    Service for managing user language preferences.
    
    Preference modes:
    - auto: Automatically detect and respond in user's query language
    - follow_upload: Respond in the language of the uploaded document
    - follow_query: Always respond in query language
    - specific: Always respond in a specific language
    """
    
    def __init__(self, db: Session):
        """Initialize the preference service."""
        self.db = db
        self.registry = get_language_registry()
    
    def get_preferences(self, user_id: int) -> Dict[str, Any]:
        """
        Get user's language preferences.
        
        Args:
            user_id: User ID
            
        Returns:
            User preferences dict
        """
        pref = self.db.query(LanguagePreference).filter(
            LanguagePreference.user_id == user_id
        ).first()
        
        if not pref:
            # Return default preferences
            return self._get_default_preferences()
        
        return {
            "preference_mode": pref.preference_mode,
            "follow_upload_language": pref.follow_upload_language,
            "follow_query_language": pref.follow_query_language,
            "preferred_output_language": pref.preferred_output_language,
            "ui_language": pref.ui_language
        }
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default preferences."""
        return {
            "preference_mode": "auto",
            "follow_upload_language": True,
            "follow_query_language": True,
            "preferred_output_language": None,
            "ui_language": "en"
        }
    
    def update_preferences(
        self,
        user_id: int,
        preference_mode: Optional[str] = None,
        follow_upload_language: Optional[bool] = None,
        follow_query_language: Optional[bool] = None,
        preferred_output_language: Optional[str] = None,
        ui_language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update user's language preferences.
        
        Args:
            user_id: User ID
            preference_mode: Preference mode (auto, follow_upload, follow_query, specific)
            follow_upload_language: Follow uploaded document language
            follow_query_language: Follow query language
            preferred_output_language: Specific language to always use
            ui_language: UI language
            
        Returns:
            Updated preferences
        """
        pref = self.db.query(LanguagePreference).filter(
            LanguagePreference.user_id == user_id
        ).first()
        
        if not pref:
            pref = LanguagePreference(user_id=user_id)
            self.db.add(pref)
        
        # Update fields
        if preference_mode is not None:
            pref.preference_mode = preference_mode
        
        if follow_upload_language is not None:
            pref.follow_upload_language = follow_upload_language
        
        if follow_query_language is not None:
            pref.follow_query_language = follow_query_language
        
        if preferred_output_language is not None:
            # Validate language
            if self.registry.get(preferred_output_language):
                pref.preferred_output_language = preferred_output_language
        
        if ui_language is not None:
            if self.registry.get(ui_language):
                pref.ui_language = ui_language
        
        pref.updated_at = datetime.utcnow()
        
        self.db.commit()
        self.db.refresh(pref)
        
        return self.get_preferences(user_id)
    
    def determine_output_language(
        self,
        user_id: int,
        query_language: Optional[str] = None,
        document_language: Optional[str] = None
    ) -> str:
        """
        Determine the output language based on preferences.
        
        Args:
            user_id: User ID
            query_language: Detected query language
            document_language: Document language
            
        Returns:
            Determined output language
        """
        prefs = self.get_preferences(user_id)
        
        mode = prefs["preference_mode"]
        
        if mode == "specific" and prefs["preferred_output_language"]:
            return prefs["preferred_output_language"]
        
        if mode == "follow_upload" and document_language:
            return document_language
        
        if mode == "follow_query" and query_language:
            return query_language
        
        # Auto mode
        if query_language:
            return query_language
        
        if document_language:
            return document_language
        
        # Fallback to English
        return "en"
    
    def get_supported_languages(self) -> list:
        """Get list of supported languages."""
        languages = self.registry.get_all()
        
        return [
            {
                "code": lang.code,
                "name": lang.iso_name,
                "native_name": lang.native_name,
                "script_type": lang.script_type,
                "writing_direction": lang.writing_direction.value,
                "has_embeddings": lang.has_embeddings,
                "has_ocr": lang.has_ocr
            }
            for lang in languages
        ]
    
    def validate_language(self, language_code: str) -> bool:
        """Check if language is supported."""
        return self.registry.get(language_code) is not None


# Service factory
def get_language_preference_service(db: Session) -> LanguagePreferenceService:
    """Get language preference service."""
    return LanguagePreferenceService(db)
