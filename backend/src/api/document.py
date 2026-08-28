from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user

from src.models.user import User
from src.schemas.document import DocumentResponse

from src.services.document_service import (
    upload_document,
    upload_document_from_images,
    ingest_from_url,
    ingest_from_github,
    ingest_from_scanned_image,
    get_user_documents,
    delete_document,
    get_owned_document,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


class UrlIngestRequest(BaseModel):
    url: str


class GithubIngestRequest(BaseModel):
    url: str


@router.post("/upload", response_model=DocumentResponse)
def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return upload_document(db=db, file=file, current_user=current_user)


@router.post("/upload-from-scan", response_model=DocumentResponse)
def upload_from_scan(
    files: list[UploadFile] = File(...),
    document_name: str = Form("Scanned Document.pdf"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    "Scan Document" flow: accepts one or more photos captured from the
    browser camera (see CameraScan.jsx), merges them into a single PDF
    (one page per photo), and runs them through the same ingestion
    pipeline as a direct PDF upload.
    """
    return upload_document_from_images(
        db=db, files=files, current_user=current_user, document_name=document_name,
    )


@router.post("/from-url", response_model=DocumentResponse)
def add_document_from_url(
    body: UrlIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import a web page's readable content (article body, stripped of nav/
    ads) as a chat-able document. Blocks requests to private/internal
    addresses -- see utils/web_extract.py's SSRF guard.
    """
    return ingest_from_url(db=db, url=body.url, current_user=current_user)


@router.post("/from-github", response_model=DocumentResponse)
def add_document_from_github(
    body: GithubIngestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Import a single file from a public GitHub repo (README, a doc, a
    source file) by its github.com blob URL. This is NOT a whole-repo
    crawler -- one file per call, see utils/github_extract.py.
    """
    return ingest_from_github(db=db, url=body.url, current_user=current_user)


@router.post("/from-image", response_model=DocumentResponse)
def add_document_from_image(
    file: UploadFile = File(...),
    language_code: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Turns a photo into an actual searchable, chat-able document via OCR
    -- distinct from /scan/analyze (the one-off "read this to me" tool),
    this persists it into the RAG pipeline like any other document.
    """
    return ingest_from_scanned_image(
        db=db, file=file, current_user=current_user, language_code=language_code,
    )


@router.get("/", response_model=list[DocumentResponse])
def list_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_documents(db=db, current_user=current_user)


@router.get("/{document_id}/file")
def get_document_file(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streams the original file back to its owner, for the in-app viewer.
    Requires the same JWT as every other route -- the frontend fetches
    this as a blob (with the Authorization header) and renders it via an
    object URL, rather than linking to it directly, so the file is never
    reachable by a bare, unauthenticated URL.

    Media type depends on how the document was ingested: a direct PDF
    upload (or camera scan, which is assembled into a PDF) serves as
    application/pdf for the PDF.js viewer; website/GitHub/OCR-image
    imports were never PDFs to begin with, so those serve their saved
    extracted text as plain text instead.
    """
    document = get_owned_document(db, document_id, current_user)

    if document.content_type == "application/pdf":
        return FileResponse(path=document.file_path, media_type="application/pdf", filename=document.filename)

    if document.content_type == "image/ocr":
        # The original photo, not extracted text -- still useful to view.
        return FileResponse(path=document.file_path, filename=document.filename)

    with open(document.file_path, "r", encoding="utf-8") as f:
        return PlainTextResponse(f.read())


@router.delete("/{document_id}")
def delete_pdf(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return delete_document(db=db, document_id=document_id, current_user=current_user)
