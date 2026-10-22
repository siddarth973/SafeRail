import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.safety import SecurityEventModel

GENESIS_PREV_HASH = "GENESIS_000000000000000000000000000000000000000000000000000000000000"

def compute_audit_hash(
    sequence_number: Optional[int],
    prev_hash: Optional[str],
    title: str,
    description: str,
    status_tag: str,
    time_str: str,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Computes a deterministic SHA-256 hash using canonical JSON serialization.
    Canonical rules:
      - Keys sorted alphabetically
      - Compact JSON formatting with separators=(',', ':')
      - Consistent casing and string trimming
    """
    canonical_payload = {
        "description": str(description).strip(),
        "metadata": metadata or {},
        "prev_hash": str(prev_hash or "").strip(),
        "sequence_number": sequence_number,
        "status_tag": str(status_tag).strip().upper(),
        "time_str": str(time_str).strip(),
        "title": str(title).strip()
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def create_audit_event(
    db: Session,
    title: str,
    description: str,
    status_tag: str,
    time_str: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    commit: bool = True
) -> SecurityEventModel:
    """
    Creates a new cryptographically chained audit event in the database.
    Finds the latest chained event, binds to its current_hash, and calculates this event's current_hash.
    """
    if not time_str:
        time_str = datetime.utcnow().strftime("%I:%M %p")

    # Find the most recent event with a current_hash to chain from
    last_event = (
        db.query(SecurityEventModel)
        .filter(SecurityEventModel.current_hash.isnot(None))
        .order_by(SecurityEventModel.id.desc())
        .first()
    )

    if last_event and last_event.current_hash:
        prev_hash = last_event.current_hash
        sequence_number = (last_event.sequence_number or 0) + 1
    else:
        prev_hash = GENESIS_PREV_HASH
        sequence_number = 1

    current_hash = compute_audit_hash(
        sequence_number=sequence_number,
        prev_hash=prev_hash,
        title=title,
        description=description,
        status_tag=status_tag,
        time_str=time_str,
        metadata=metadata
    )

    event = SecurityEventModel(
        sequence_number=sequence_number,
        time_str=time_str,
        title=title,
        description=description,
        status_tag=status_tag,
        prev_hash=prev_hash,
        current_hash=current_hash,
        metadata_json=json.dumps(metadata) if metadata else None
    )

    db.add(event)
    if commit:
        db.commit()
        db.refresh(event)

    return event

def verify_single_event_record(
    event: SecurityEventModel,
    expected_predecessor: Optional[SecurityEventModel]
) -> Dict[str, Any]:
    """
    Verifies the cryptographic integrity and chain linkage of a single SecurityEventModel.
    Returns status: 'VALID', 'INVALID', or 'UNVERIFIABLE'.
    """
    # 1. Unverifiable: No cryptographic hash or prev_hash present
    if not event.current_hash or not event.prev_hash:
        return {
            "event_id": event.id,
            "status": "UNVERIFIABLE",
            "stored_hash": None,
            "computed_hash": None,
            "prev_hash": None,
            "expected_prev_hash": None,
            "sequence_number": event.sequence_number,
            "reason": "Legacy record: created without cryptographic hash chaining proof."
        }

    # 2. Check chain linkage to previous block
    expected_prev = expected_predecessor.current_hash if expected_predecessor else GENESIS_PREV_HASH
    if event.prev_hash != expected_prev:
        return {
            "event_id": event.id,
            "status": "INVALID",
            "stored_hash": event.current_hash,
            "computed_hash": None,
            "prev_hash": event.prev_hash,
            "expected_prev_hash": expected_prev,
            "sequence_number": event.sequence_number,
            "reason": f"Broken chain link: stored prev_hash does not match preceding block's current_hash."
        }

    # 3. Recompute content hash and check against stored current_hash
    metadata = None
    if event.metadata_json:
        try:
            metadata = json.loads(event.metadata_json)
        except Exception:
            metadata = None

    computed = compute_audit_hash(
        sequence_number=event.sequence_number,
        prev_hash=event.prev_hash,
        title=event.title,
        description=event.description,
        status_tag=event.status_tag,
        time_str=event.time_str,
        metadata=metadata
    )

    if computed != event.current_hash:
        return {
            "event_id": event.id,
            "status": "INVALID",
            "stored_hash": event.current_hash,
            "computed_hash": computed,
            "prev_hash": event.prev_hash,
            "expected_prev_hash": expected_prev,
            "sequence_number": event.sequence_number,
            "reason": f"Content tampering detected: recomputed hash does not match stored hash."
        }

    return {
        "event_id": event.id,
        "status": "VALID",
        "stored_hash": event.current_hash,
        "computed_hash": computed,
        "prev_hash": event.prev_hash,
        "expected_prev_hash": expected_prev,
        "sequence_number": event.sequence_number,
        "reason": "Cryptographic signature and chain linkage verified successfully."
    }

def verify_audit_event_by_id(db: Session, event_id: int) -> Dict[str, Any]:
    """
    Verifies a single audit event by ID within the database context.
    """
    event = db.query(SecurityEventModel).filter(SecurityEventModel.id == event_id).first()
    if not event:
        return {
            "event_id": event_id,
            "status": "NOT_FOUND",
            "reason": f"Audit record #{event_id} does not exist."
        }

    # Find predecessor chained event
    prev_event = (
        db.query(SecurityEventModel)
        .filter(
            SecurityEventModel.id < event.id,
            SecurityEventModel.current_hash.isnot(None)
        )
        .order_by(SecurityEventModel.id.desc())
        .first()
    )

    return verify_single_event_record(event, prev_event)

def verify_entire_audit_chain(db: Session) -> Dict[str, Any]:
    """
    Verifies the entire audit trail chain in sequence from beginning to end.
    Detects any modified records, missing links, or invalid relationships.
    """
    events = db.query(SecurityEventModel).order_by(SecurityEventModel.id.asc()).all()
    if not events:
        return {
            "status": "VALID",
            "total_events": 0,
            "valid_count": 0,
            "invalid_count": 0,
            "unverifiable_count": 0,
            "broken_links": [],
            "message": "Audit log is empty.",
            "verified_at": datetime.utcnow().isoformat()
        }

    valid_count = 0
    invalid_count = 0
    unverifiable_count = 0
    broken_links = []

    last_chained_event = None
    for ev in events:
        res = verify_single_event_record(ev, last_chained_event)
        if res["status"] == "VALID":
            valid_count += 1
            last_chained_event = ev
        elif res["status"] == "INVALID":
            invalid_count += 1
            broken_links.append(res)
            last_chained_event = ev
        elif res["status"] == "UNVERIFIABLE":
            unverifiable_count += 1

    if invalid_count > 0:
        overall_status = "INVALID"
        message = f"Integrity check FAILED: {invalid_count} tampered or broken block(s) detected."
    elif valid_count > 0:
        overall_status = "VALID"
        if unverifiable_count > 0:
            message = f"Hash-chain verified: {valid_count} cryptographically signed block(s) valid ({unverifiable_count} legacy records unchained)."
        else:
            message = f"All {valid_count} blocks in the audit hash chain are cryptographically valid."
    else:
        overall_status = "UNVERIFIABLE"
        message = f"All {unverifiable_count} records are legacy entries without cryptographic proofs."

    return {
        "status": overall_status,
        "total_events": len(events),
        "valid_count": valid_count,
        "invalid_count": invalid_count,
        "unverifiable_count": unverifiable_count,
        "broken_links": broken_links,
        "message": message,
        "verified_at": datetime.utcnow().isoformat()
    }
