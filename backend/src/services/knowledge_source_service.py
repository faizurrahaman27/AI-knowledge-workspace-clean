"""
Knowledge Source Service

Service for managing knowledge sources with support for universal file types,
URL imports, and the complete processing pipeline lifecycle.
"""

import os
import zipfile
from datetime import datetime, timezone
from typing import Optional, List, Callable, AsyncGenerator
from enum import Enum
import asyncio

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from src.core.settings import settings
from src.core.logging import logger
from src.models.document import Document
from src.models.user import User
from src.utils.vector_store import add_documents, collection
from src.utils.pdf import extract_pages_from_pdf
from src.utils.chunking import chunk_text
from src.utils.embeddings import generate_embeddings
from src.utils.language import detect_language
from src.utils.ocr import extract_text_from_image


UPLOAD_DIR = "uploads"


class ProcessingState(str, Enum):
    """Processing pipeline states."""
    UPLOADED = "uploaded"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    READY = "ready"
    FAILED = "failed"


# Content type to file extension mapping
CONTENT_TYPE_MAP = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/html": ".html",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/json": ".json",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".pptx",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",
    "audio/ogg": ".ogg",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "application/zip": ".zip",
}


# Supported file types for ingestion
SUPPORTED_TYPES = [
    "application/pdf",
    "text/plain",
    "text/html",
    "text/markdown",
    "image/jpeg",
    "image/png",
]


def _safe_filename(filename: str) -> str:
    """Strip path components from filename."""
    return os.path.basename(filename or "upload")


def _detect_content_type(filename: str, content_type: Optional[str] = None) -> str:
    """Detect content type from filename or provided type."""
    if content_type and content_type in CONTENT_TYPE_MAP:
        return content_type
    
    ext = os.path.splitext(filename)[1].lower()
    for ct, e in CONTENT_TYPE_MAP.items():
        if e == ext:
            return ct
    
    # Default to octet-stream
    return "application/octet-stream"


def _get_file_extension(content_type: str, filename: str) -> str:
    """Get file extension for content type."""
    if content_type in CONTENT_TYPE_MAP:
        return CONTENT_TYPE_MAP[content_type]
    
    ext = os.path.splitext(filename)[1]
    return ext if ext else ".bin"


async def _emit_processing_event(
    source_id: int,
    state: ProcessingState,
    message: str,
    workspace_id: Optional[int] = None,
    progress: Optional[float] = None,
    metadata: Optional[dict] = None
):
    """Emit a processing event via WebSocket."""
    try:
        from src.main import orchestrator
        
        if orchestrator and orchestrator._event_manager:
            from src.enterprise.events.manager import EventType, WorkflowEvent
            
            event = WorkflowEvent(
                event_type=EventType.DOCUMENT_PROCESSING,
                workflow_id=f"source_{source_id}",
                user_id=0,  # Will be set by caller
                workspace_id=workspace_id,
                data={
                    "source_id": source_id,
                    "state": state.value,
                    "message": message,
                    "progress": progress,
                    "metadata": metadata or {}
                }
            )
            await orchestrator._event_manager.emit(event)
    except Exception as e:
        logger.debug(f"Could not emit processing event: {e}")


