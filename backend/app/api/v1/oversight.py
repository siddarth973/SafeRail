import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import (
    AttentionDrillModel,
    OversightSnapshotModel,
    RestrictionHistoryModel,
    OversightMetricModel
)
from app.schemas.safety import (
    OversightHealthResponse,
    OversightHealthMetricItem,
    ReviewerBudgetResponse,
    AttentionDrillResponse,
    DrillSubmissionRequest,
    DrillSubmissionResponse,
    RestrictionStatusResponse,
    RestrictionHistoryItem,
    RestrictionOverrideRequest
)
from app.services.oversight_service import (
    calculate_oversight_health,
    get_reviewer_budget_status,
    get_current_restriction_level,
    evaluate_and_apply_automatic_restrictions,
    submit_drill_response,
    RESTRICTION_NAMES
)
from app.services.audit_service import create_audit_event
from app.core.auth import verify_reviewer_authorization

router = APIRouter()

@router.get("/oversight/health", response_model=OversightHealthResponse)
def get_oversight_health(db: Session = Depends(get_db)):
    """
    Feature B4: Live Oversight Health Score & Metric Breakdown.
    Calculates deterministic 0-100 score from real events and drills.
    Honestly identifies INSUFFICIENT_DATA rather than inventing scores.
    """
    health = calculate_oversight_health(db)
    
    # Save a periodic historical snapshot
    try:
        snapshot = OversightSnapshotModel(
            score=health["score"],
            status=health["status"],
            data_sufficiency=health["data_sufficiency"],
            budget_utilization=health["budget"]["utilization_rate"],
            drill_accuracy=health["drills"]["pass_rate"],
            rapid_approval_count=health["rapid_approvals"],
            pending_backlog_count=health["pending_backlog"],
            metrics_json=json.dumps(health["breakdown"])
        )
        db.add(snapshot)
        db.commit()
    except Exception:
        db.rollback()

    return OversightHealthResponse(
        score=health["score"],
        status=health["status"],
        data_sufficiency=health["data_sufficiency"],
        breakdown=[
            OversightHealthMetricItem(
                metric=item["metric"],
                measured_value=item["measured_value"],
                points_earned=item["points_earned"],
                max_points=item["max_points"],
                explanation=item["explanation"]
            ) for item in health["breakdown"]
        ],
        budget=health["budget"],
        drills=health["drills"],
        rapid_approvals=health["rapid_approvals"],
        pending_backlog=health["pending_backlog"],
        calculated_at=health["calculated_at"]
    )

@router.get("/oversight/history")
def get_oversight_history(limit: int = 15, db: Session = Depends(get_db)):
    """
    Returns historical oversight health snapshots for trend analysis.
    """
    snapshots = (
        db.query(OversightSnapshotModel)
        .order_by(OversightSnapshotModel.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": s.id,
            "score": s.score,
            "status": s.status,
            "data_sufficiency": s.data_sufficiency,
            "budget_utilization": s.budget_utilization,
            "drill_accuracy": s.drill_accuracy,
            "rapid_approval_count": s.rapid_approval_count,
            "snapshot_at": s.snapshot_at.isoformat()
        } for s in reversed(snapshots)
    ]

