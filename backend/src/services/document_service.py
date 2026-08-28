import os
from uuid import uuid4
import asyncio

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from src.core.settings import settings
from src.core.logging import logger

from src.models.chat import Chat
from src.models.document import Document
from src.models.user import User

from src.utils.vector_store import (
    add_documents,
    collection,
)

from src.utils.pdf import extract_pages_from_pdf
from src.utils.chunking import chunk_text
from src.utils.embeddings import generate_embeddings
from src.utils.language import detect_language
from src.utils.ocr import extract_text_from_image

UPLOAD_DIR = "uploads"

PDF_MAGIC_BYTES = b"%PDF-"

# Event emitter for real-time updates
_event_emitter = None

def _get_event_emitter():
    """Get event emitter instance."""
    global _event_emitter
    if _event_emitter is None:
        try:
            from src.core.event_emitter import get_event_emitter
            _event_emitter = get_event_emitter()
        except ImportError:
            pass
    return _event_emitter

async def _emit_event(event_type: str, data: dict = None, document_id: int = None, workspace_id: int = None, user_id: int = None):
    """Emit an event to connected clients."""
    emitter = _get_event_emitter()
    if emitter:
        try:
            await emitter.emit(
                event_type=event_type,
                data=data or {},
                document_id=document_id,
                workspace_id=workspace_id,
                user_id=user_id,
                immediate=True,
            )
        except Exception as e:
            logger.error(f"Failed to emit event {event_type}: {e}")


def _safe_original_name(filename: str) -> str:
    """Strip any path components a client might sneak into the filename."""
    return os.path.basename(filename or "upload.pdf")