async def process_universal_upload(
    db: Session,
    file: UploadFile,
    user: User,
    workspace_id: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> Document:
    """
    Process any supported file type with full pipeline.
    
    Args:
        db: Database session
        file: Uploaded file
        user: Owner user
        workspace_id: Optional workspace ID
        progress_callback: Optional callback for progress updates
        
    Returns:
        Created document
    """
    original_name = _safe_filename(file.filename)
    content_type = _detect_content_type(original_name, file.content_type)
    
    # Check file size
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    
    # Save file
    file_ext = _get_file_extension(content_type, original_name)
    unique_name = f"{uuid4()}_{original_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_name)
    
    size_bytes = 0
    with open(file_path, "wb") as buffer:
        while True:
            block = file.file.read(1024 * 1024)
            if not block:
                break
            size_bytes += len(block)
            if size_bytes > max_bytes:
                buffer.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB upload limit."
                )
            buffer.write(block)
    
    # Create document record
    document = Document(
        filename=original_name,
        file_path=file_path,
        content_type=content_type,
        size_bytes=size_bytes,
        owner_id=user.id,
        workspace_id=workspace_id,
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # Emit uploaded event
    await _emit_processing_event(
        document.id, ProcessingState.UPLOADED, 
        f"Uploaded {original_name}",
        workspace_id=workspace_id,
        progress=10
    )
    
    # Process based on content type
    try:
        if content_type == "application/pdf":
            await _process_pdf(db, document, user, progress_callback)
        elif content_type.startswith("image/"):
            await _process_image(db, document, user, progress_callback)
        elif content_type in ["text/plain", "text/markdown", "text/csv", "application/json"]:
            await _process_text_file(db, document, user, progress_callback)
        elif content_type == "application/zip":
            await _process_zip(db, document, user, workspace_id, user, progress_callback)
        else:
            # Fallback: treat as text
            await _process_text_file(db, document, user, progress_callback)
            
    except Exception as e:
        logger.exception(f"Processing failed for document {document.id}")
        raise HTTPException(
            status_code=422,
            detail=f"Failed to process file: {str(e)}"
        )
    
    return document


def _ingest_pages(
    db: Session,
    pages: list[dict],
    document: Document,
    current_user: User,
):
    """
    Shared chunk -> embed -> store -> detect-language pipeline.
    """
    all_chunks = []
    all_embeddings = []
    all_ids = []
    all_metadatas = []

    sample_text = ""

    for page_data in pages:
        page_number = page_data["page"]
        page_text = page_data["text"]

        if len(sample_text) < 500:
            sample_text += " " + page_text

        chunks = chunk_text(page_text)
        if not chunks:
            continue

        embeddings = generate_embeddings(chunks)

        for index, chunk in enumerate(chunks):
            all_chunks.append(chunk)
            all_embeddings.append(embeddings[index])
            all_ids.append(f"{current_user.id}_{uuid4()}")
            all_metadatas.append({
                "document_id": document.id,
                "user_id": current_user.id,
                "filename": document.filename,
                "page": page_number,
                "chunk": index + 1,
            })

    if all_chunks:
        add_documents(
            ids=all_ids,
            documents=all_chunks,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
        )

    language_code, language_name = detect_language(sample_text)
    document.language_code = language_code
    document.language_name = language_name
    db.commit()

    logger.info(
        "Document ingested: document_id=%s source=%s pages=%d chunks=%d owner_id=%s language=%s",
        document.id, document.content_type, len(pages), len(all_chunks), current_user.id, language_code,
    )

    return document


async def _process_pdf(
    db: Session,
    document: Document,
    user: User,
    progress_callback: Optional[Callable] = None
):
    """Process PDF file."""
    await _emit_processing_event(
        document.id, ProcessingState.EXTRACTING,
        "Extracting text from PDF",
        progress=20
    )
    
    try:
        pages = extract_pages_from_pdf(document.file_path)
    except Exception:
        logger.exception("Failed to extract text from PDF")
        raise HTTPException(
            status_code=422,
            detail="Could not read this PDF. It may be corrupted or password-protected."
        )
    
    await _emit_processing_event(
        document.id, ProcessingState.CHUNKING,
        f"Processing {len(pages)} pages",
        progress=50
    )
    
    await _emit_processing_event(
        document.id, ProcessingState.EMBEDDING,
        "Generating embeddings",
        progress=70
    )
    
    _ingest_pages(db, pages, document, user)
    
    await _emit_processing_event(
        document.id, ProcessingState.READY,
        "Document ready",
        progress=100
    )


async def _process_image(
    db: Session,
    document: Document,
    user: User,
    progress_callback: Optional[Callable] = None
):
    """Process image file with OCR."""
    await _emit_processing_event(
        document.id, ProcessingState.EXTRACTING,
        "Running OCR on image",
        progress=20
    )
    
    try:
        text = extract_text_from_image(document.file_path)
    except Exception:
        logger.exception("OCR failed for image")
        raise HTTPException(
            status_code=422,
            detail="Could not read text from this image."
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text found in this image."
        )
    
    await _emit_processing_event(
        document.id, ProcessingState.CHUNKING,
        "Processing extracted text",
        progress=50
    )
    
    await _emit_processing_event(
        document.id, ProcessingState.EMBEDDING,
        "Generating embeddings",
        progress=70
    )
    
    _ingest_pages(db, [{"page": 1, "text": text}], document, user)
    
    await _emit_processing_event(
        document.id, ProcessingState.READY,
        "Image processed and ready",
        progress=100
    )


async def _process_text_file(
    db: Session,
    document: Document,
    user: User,
    progress_callback: Optional[Callable] = None
):
    """Process plain text file."""
    await _emit_processing_event(
        document.id, ProcessingState.EXTRACTING,
        "Reading text file",
        progress=20
    )
    
    try:
        with open(document.file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
    except Exception:
        logger.exception("Failed to read text file")
        raise HTTPException(
            status_code=422,
            detail="Could not read this text file."
        )
    
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="The text file is empty."
        )
    
    await _emit_processing_event(
        document.id, ProcessingState.CHUNKING,
        "Chunking text",
        progress=50
    )
    
    await _emit_processing_event(
        document.id, ProcessingState.EMBEDDING,
        "Generating embeddings",
        progress=70
    )
    
    _ingest_pages(db, [{"page": 1, "text": text}], document, user)
    
    await _emit_processing_event(
        document.id, ProcessingState.READY,
        "Text file ready",
        progress=100
    )


async def _process_zip(
    db: Session,
    document: Document,
    user: User,
    workspace_id: Optional[int],
    owner: User,
    progress_callback: Optional[Callable] = None
):
    """Extract and process contents of ZIP file."""
    await _emit_processing_event(
        document.id, ProcessingState.EXTRACTING,
        "Extracting ZIP archive",
        progress=10
    )
    
    try:
        with zipfile.ZipFile(document.file_path, "r") as zf:
            file_list = zf.namelist()
            
            # Filter supported files
            supported_files = [
                f for f in file_list 
                if any(f.lower().endswith(ext) for ext in ['.pdf', '.txt', '.md', '.csv', '.json'])
            ]
            
            if not supported_files:
                raise HTTPException(
                    status_code=422,
                    detail="No supported files found in ZIP archive."
                )
            
            extracted_docs = []
            total = len(supported_files)
            
            for i, filename in enumerate(supported_files):
                progress = 20 + (60 * i / total)
                await _emit_processing_event(
                    document.id, ProcessingState.EXTRACTING,
                    f"Processing {filename}",
                    progress=progress
                )
                
                # Extract to temp file
                temp_path = os.path.join(UPLOAD_DIR, f"_temp_{uuid4()}_{os.path.basename(filename)}")
                
                try:
                    with zf.open(filename) as src, open(temp_path, "wb") as dst:
                        dst.write(src.read())
                    
                    # Create document for this file
                    file_doc = Document(
                        filename=os.path.basename(filename),
                        file_path=temp_path,
                        content_type=_detect_content_type(filename),
                        size_bytes=os.path.getsize(temp_path),
                        owner_id=owner.id,
                        workspace_id=workspace_id,
                    )
                    db.add(file_doc)
                    db.flush()
                    
                    extracted_docs.append(file_doc)
                    
                except Exception as e:
                    logger.warning(f"Failed to extract {filename}: {e}")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    continue
                
                await _emit_processing_event(
                    document.id, ProcessingState.EMBEDDING,
                    f"Embedded {i+1}/{total}",
                    progress=70 + (20 * i / total)
                )
            
            # Delete the ZIP file as we've extracted everything
            os.remove(document.file_path)
            db.delete(document)
            db.commit()
            
            await _emit_processing_event(
                document.id, ProcessingState.READY,
                f"Extracted {len(extracted_docs)} files",
                progress=100
            )
            
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=422,
            detail="Invalid ZIP archive."
        )


