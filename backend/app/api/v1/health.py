from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.config import settings
from app.db.session import get_db
from app.schemas.safety import HealthCheckResponse

router = APIRouter()

@router.get("/health", response_model=HealthCheckResponse)
def get_v1_health(db: Session = Depends(get_db)):
    """Health check endpoint checking application and SQLite database status."""
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return HealthCheckResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        tagline=settings.TAGLINE,
        version=settings.VERSION,
        database=db_status,
        timestamp=datetime.utcnow()
    )