def _ingest_pages(
    db: Session,
    pages: list[dict],
    document: Document,
    current_user: User,
):
    """
    Shared chunk -> embed -> store -> detect-language pipeline, given a
    Document row that already exists and a list of {"page": N, "text": "..."}
    dicts -- the actual extraction differs per source (PyMuPDF for PDFs,
    trafilatura for websites, a raw GitHub fetch for code/doc files, OCR
    for scanned images), but everything downstream of "I have page-shaped
    text" is identical, so it lives here once instead of four times.
    """
    # Emit pipeline started event
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_event(
                "pipeline:start",
                {"message": f"Starting document processing for {document.filename}", "pages": len(pages)},
                document_id=document.id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_event(
                "pipeline:start",
                {"message": f"Starting document processing for {document.filename}", "pages": len(pages)},
                document_id=document.id,
                user_id=current_user.id,
            ))
    except Exception:
        pass
    
    all_chunks = []
    all_embeddings = []
    all_ids = []
    all_metadatas = []

    sample_text_for_language = ""
    
    total_pages = len(pages)
    
    for page_data in pages:
        page_number = page_data["page"]
        page_text = page_data["text"]

        if len(sample_text_for_language) < 500:
            sample_text_for_language += " " + page_text

        # Emit chunking event
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_event(
                    "chunking:started",
                    {"message": f"Chunking page {page_number}/{total_pages}", "page": page_number, "total_pages": total_pages},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_event(
                    "chunking:started",
                    {"message": f"Chunking page {page_number}/{total_pages}", "page": page_number, "total_pages": total_pages},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

        chunks = chunk_text(page_text)
        if not chunks:
            continue

        # Emit embedding event
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_event(
                    "embedding:started",
                    {"message": f"Generating embeddings for {len(chunks)} chunks", "chunk_count": len(chunks)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_event(
                    "embedding:started",
                    {"message": f"Generating embeddings for {len(chunks)} chunks", "chunk_count": len(chunks)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

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
        
        # Emit chunking completed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_event(
                    "chunking:completed",
                    {"message": f"Chunked page {page_number}", "page": page_number, "chunks_created": len(chunks)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_event(
                    "chunking:completed",
                    {"message": f"Chunked page {page_number}", "page": page_number, "chunks_created": len(chunks)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass

    # Emit embedding completed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_event(
                "embedding:completed",
                {"message": f"Embeddings generated for {len(all_chunks)} chunks", "total_chunks": len(all_chunks)},
                document_id=document.id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_event(
                "embedding:completed",
                {"message": f"Embeddings generated for {len(all_chunks)} chunks", "total_chunks": len(all_chunks)},
                document_id=document.id,
                user_id=current_user.id,
            ))
    except Exception:
        pass

    if all_chunks:
        # Emit indexing event
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(_emit_event(
                    "indexing:started",
                    {"message": "Indexing documents in vector store", "document_count": len(all_ids)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
            else:
                loop.run_until_complete(_emit_event(
                    "indexing:started",
                    {"message": "Indexing documents in vector store", "document_count": len(all_ids)},
                    document_id=document.id,
                    user_id=current_user.id,
                ))
        except Exception:
            pass
        
        add_documents(
            ids=all_ids,
            documents=all_chunks,
            embeddings=all_embeddings,
            metadatas=all_metadatas,
        )

    # Emit language detection
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_event(
                "language:detection:started",
                {"message": "Detecting document language"},
                document_id=document.id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_event(
                "language:detection:started",
                {"message": "Detecting document language"},
                document_id=document.id,
                user_id=current_user.id,
            ))
    except Exception:
        pass

    language_code, language_name = detect_language(sample_text_for_language)
    document.language_code = language_code
    document.language_name = language_name
    db.commit()

    # Emit language detection completed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_event(
                "language:detection:completed",
                {"message": f"Language detected: {language_name}", "language_code": language_code, "language_name": language_name},
                document_id=document.id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_event(
                "language:detection:completed",
                {"message": f"Language detected: {language_name}", "language_code": language_code, "language_name": language_name},
                document_id=document.id,
                user_id=current_user.id,
            ))
    except Exception:
        pass

    # Emit document processed
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_emit_event(
                "document:processed",
                {"message": "Document processed successfully", "document_id": document.id, "filename": document.filename, "pages": len(pages), "chunks": len(all_chunks), "language": language_code},
                document_id=document.id,
                user_id=current_user.id,
            ))
        else:
            loop.run_until_complete(_emit_event(
                "document:processed",
                {"message": "Document processed successfully", "document_id": document.id, "filename": document.filename, "pages": len(pages), "chunks": len(all_chunks), "language": language_code},
                document_id=document.id,
                user_id=current_user.id,
            ))
    except Exception:
        pass

    logger.info(
        "Document ingested: document_id=%s source=%s pages=%d chunks=%d owner_id=%s language=%s",
        document.id, document.content_type, len(pages), len(all_chunks), current_user.id, language_code,
    )

    return document


def _ingest_pdf_file(
    db: Session,
    file_path: str,
    original_name: str,
    size_bytes: int,
    current_user: User,
):
    """
    Shared ingestion pipeline for any PDF already saved to disk, whether it
    arrived as a direct upload or was assembled from scanned photos
    (see documents_from_images below). Extract -> chunk -> embed -> store
    -> detect language -> persist Document row.
    """

    document = Document(
        filename=original_name,
        file_path=file_path,
        content_type="application/pdf",
        size_bytes=size_bytes,
        owner_id=current_user.id,
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    try:
        pages = extract_pages_from_pdf(file_path)
    except Exception:
        logger.exception("Failed to extract text from PDF (document_id=%s)", document.id)
        db.delete(document)
        db.commit()
        os.remove(file_path)
        raise HTTPException(
            status_code=422,
            detail="Could not read this PDF. It may be corrupted, empty, or password-protected.",
        )

    return _ingest_pages(db, pages, document, current_user)


def upload_document(
    db: Session,
    file: UploadFile,
    current_user: User,
):
    original_name = _safe_original_name(file.filename)

    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    unique_filename = f"{uuid4()}_{original_name}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    size_bytes = 0

    # Stream to disk in chunks so a huge upload can't exhaust memory, and
    # enforce the size cap while writing rather than after the fact.
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
                    detail=f"File exceeds the {settings.MAX_UPLOAD_MB}MB upload limit.",
                )
            buffer.write(block)

    # Validate actual file content, not just the extension: a client can
    # rename any file to end in ".pdf".
    with open(file_path, "rb") as f:
        header = f.read(len(PDF_MAGIC_BYTES))

    if header != PDF_MAGIC_BYTES:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    return _ingest_pdf_file(db, file_path, original_name, size_bytes, current_user)


def upload_document_from_images(
    db: Session,
    files: list[UploadFile],
    current_user: User,
    document_name: str = "Scanned Document.pdf",
):
    """
    "Scan Document" flow: multiple photos (e.g. from a phone camera) are
    merged into a single PDF, one page per photo, then run through the
    exact same ingestion pipeline as a direct PDF upload -- so scanned
    documents get full RAG chat, citations, and page-jump support too.
    """
    import img2pdf
    from PIL import Image, ImageOps

    if not files:
        raise HTTPException(status_code=400, detail="At least one photo is required.")

    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    processed_image_paths = []

    try:
        for i, file in enumerate(files):
            raw = file.file.read()

            if len(raw) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Photo {i + 1} exceeds the {settings.MAX_UPLOAD_MB}MB limit.",
                )

            temp_path = os.path.join(UPLOAD_DIR, f"_scan_{uuid4()}.jpg")

            with open(temp_path, "wb") as f:
                f.write(raw)

            try:
                # Normalize orientation (phone EXIF) and re-save as a clean
                # JPEG so img2pdf gets a consistent, valid input regardless
                # of the source format (png/webp/heic-as-jpeg, etc.)
                image = Image.open(temp_path)
                image = ImageOps.exif_transpose(image)
                image = image.convert("RGB")
                image.save(temp_path, "JPEG", quality=90)
            except Exception:
                os.remove(temp_path)
                raise HTTPException(status_code=400, detail=f"Photo {i + 1} is not a readable image.")

            processed_image_paths.append(temp_path)

        unique_filename = f"{uuid4()}_{_safe_original_name(document_name)}"
        pdf_path = os.path.join(UPLOAD_DIR, unique_filename)

        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(processed_image_paths))

    finally:
        for p in processed_image_paths:
            if os.path.exists(p):
                os.remove(p)

    size_bytes = os.path.getsize(pdf_path)

    return _ingest_pdf_file(
        db, pdf_path, _safe_original_name(document_name), size_bytes, current_user
    )


def ingest_from_url(db: Session, url: str, current_user: User):
    """Ingest a web page's readable content as a document. See
    utils/web_extract.py for the SSRF guardrails -- this fetches a URL on
    the server's behalf at a logged-in user's request, which is a real
    attack surface if not validated."""
    from src.utils.web_extract import fetch_and_extract_url, UrlIngestionError

    try:
        pages, title = fetch_and_extract_url(url)
    except UrlIngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    full_text = "\n\n".join(p["text"] for p in pages)
    file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_web.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    document = Document(
        filename=title[:200],
        file_path=file_path,
        content_type="text/html",
        size_bytes=len(full_text.encode("utf-8")),
        owner_id=current_user.id,
        source_url=url,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _ingest_pages(db, pages, document, current_user)


def ingest_from_github(db: Session, url: str, current_user: User):
    """Ingest a single file from a public GitHub repo (README, a doc, a
    source file) -- NOT a whole-repo crawler, see utils/github_extract.py."""
    from src.utils.github_extract import fetch_github_file, GithubIngestionError

    try:
        pages, display_name = fetch_github_file(url)
    except GithubIngestionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    full_text = "\n\n".join(p["text"] for p in pages)
    file_path = os.path.join(UPLOAD_DIR, f"{uuid4()}_{_safe_original_name(display_name)}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_text)

    document = Document(
        filename=display_name,
        file_path=file_path,
        content_type="text/plain",
        size_bytes=len(full_text.encode("utf-8")),
        owner_id=current_user.id,
        source_url=url,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _ingest_pages(db, pages, document, current_user)


def ingest_from_scanned_image(
    db: Session,
    file: UploadFile,
    current_user: User,
    language_code: str | None = None,
):
    """
    Turns a photo into an actual searchable, chat-able document via OCR --
    distinct from /scan/analyze (the standalone one-off "read this photo
    to me" tool), this persists the extracted text into the RAG pipeline
    like any other document, with citations back to "page 1" of the scan.
    """
    original_name = _safe_original_name(file.filename or "scan.jpg")
    ext = os.path.splitext(original_name)[1].lower()

    if ext not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
        raise HTTPException(status_code=400, detail=f"Unsupported image type '{ext}'.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    image_path = os.path.join(UPLOAD_DIR, f"{uuid4()}{ext}")
    with open(image_path, "wb") as f:
        f.write(file.file.read())

    try:
        text = extract_text_from_image(image_path, language_code=language_code)
    except Exception:
        logger.exception("OCR ingestion failed for %s", original_name)
        os.remove(image_path)
        raise HTTPException(status_code=422, detail="Could not read text from this image.")

    if not text.strip():
        os.remove(image_path)
        raise HTTPException(status_code=422, detail="No readable text found in this image.")

    document = Document(
        filename=original_name,
        file_path=image_path,
        content_type="image/ocr",
        size_bytes=os.path.getsize(image_path),
        owner_id=current_user.id,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return _ingest_pages(db, [{"page": 1, "text": text}], document, current_user)


def get_user_documents(
    db: Session,
    current_user: User,
):

    return (
        db.query(Document)
        .filter(
            Document.owner_id == current_user.id
        )
        .order_by(Document.id.desc())
        .all()
    )


def get_owned_document(
    db: Session,
    document_id: int,
    current_user: User,
) -> Document:
    """Fetch a document the current user owns, or 404. Shared by the file
    endpoint and anything else that needs owner-checked access."""

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    # Defensive: only enforce file existence when a path is actually set,
    # in case a future ingestion source doesn't save a local file (every
    # current source -- PDF, website, GitHub, OCR scan -- does).
    if document.file_path and not os.path.exists(document.file_path):
        raise HTTPException(status_code=404, detail="File is missing on the server.")

    return document


def delete_document(
    db: Session,
    document_id: int,
    current_user: User,
):

    document = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.owner_id == current_user.id,
        )
        .first()
    )

    if not document:

        raise HTTPException(
            status_code=404,
            detail="Document not found.",
        )

    if os.path.exists(document.file_path):
        os.remove(document.file_path)

    collection.delete(
        where={
            "document_id": document.id
        }
    )

    (
        db.query(Chat)
        .filter(
            Chat.document_id == document.id
        )
        .delete()
    )

    db.delete(document)

    db.commit()

    logger.info("Document deleted: document_id=%s owner_id=%s", document_id, current_user.id)

    return {
        "message": "Document deleted successfully."
    }