async def process_url_import(
    db: Session,
    url: str,
    user: User,
    workspace_id: Optional[int] = None,
    source_type: str = "web_page"
) -> Document:
    """
    Process URL import (website, GitHub, etc.).
    
    Args:
        db: Database session
        url: URL to import
        user: Owner user
        workspace_id: Optional workspace ID
        source_type: Type of source (web_page, github_file, research_paper, etc.)
        
    Returns:
        Created document
    """
    from src.utils.web_extract import fetch_and_extract_url, UrlIngestionError
    from src.utils.github_extract import fetch_github_file, GithubIngestionError
    
    await _emit_processing_event(
        0, ProcessingState.QUEUED,
        f"Queued {source_type} import",
        workspace_id=workspace_id,
        progress=5
    )
    
    try:
        if source_type == "github_file" or "github.com" in url:
            await _emit_processing_event(
                0, ProcessingState.EXTRACTING,
                "Fetching from GitHub",
                workspace_id=workspace_id,
                progress=20
            )
            pages, display_name = fetch_github_file(url)
        else:
            await _emit_processing_event(
                0, ProcessingState.EXTRACTING,
                "Fetching web page",
                workspace_id=workspace_id,
                progress=20
            )
            pages, display_name = fetch_and_extract_url(url)
        
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        full_text = "\n\n".join(p["text"] for p in pages)
        file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_web.txt")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        document = Document(
            filename=display_name[:200] if display_name else url,
            file_path=file_path,
            content_type="text/html",
            size_bytes=len(full_text.encode("utf-8")),
            owner_id=user.id,
            workspace_id=workspace_id,
            source_url=url,
        )
        db.add(document)
        db.commit()
        db.refresh(document)
        
        await _emit_processing_event(
            document.id, ProcessingState.CHUNKING,
            "Chunking content",
            workspace_id=workspace_id,
            progress=50
        )
        
        await _emit_processing_event(
            document.id, ProcessingState.EMBEDDING,
            "Generating embeddings",
            workspace_id=workspace_id,
            progress=70
        )
        
        _ingest_pages(db, pages, document, user)
        
        await _emit_processing_event(
            document.id, ProcessingState.READY,
            "Source imported and ready",
            workspace_id=workspace_id,
            progress=100
        )
        
        return document
        
    except (UrlIngestionError, GithubIngestionError) as e:
        raise HTTPException(status_code=422, detail=str(e))


# Import uuid4
from uuid import uuid4
