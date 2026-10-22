from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import UntrustedContentModel
from pydantic import BaseModel

router = APIRouter()

class UntrustedContentSchema(BaseModel):
    id: str
    title: str
    content_text: str
    trust_label: str
    source: str
    created_at: str

@router.get("/untrusted-content", response_model=List[UntrustedContentSchema])
def list_untrusted_content(db: Session = Depends(get_db)):
    """
    Returns seeded tickets and external inputs with their trust labeling (Feature A3).
    """
    contents = db.query(UntrustedContentModel).all()
    return [
        UntrustedContentSchema(
            id=c.id,
            title=c.title,
            content_text=c.content_text,
            trust_label=c.trust_label,
            source=c.source,
            created_at=c.created_at.strftime("%I:%M %p")
        ) for c in contents
    ]
