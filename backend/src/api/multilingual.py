"""
Multilingual Intelligence API

REST API for multilingual support.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User

from src.multilingual.detector import get_language_detector
from src.multilingual.normalizer import get_unicode_normalizer
from src.multilingual.registry import get_language_registry
from src.multilingual.search import get_cross_language_search_service
from src.multilingual.generation import get_multilingual_generation_service
from src.multilingual.preferences import get_language_preference_service
from src.multilingual.models import LanguagePreference

router = APIRouter(prefix="/multilingual", tags=["Multilingual"])


# ============================================================================
# Language Detection Endpoints
# ============================================================================

@router.post("/detect")
async def detect_language(
    text: str = Query(..., min_length=1),
    hint: Optional[str] = None,
):
    """
    Detect language from text.
    
    Automatically detects:
    - Language
    - Script type
    - Writing direction
    - Confidence
    - Mixed language indicators
    """
    detector = get_language_detector()
    
    result = detector.detect(text, hint)
    
    return {
        "language": result.language,
        "confidence": result.confidence,
        "script": result.script,
        "writing_direction": result.writing_direction,
        "is_mixed": result.is_mixed,
        "secondary_languages": result.secondary_languages,
        "encoding": result.encoding,
        "character_count": result.character_count,
        "word_count": result.word_count
    }


@router.post("/detect/batch")
async def detect_language_batch(
    texts: List[str] = Query(..., min_items=1, max_items=100),
    hint: Optional[str] = None,
):
    """Detect languages for multiple texts."""
    detector = get_language_detector()
    
    results = detector.detect_batch(texts)
    
    return [
        {
            "language": r.language,
            "confidence": r.confidence,
            "script": r.script,
            "writing_direction": r.writing_direction,
            "is_mixed": r.is_mixed
        }
        for r in results
    ]


# ============================================================================
# Supported Languages Endpoints
# ============================================================================

@router.get("/languages")
async def list_languages(
    script_type: Optional[str] = None,
    has_embeddings: Optional[bool] = None,
    has_ocr: Optional[bool] = None,
    rtl_only: Optional[bool] = None,
):
    """List all supported languages with filters."""
    registry = get_language_registry()
    
    languages = registry.get_all()
    
    # Apply filters
    if script_type:
        languages = [l for l in languages if l.script_type == script_type]
    
    if has_embeddings is not None:
        if has_embeddings:
            languages = [l for l in languages if l.has_embeddings]
        else:
            languages = [l for l in languages if not l.has_embeddings]
    
    if has_ocr is not None:
        if has_ocr:
            languages = [l for l in languages if l.has_ocr]
        else:
            languages = [l for l in languages if not l.has_ocr]
    
    if rtl_only:
        languages = [l for l in languages if l.writing_direction.value == "rtl"]
    
    return [
        {
            "code": lang.code,
            "name": lang.iso_name,
            "native_name": lang.native_name,
            "script_type": lang.script_type,
            "writing_direction": lang.writing_direction.value,
            "has_embeddings": lang.has_embeddings,
            "has_ocr": lang.has_ocr,
            "has_tts": lang.has_tts
        }
        for lang in languages
    ]


@router.get("/languages/{code}")
async def get_language(code: str):
    """Get details for a specific language."""
    registry = get_language_registry()
    
    lang = registry.get(code)
    
    if not lang:
        raise HTTPException(status_code=404, detail="Language not found")
    
    return {
        "code": lang.code,
        "name": lang.iso_name,
        "native_name": lang.native_name,
        "script_type": lang.script_type,
        "writing_direction": lang.writing_direction.value,
        "has_embeddings": lang.has_embeddings,
        "has_ocr": lang.has_ocr,
        "has_tts": lang.has_tts,
        "related_languages": lang.related_languages,
        "is_rtl": lang.writing_direction.value == "rtl"
    }


@router.get("/languages/search")
async def search_languages(q: str = Query(..., min_length=1)):
    """Search languages by name."""
    registry = get_language_registry()
    
    results = registry.search(q)
    
    return [
        {
            "code": lang.code,
            "name": lang.iso_name,
            "native_name": lang.native_name
        }
        for lang in results
    ]


# ============================================================================
# User Preferences Endpoints
# ============================================================================

@router.get("/preferences")
async def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get user's language preferences."""
    service = get_language_preference_service(db)
    
    return service.get_preferences(current_user.id)


