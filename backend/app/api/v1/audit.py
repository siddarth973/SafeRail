from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import SecurityEventModel
from app.schemas.safety import (
    SecurityEventSchema,
    AuditVerificationResponse,
    AuditChainVerificationResponse
)
from app.services.audit_service import (
    verify_audit_event_by_id,
    verify_entire_audit_chain
)

router = APIRouter()

@router.get("/audit/events", response_model=List[SecurityEventSchema])
def list_audit_events(db: Session = Depends(get_db)):
    """
    Returns all audit trail events in chronological sequence (id ASC).
    Includes sequence_number, prev_hash, and current_hash where available.
    """
    events = db.query(SecurityEventModel).order_by(SecurityEventModel.id.asc()).all()
    return [
        SecurityEventSchema(
            id=ev.id,
            sequence_number=ev.sequence_number,
            time_str=ev.time_str,
            title=ev.title,
            description=ev.description,
            status_tag=ev.status_tag,
            prev_hash=ev.prev_hash,
            current_hash=ev.current_hash
        ) for ev in events
    ]

@router.post("/audit/verify/{event_id}", response_model=AuditVerificationResponse)
def verify_event_endpoint(event_id: int, db: Session = Depends(get_db)):
    """
    Cryptographically verifies an individual audit record (Feature A6 / Bug Fix).
    Validates:
      1. Whether cryptographic proof exists (returns UNVERIFIABLE for legacy records).
      2. Content SHA-256 integrity against stored current_hash.
      3. Chain linkage (prev_hash matches predecessor's current_hash).
    """
    result = verify_audit_event_by_id(db, event_id)
    if result.get("status") == "NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["reason"]
        )

    return AuditVerificationResponse(
        event_id=result["event_id"],
        status=result["status"],
        stored_hash=result.get("stored_hash"),
        computed_hash=result.get("computed_hash"),
        prev_hash=result.get("prev_hash"),
        expected_prev_hash=result.get("expected_prev_hash"),
        sequence_number=result.get("sequence_number"),
        reason=result["reason"]
    )

@router.post("/audit/verify-chain", response_model=AuditChainVerificationResponse)
def verify_chain_endpoint(db: Session = Depends(get_db)):
    """
    Cryptographically verifies the entire audit log hash chain.
    Walks all blocks in chronological sequence, checking parent-child hashes and contents.
    Returns honest VALID, INVALID, or UNVERIFIABLE assessment with detailed metrics.
    """
    chain_result = verify_entire_audit_chain(db)
    return AuditChainVerificationResponse(
        status=chain_result["status"],
        total_events=chain_result["total_events"],
        valid_count=chain_result["valid_count"],
        invalid_count=chain_result["invalid_count"],
        unverifiable_count=chain_result["unverifiable_count"],
        broken_links=chain_result["broken_links"],
        message=chain_result["message"],
        verified_at=chain_result["verified_at"]
    )
