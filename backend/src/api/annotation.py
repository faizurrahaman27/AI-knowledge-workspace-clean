from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.dependencies.auth import get_current_user
from src.models.user import User
from src.models.annotation import Annotation
from src.schemas.annotation import AnnotationCreate, AnnotationResponse
from src.services.document_service import get_owned_document

router = APIRouter(prefix="/documents", tags=["Annotations"])


@router.post("/{document_id}/annotations", response_model=AnnotationResponse)
def create_annotation(
    document_id: int,
    body: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_document(db, document_id, current_user)  # 404s if not yours

    annotation = Annotation(
        document_id=document_id,
        user_id=current_user.id,
        page=body.page,
        quote_text=body.quote_text,
        note_text=body.note_text,
        color=body.color,
        x_percent=body.x_percent,
        y_percent=body.y_percent,
    )
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.get("/{document_id}/annotations", response_model=list[AnnotationResponse])
def list_annotations(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_document(db, document_id, current_user)

    return (
        db.query(Annotation)
        .filter(Annotation.document_id == document_id, Annotation.user_id == current_user.id)
        .order_by(Annotation.page.asc(), Annotation.created_at.asc())
        .all()
    )


@router.delete("/{document_id}/annotations/{annotation_id}")
def delete_annotation(
    document_id: int,
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_owned_document(db, document_id, current_user)

    annotation = (
        db.query(Annotation)
        .filter(
            Annotation.id == annotation_id,
            Annotation.document_id == document_id,
            Annotation.user_id == current_user.id,
        )
        .first()
    )
    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found.")

    db.delete(annotation)
    db.commit()
    return {"message": "Annotation deleted."}