@router.get("/oversight/budget", response_model=ReviewerBudgetResponse)
def get_approval_budget(reviewer_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Feature B1: Reviewer Approval Budget and Capacity.
    Calculates reviewer workload from real ApprovalModel events within sliding 24h window.
    """
    status_data = get_reviewer_budget_status(db, reviewer_id=reviewer_id)
    return ReviewerBudgetResponse(
        budget_total=status_data["budget_total"],
        budget_used=status_data["budget_used"],
        budget_remaining=status_data["budget_remaining"],
        utilization_rate=status_data["utilization_rate"],
        status=status_data["status"],
        window_hours=status_data["window_hours"],
        is_exhausted=status_data["is_exhausted"],
        is_warning=status_data["is_warning"],
        active_reviewer=status_data["active_reviewer"]
    )

@router.get("/oversight/drills", response_model=List[AttentionDrillResponse])
def list_attention_drills(db: Session = Depends(get_db)):
    """
    Feature B3: Lists synthetic reviewer-attention drills.
    Each drill tests identification of prompt injections, exfiltration, or dangerous commands.
    """
    drills = db.query(AttentionDrillModel).order_by(AttentionDrillModel.created_at.desc()).all()
    return [
        AttentionDrillResponse(
            id=d.id,
            title=d.title,
            description=d.description,
            scenario_type=d.scenario_type,
            target=d.target,
            action_details=json.loads(d.action_details_json) if d.action_details_json else None,
            expected_decision=d.expected_decision,
            is_simulation=d.is_simulation,
            status=d.status,
            reviewer_decision=d.reviewer_decision,
            reviewer_id=d.reviewer_id,
            reviewer_notes=d.reviewer_notes,
            responded_at=d.responded_at.isoformat() if d.responded_at else None,
            created_at=d.created_at.strftime("%I:%M %p")
        ) for d in drills
    ]

@router.post("/oversight/drills/{drill_id}/submit", response_model=DrillSubmissionResponse)
def submit_drill(drill_id: str, request: DrillSubmissionRequest, db: Session = Depends(get_db)):
    """
    Feature B3: Submits reviewer evaluation for an attention drill.
    Guarantees: Never executes mock tools. Updates oversight score based on accuracy.
    Enforces backend reviewer authorization.
    """
    # Enforce backend reviewer authorization
    verify_reviewer_authorization(request.reviewer_id, "attention drill submission")

    try:
        result = submit_drill_response(
            db=db,
            drill_id=drill_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            notes=request.notes
        )
        return DrillSubmissionResponse(
            drill_id=result["drill_id"],
            status=result["status"],
            is_correct=result["is_correct"],
            scenario_type=result["scenario_type"],
            reviewer_decision=result["reviewer_decision"],
            responded_at=result["responded_at"],
            message=result["message"]
        )
    except KeyError as ke:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ke))
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

@router.get("/oversight/restrictions", response_model=RestrictionStatusResponse)
def get_restrictions(db: Session = Depends(get_db)):
    """
    Feature B5: Current automatic restriction level and transition history.
    """
    latest_record = (
        db.query(RestrictionHistoryModel)
        .order_by(RestrictionHistoryModel.id.desc())
        .first()
    )

    if latest_record and latest_record.is_override:
        current_level = latest_record.level
        level_name = latest_record.level_name
        reason = latest_record.reason
    else:
        status_info = evaluate_and_apply_automatic_restrictions(db)
        current_level = status_info["current_level"]
        level_name = status_info["level_name"]
        reason = status_info["reason"]
    
    history_records = (
        db.query(RestrictionHistoryModel)
        .order_by(RestrictionHistoryModel.id.desc())
        .limit(10)
        .all()
    )

    return RestrictionStatusResponse(
        current_level=current_level,
        level_name=level_name,
        reason=reason,
        history=[
            RestrictionHistoryItem(
                id=h.id,
                level=h.level,
                level_name=h.level_name,
                reason=h.reason,
                authorized_by=h.authorized_by,
                is_override=h.is_override,
                created_at=h.created_at.strftime("%b %d, %I:%M %p")
            ) for h in history_records
        ]
    )

@router.post("/oversight/restrictions/override", response_model=RestrictionStatusResponse)
def override_restrictions(request: RestrictionOverrideRequest, db: Session = Depends(get_db)):
    """
    Feature B5: Manual authorized reviewer override for restriction level.
    Requires authorized reviewer ID and typed justification.
    """
    # Enforce backend reviewer authorization
    verify_reviewer_authorization(request.reviewer_id, "restriction override")

    if not request.reason or len(request.reason.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Typed justification of at least 10 characters required for manual restriction override."
        )

    override_record = RestrictionHistoryModel(
        level=request.level,
        level_name=RESTRICTION_NAMES.get(request.level, "CUSTOM"),
        reason=f"Manual reviewer override: {request.reason.strip()}",
        authorized_by=request.reviewer_id,
        is_override=True,
        created_at=datetime.utcnow()
    )
    db.add(override_record)

    metric = db.query(OversightMetricModel).first()
    if metric:
        metric.active_restrictions = request.level
    db.commit()

    create_audit_event(
        db=db,
        title="Restriction Level Override",
        description=f"Reviewer {request.reviewer_id} set restriction level to {request.level} ({RESTRICTION_NAMES.get(request.level)}): {request.reason}",
        status_tag="WARNING" if request.level > 0 else "INFO",
        metadata={"reviewer_id": request.reviewer_id, "level": request.level}
    )

    return get_restrictions(db)