@router.put("/preferences")
async def update_preferences(
    preference_mode: Optional[str] = None,
    follow_upload_language: Optional[bool] = None,
    follow_query_language: Optional[bool] = None,
    preferred_output_language: Optional[str] = None,
    ui_language: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user's language preferences."""
    service = get_language_preference_service(db)
    
    return service.update_preferences(
        user_id=current_user.id,
        preference_mode=preference_mode,
        follow_upload_language=follow_upload_language,
        follow_query_language=follow_query_language,
        preferred_output_language=preferred_output_language,
        ui_language=ui_language
    )


# ============================================================================
# Cross-Language Search Endpoints
# ============================================================================

@router.get("/search")
async def cross_language_search(
    q: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    language_filter: Optional[str] = None,
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search across languages.
    
    Query can be in any language.
    Results are retrieved from documents in all languages.
    """
    service = get_cross_language_search_service(db)
    
    doc_ids = None
    if document_ids:
        try:
            doc_ids = [int(x) for x in document_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document IDs")
    
    results = service.search(
        query=q,
        user_id=current_user.id,
        limit=limit,
        language_filter=language_filter,
        document_ids=doc_ids
    )
    
    return {
        "query": q,
        "results": results
    }


@router.get("/search/distribution")
async def get_language_distribution(
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get language distribution in user's documents."""
    service = get_cross_language_search_service(db)
    
    doc_ids = None
    if document_ids:
        try:
            doc_ids = [int(x) for x in document_ids.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document IDs")
    
    return service.get_language_distribution(
        user_id=current_user.id,
        document_ids=doc_ids
    )


# ============================================================================
# Text Normalization Endpoints
# ============================================================================

@router.post("/normalize")
async def normalize_text(
    text: str = Query(...),
    language: Optional[str] = None,
):
    """Normalize Unicode text."""
    normalizer = get_unicode_normalizer()
    
    normalized = normalizer.normalize(text, language)
    stats = normalizer.get_text_stats(text)
    
    return {
        "original": text,
        "normalized": normalized,
        "stats": stats
    }


# ============================================================================
# Translation Endpoints
# ============================================================================

@router.post("/translate")
async def translate_content(
    text: str = Query(...),
    source_language: str = Query(...),
    target_language: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Translate content between languages.
    
    Note: This is a basic translation endpoint.
    In production, would use dedicated translation API.
    """
    service = get_multilingual_generation_service()
    
    translated = service.translate_content(
        content=text,
        source_language=source_language,
        target_language=target_language
    )
    
    return {
        "original": text,
        "translated": translated,
        "source_language": source_language,
        "target_language": target_language
    }


# ============================================================================
# RTL Support Endpoints
# ============================================================================

@router.get("/rtl/check/{language_code}")
async def check_rtl(language_code: str):
    """Check if language is RTL."""
    from src.multilingual.rtl_renderer import get_rtl_renderer
    
    renderer = get_rtl_renderer()
    config = renderer.get_config(language_code)
    
    return {
        "language_code": language_code,
        "is_rtl": config.enabled,
        "direction": config.base_direction,
        "text_align": config.text_align
    }


@router.get("/rtl/css/{language_code}")
async def get_rtl_css(language_code: str):
    """Get RTL CSS for language."""
    from src.multilingual.rtl_renderer import get_rtl_renderer
    
    renderer = get_rtl_renderer()
    
    if not renderer.is_rtl_language(language_code):
        return {"css": "", "message": "Language is LTR"}
    
    return {
        "css": renderer.get_css(language_code),
        "language_code": language_code
    }


# ============================================================================
# Document Language Endpoints
# ============================================================================

@router.get("/documents/{document_id}/language")
async def get_document_language(
    document_id: int,
    db: Session = Depends(get_db),
):
    """Get detected language for a document."""
    from src.multilingual.models import DocumentLanguage
    
    doc_lang = db.query(DocumentLanguage).filter(
        DocumentLanguage.document_id == document_id
    ).first()
    
    if not doc_lang:
        raise HTTPException(status_code=404, detail="Document language not found")
    
    return {
        "document_id": doc_lang.document_id,
        "primary_language": doc_lang.primary_language,
        "confidence": doc_lang.language_confidence,
        "script_type": doc_lang.script_type,
        "writing_direction": doc_lang.writing_direction,
        "is_mixed": doc_lang.is_mixed,
        "secondary_languages": doc_lang.secondary_languages
    }
