"""
Upload API

REST API for universal file upload and URL import with
support for all knowledge source types.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.services import knowledge_source_service as kss
from src.services import workspace_service as ws

router = APIRouter(prefix="/upload", tags=["Upload"])


# === File Upload Routes ===

@router.post("/file")
async def upload_file(
    file: UploadFile = File(...),
    workspace_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a file for ingestion.
    
    Supports: PDF, TXT, MD, CSV, JSON, DOCX, PPTX, images (with OCR), 
    audio (transcription - future), video (transcription - future), ZIP archives.
    
    Files are automatically processed through the ingestion pipeline:
    Uploaded -> Queued -> Extracting -> Chunking -> Embedding -> Indexed -> Ready
    """
    # Validate workspace access if specified
    if workspace_id:
        try:
            ws._get_owned_or_member_workspace(db, workspace_id, current_user)
        except Exception:
            raise HTTPException(status_code=404, detail="Workspace not found")
    
    try:
        document = await kss.process_universal_upload(
            db=db,
            file=file,
            user=current_user,
            workspace_id=workspace_id
        )
        
        return {
            "id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "size_bytes": document.size_bytes,
            "workspace_id": document.workspace_id,
            "language_code": document.language_code,
            "language_name": document.language_name,
            "source_url": document.source_url,
            "created_at": document.created_at.isoformat() if document.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/files")
async def upload_multiple_files(
    files: List[UploadFile] = File(...),
    workspace_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple files at once.
    
    Each file is processed individually through the ingestion pipeline.
    Returns a list of created documents.
    """
    # Validate workspace access if specified
    if workspace_id:
        try:
            ws._get_owned_or_member_workspace(db, workspace_id, current_user)
        except Exception:
            raise HTTPException(status_code=404, detail="Workspace not found")
    
    results = []
    errors = []
    
    for i, file in enumerate(files):
        try:
            document = await kss.process_universal_upload(
                db=db,
                file=file,
                user=current_user,
                workspace_id=workspace_id
            )
            results.append({
                "id": document.id,
                "filename": document.filename,
                "status": "success"
            })
        except Exception as e:
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {
        "uploaded": results,
        "failed": errors,
        "total": len(files),
        "successful": len(results)
    }


@router.post("/scan")
async def upload_scan(
    file: UploadFile = File(...),
    language_code: Optional[str] = Form(None),
    workspace_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a scanned document for OCR processing.
    
    Images are processed with OCR to extract text, then indexed
    for chat and search.
    """
    # Validate workspace access if specified
    if workspace_id:
        try:
            ws._get_owned_or_member_workspace(db, workspace_id, current_user)
        except Exception:
            raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Validate it's an image
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Scan upload requires an image file (JPEG, PNG, etc.)"
        )
    
    try:
        document = await kss.process_universal_upload(
            db=db,
            file=file,
            user=current_user,
            workspace_id=workspace_id
        )
        
        return {
            "id": document.id,
            "filename": document.filename,
            "status": "processed",
            "language_code": document.language_code,
            "language_name": document.language_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === URL Import Routes ===

class URLImportRequest(BaseModel):
    """Request to import from URL."""
    url: str
    source_type: str = "web_page"  # web_page, github_file, research_paper, doi, youtube
    workspace_id: Optional[int] = None


@router.post("/url")
async def import_from_url(
    body: URLImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import content from a URL.
    
    Supported sources:
    - web_page: Any website article or page
    - github_file: Single file from GitHub
    - research_paper: Academic paper URL
    - youtube: Video for transcription (future)
    """
    # Validate workspace access if specified
    if body.workspace_id:
        try:
            ws._get_owned_or_member_workspace(db, body.workspace_id, current_user)
        except Exception:
            raise HTTPException(status_code=404, detail="Workspace not found")
    
    try:
        document = await kss.process_url_import(
            db=db,
            url=body.url,
            user=current_user,
            workspace_id=body.workspace_id,
            source_type=body.source_type
        )
        
        return {
            "id": document.id,
            "filename": document.filename,
            "content_type": document.content_type,
            "source_url": document.source_url,
            "language_code": document.language_code,
            "language_name": document.language_name,
            "created_at": document.created_at.isoformat() if document.created_at else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/github")
async def import_from_github(
    url: str,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import a single file from GitHub.
    
    Supports raw GitHub URLs or github.com URLs to files.
    """
    # Validate workspace access if specified
    if workspace_id:
        try:
            ws._get_owned_or_member_workspace(db, workspace_id, current_user)
        except Exception:
            raise HTTPException(status_code=404, detail="Workspace not found")
    
    try:
        document = await kss.process_url_import(
            db=db,
            url=url,
            user=current_user,
            workspace_id=workspace_id,
            source_type="github_file"
        )
        
        return {
            "id": document.id,
            "filename": document.filename,
            "source_url": document.source_url,
            "language_code": document.language_code,
            "language_name": document.language_name
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Import BaseModel
from pydantic import BaseModel
