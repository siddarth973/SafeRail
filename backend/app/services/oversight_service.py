import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.models.safety import (
    ApprovalModel,
    ActionModel,
    AttentionDrillModel,
    OversightSnapshotModel,
    RestrictionHistoryModel,
    OversightMetricModel,
    AgentModel
)
from app.services.audit_service import create_audit_event

# Restriction Levels
RESTRICTION_LEVEL_0 = 0  # NORMAL: Healthy oversight
RESTRICTION_LEVEL_1 = 1  # ELEVATED: Warning state, bundling disabled, scrutiny on sensitive tools
RESTRICTION_LEVEL_2 = 2  # STRICT: Poor oversight, Tier 1 needs approval, budget capped
RESTRICTION_LEVEL_3 = 3  # EMERGENCY: Critical oversight or fail-closed, emergency hold

RESTRICTION_NAMES = {
    0: "NORMAL",
    1: "ELEVATED",
    2: "STRICT",
    3: "EMERGENCY"
}

DEFAULT_BUDGET_TOTAL = 100
DEFAULT_BUDGET_WINDOW_HOURS = 24
WARNING_BUDGET_PERCENT = 80.0

def get_reviewer_budget_status(
    db: Session,
    reviewer_id: Optional[str] = None,
    window_hours: int = DEFAULT_BUDGET_WINDOW_HOURS,
    budget_total: int = DEFAULT_BUDGET_TOTAL
) -> Dict[str, Any]:
    """
    Feature B1: Calculates reviewer approval budget usage from actual stored ApprovalModel events.
    Window is sliding (default 24 hours).
    """
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    query = db.query(ApprovalModel).filter(
        ApprovalModel.used == True,
        ApprovalModel.executed_at >= cutoff
    )
    if reviewer_id:
        query = query.filter(ApprovalModel.reviewer_id == reviewer_id)

    budget_used = query.count()
    budget_remaining = max(0, budget_total - budget_used)
    utilization_rate = round((budget_used / budget_total) * 100.0, 1) if budget_total > 0 else 100.0

    if budget_used >= budget_total:
        status_label = "EXHAUSTED"
    elif utilization_rate >= WARNING_BUDGET_PERCENT:
        status_label = "WARNING"
    else:
        status_label = "HEALTHY"

    return {
        "budget_total": budget_total,
        "budget_used": budget_used,
        "budget_remaining": budget_remaining,
        "utilization_rate": utilization_rate,
        "status": status_label,
        "window_hours": window_hours,
        "is_exhausted": budget_used >= budget_total,
        "is_warning": utilization_rate >= WARNING_BUDGET_PERCENT,
        "active_reviewer": reviewer_id or "reviewer-kavya"
    }

def get_drill_metrics(db: Session) -> Dict[str, Any]:
    """
    Feature B3: Calculates drill metrics from actual AttentionDrillModel records.
    """
    drills = db.query(AttentionDrillModel).all()
    total_drills = len(drills)
    completed_drills = [d for d in drills if d.status in ("PASSED", "FAILED")]
    passed_drills = [d for d in completed_drills if d.status == "PASSED"]
    failed_drills = [d for d in completed_drills if d.status == "FAILED"]
    pending_drills = [d for d in drills if d.status == "PENDING"]

    pass_rate = round((len(passed_drills) / len(completed_drills)) * 100.0, 1) if completed_drills else None

    return {
        "total_drills": total_drills,
        "completed_count": len(completed_drills),
        "passed_count": len(passed_drills),
        "failed_count": len(failed_drills),
        "pending_count": len(pending_drills),
        "pass_rate": pass_rate
    }

def detect_rapid_approvals(db: Session, window_hours: int = 24, threshold_seconds: int = 3) -> int:
    """
    Detects consecutive approvals executed within threshold_seconds (rubber-stamping).
    """
    cutoff = datetime.utcnow() - timedelta(hours=window_hours)
    approvals = (
        db.query(ApprovalModel)
        .filter(ApprovalModel.used == True, ApprovalModel.executed_at >= cutoff)
        .order_by(ApprovalModel.executed_at.asc())
        .all()
    )

    rapid_count = 0
    for i in range(1, len(approvals)):
        prev_time = approvals[i - 1].executed_at
        curr_time = approvals[i].executed_at
        if prev_time and curr_time:
            delta = (curr_time - prev_time).total_seconds()
            if 0 <= delta < threshold_seconds:
                rapid_count += 1

    return rapid_count

def count_pending_high_risk_backlog(db: Session, max_pending_minutes: int = 5) -> int:
    """
    Counts pending Tier 2 / Tier 3 actions that have been waiting > max_pending_minutes.
    """
    cutoff = datetime.utcnow() - timedelta(minutes=max_pending_minutes)
    count = db.query(ActionModel).filter(
        ActionModel.status == "PENDING",
        ActionModel.risk_tier.in_(["Tier 2", "Tier 3"]),
        ActionModel.created_at <= cutoff
    ).count()
    return count

def calculate_oversight_health(
    db: Session,
    window_hours: int = 24,
    budget_total: int = DEFAULT_BUDGET_TOTAL
) -> Dict[str, Any]:
    """
    Feature B4: Deterministic Oversight Health Scoring Engine.
    Formula: 4 weighted pillars (each up to 25 points, total 0-100).
    Explicitly handles INSUFFICIENT_DATA instead of inventing scores.
    """
    # 1. Budget pillar (0-25 pts)
    budget = get_reviewer_budget_status(db, window_hours=window_hours, budget_total=budget_total)
    util = budget["utilization_rate"]
    if util < 60.0:
        budget_pts = 25
        budget_exp = f"Healthy budget utilization ({util}% used of {budget_total})."
    elif util < 80.0:
        budget_pts = 20
        budget_exp = f"Moderate workload ({util}% used of {budget_total})."
    elif util < 90.0:
        budget_pts = 12
        budget_exp = f"High workload warning ({util}% used of {budget_total})."
    elif util < 100.0:
        budget_pts = 5
        budget_exp = f"Critical budget proximity ({util}% used)."
    else:
        budget_pts = 0
        budget_exp = "Reviewer budget exhausted (rubber-stamping fatigue risk)."

    # 2. Drill accuracy pillar (0-25 pts)
    drill_stats = get_drill_metrics(db)
    pass_rate = drill_stats["pass_rate"]
    completed_drills = drill_stats["completed_count"]
    if completed_drills >= 2:
        if pass_rate == 100.0:
            drill_pts = 25
            drill_exp = f"Flawless drill detection ({completed_drills}/{completed_drills} suspicious simulations caught)."
        elif pass_rate >= 80.0:
            drill_pts = 18
            drill_exp = f"Good attention drill accuracy ({pass_rate}% passed)."
        elif pass_rate >= 60.0:
            drill_pts = 10
            drill_exp = f"Attention deficiency observed ({pass_rate}% passed)."
        else:
            drill_pts = 0
            drill_exp = f"Severe drill failure rate ({pass_rate}% passed, reviewer missed simulated threats)."
    elif completed_drills == 1:
        drill_pts = 15 if pass_rate == 100.0 else 5
        drill_exp = f"Limited drill sample (1 test completed, pass rate: {pass_rate}%)."
    else:
        drill_pts = 12  # Neutral baseline for 0 drills
        drill_exp = "No attention drills completed yet in period."

    # 3. Rapid approval anomaly pillar (0-25 pts)
    rapid_count = detect_rapid_approvals(db, window_hours=window_hours)
    if rapid_count == 0:
        rapid_pts = 25
        rapid_exp = "No rapid approval anomalies detected; review latencies are deliberate."
    elif rapid_count <= 2:
        rapid_pts = 15
        rapid_exp = f"{rapid_count} rapid approval sequence(s) detected (<3s interval)."
    else:
        rapid_pts = 5
        rapid_exp = f"Repeated rapid approval anomalies ({rapid_count} instances <3s apart; rubber-stamping pattern)."

    # 4. Pending high-risk backlog pillar (0-25 pts)
    backlog_count = count_pending_high_risk_backlog(db)
    if backlog_count == 0:
        backlog_pts = 25
        backlog_exp = "No neglected high-risk actions in review queue."
    elif backlog_count <= 2:
        backlog_pts = 18
        backlog_exp = f"{backlog_count} high-risk action(s) pending for >5 minutes."
    elif backlog_count <= 5:
        backlog_pts = 10
        backlog_exp = f"Review queue backlog: {backlog_count} high-risk actions waiting."
    else:
        backlog_pts = 0
        backlog_exp = f"Severe backlog: {backlog_count} high-risk actions stalled without reviewer decision."

    # Total score calculation
    raw_score = budget_pts + drill_pts + rapid_pts + backlog_pts
    final_score = max(0, min(100, raw_score))

    # Data sufficiency assessment:
    # If there are zero reviews recorded in the window AND zero drills completed,
    # we must report INSUFFICIENT_DATA rather than claiming healthy oversight.
    has_decision_data = budget["budget_used"] > 0
    has_drill_data = completed_drills > 0
    if not has_decision_data and not has_drill_data:
        data_sufficiency = "INSUFFICIENT_DATA"
        status_label = "INSUFFICIENT_DATA"
    else:
        data_sufficiency = "SUFFICIENT"
        if final_score >= 80:
            status_label = "HEALTHY"
        elif final_score >= 60:
            status_label = "WARNING"
        elif final_score >= 40:
            status_label = "POOR"
        else:
            status_label = "CRITICAL"

    breakdown = [
        {
            "metric": "Reviewer Workload & Budget",
            "measured_value": f"{budget['budget_used']}/{budget_total} ({util}%)",
            "points_earned": budget_pts,
            "max_points": 25,
            "explanation": budget_exp
        },
        {
            "metric": "Synthetic Attention Drills",
            "measured_value": f"{pass_rate}%" if pass_rate is not None else "No drills completed",
            "points_earned": drill_pts,
            "max_points": 25,
            "explanation": drill_exp
        },
        {
            "metric": "Approval Velocity Consistency",
            "measured_value": f"{rapid_count} rapid approvals (<3s)",
            "points_earned": rapid_pts,
            "max_points": 25,
            "explanation": rapid_exp
        },
        {
            "metric": "High-Risk Queue Throughput",
            "measured_value": f"{backlog_count} backlogged actions (>5m)",
            "points_earned": backlog_pts,
            "max_points": 25,
            "explanation": backlog_exp
        }
    ]

    return {
        "score": final_score,
        "status": status_label,
        "data_sufficiency": data_sufficiency,
        "breakdown": breakdown,
        "budget": budget,
        "drills": drill_stats,
        "rapid_approvals": rapid_count,
        "pending_backlog": backlog_count,
        "calculated_at": datetime.utcnow().isoformat()
    }

def evaluate_and_apply_automatic_restrictions(db: Session) -> Dict[str, Any]:
    """
    Feature B5: Evaluates oversight health and synchronizes automatic safety restrictions.
    Implements fail-closed posture: failures elevate restrictions to EMERGENCY.
    """
    try:
        health = calculate_oversight_health(db)
        score = health["score"]
        status_label = health["status"]
        budget = health["budget"]

        # Determine target restriction level
        if status_label == "CRITICAL" or score < 40:
            target_level = RESTRICTION_LEVEL_3
            reason = f"Oversight quality Critical (Score: {score}/100). Conservative safety fallback engaged."
        elif status_label == "POOR" or score < 60 or budget["is_exhausted"]:
            target_level = RESTRICTION_LEVEL_2
            reason = f"Oversight quality Poor (Score: {score}/100, Budget exhausted: {budget['is_exhausted']}). Strict verification required."
        elif status_label == "WARNING" or score < 80 or budget["is_warning"]:
            target_level = RESTRICTION_LEVEL_1
            reason = f"Oversight quality Warning (Score: {score}/100). Bundling disabled; elevated review scrutiny."
        elif status_label == "INSUFFICIENT_DATA":
            target_level = RESTRICTION_LEVEL_1
            reason = "Insufficient oversight observations; conservative elevated scrutiny active."
        else:
            target_level = RESTRICTION_LEVEL_0
            reason = f"Oversight Healthy (Score: {score}/100). Normal baseline security policies active."

    except Exception as e:
        # FAIL-CLOSED: if scoring calculation fails, default to Level 3 Emergency
        target_level = RESTRICTION_LEVEL_3
        reason = f"Oversight service calculation failure ({str(e)}). Fail-closed conservative fallback active."
        health = {"score": 0, "status": "CRITICAL", "data_sufficiency": "INSUFFICIENT_DATA"}

    # Fetch latest recorded restriction state
    latest_record = (
        db.query(RestrictionHistoryModel)
        .order_by(RestrictionHistoryModel.id.desc())
        .first()
    )

    current_level = latest_record.level if latest_record else 0

    # Respect active manual reviewer override unless fail-closed emergency escalation engages
    if latest_record and latest_record.is_override:
        if target_level < RESTRICTION_LEVEL_3:
            return {
                "current_level": current_level,
                "level_name": latest_record.level_name,
                "reason": latest_record.reason,
                "health": health
            }

    # If level changes and no recent duplicate record, record transition
    if current_level != target_level:
        transition = RestrictionHistoryModel(
            level=target_level,
            level_name=RESTRICTION_NAMES.get(target_level, "UNKNOWN"),
            reason=reason,
            trigger_metrics_json=json.dumps({
                "score": health.get("score"),
                "status": health.get("status"),
                "target_level": target_level
            }),
            authorized_by="SYSTEM_AUTOMATION",
            is_override=False,
            created_at=datetime.utcnow()
        )
        db.add(transition)

        # Update summary oversight metric model for UI gauge
        metric_summary = db.query(OversightMetricModel).first()
        if metric_summary:
            metric_summary.active_restrictions = target_level
            metric_summary.reviewer_health = health.get("score", 50)
            metric_summary.reviewer_health_status = health.get("status", "Normal")
            db.commit()

        # Audit event for restriction change
        create_audit_event(
            db=db,
            title="Automatic Restriction Change",
            description=f"Security level shifted to {RESTRICTION_NAMES.get(target_level)}: {reason}",
            status_tag="WARNING" if target_level > 0 else "INFO",
            metadata={"new_level": target_level, "score": health.get("score")}
        )

    # If critical level (Level 3), verify if any agents need pausing per configuration
    if target_level == RESTRICTION_LEVEL_3:
        # Pause agents that do not have active emergency immunity
        agents = db.query(AgentModel).filter(AgentModel.status == "ACTIVE").all()
        for ag in agents:
            if ag.type in ("executor", "analytics"):
                ag.status = "PAUSED"
                create_audit_event(
                    db=db,
                    title="Agent Auto-Paused by Oversight",
                    description=f"Agent '{ag.id}' automatically paused due to Critical Oversight Health (Level 3).",
                    status_tag="WARNING",
                    metadata={"agent_id": ag.id, "restriction_level": 3}
                )
        db.commit()

    return {
        "current_level": target_level,
        "level_name": RESTRICTION_NAMES.get(target_level, "NORMAL"),
        "reason": reason,
        "health": health
    }

def get_current_restriction_level(db: Session) -> int:
    """Helper to query the currently active restriction level."""
    latest = (
        db.query(RestrictionHistoryModel)
        .order_by(RestrictionHistoryModel.id.desc())
        .first()
    )
    return latest.level if latest else RESTRICTION_LEVEL_0

def submit_drill_response(
    db: Session,
    drill_id: str,
    reviewer_id: str,
    decision: str,
    notes: Optional[str] = None
) -> Dict[str, Any]:
    """
    Feature B3: Submits reviewer evaluation for an attention drill.
    Guarantees:
      - NEVER executes any mock tool or real payload.
      - Records reviewer accuracy and timestamp.
      - Simulates suspicious prompt injections, sensitive exports, or destructive operations.
    """
    clean_decision = decision.upper().strip()
    if clean_decision not in ("APPROVED", "REJECTED"):
        raise ValueError("Drill decision must be 'APPROVED' or 'REJECTED'.")

    drill = db.query(AttentionDrillModel).filter(AttentionDrillModel.id == drill_id).first()
    if not drill:
        raise KeyError(f"Attention drill '{drill_id}' does not exist.")

    # Attention drills are designed with suspicious/dangerous parameters,
    # so the correct, attentive reviewer action is always REJECTED.
    is_correct = (clean_decision == drill.expected_decision)
    new_status = "PASSED" if is_correct else "FAILED"

    drill.status = new_status
    drill.reviewer_decision = clean_decision
    drill.reviewer_id = reviewer_id
    drill.reviewer_notes = notes or ("Identified drill threat accurately" if is_correct else "Failed to flag simulated drill threat")
    drill.responded_at = datetime.utcnow()
    db.commit()

    # Log to audit trail with explicit synthetic simulation tag
    create_audit_event(
        db=db,
        title="Attention Drill Evaluated",
        description=f"Drill {drill.id} ({drill.scenario_type}): Reviewer {reviewer_id} responded {clean_decision} -> {new_status} (Never Executed)",
        status_tag="APPROVED" if is_correct else "WARNING",
        metadata={
            "drill_id": drill.id,
            "is_simulation": True,
            "status": new_status,
            "reviewer_id": reviewer_id
        }
    )

    # Re-evaluate automatic restrictions with updated drill performance
    evaluate_and_apply_automatic_restrictions(db)

    return {
        "drill_id": drill.id,
        "status": new_status,
        "is_correct": is_correct,
        "scenario_type": drill.scenario_type,
        "reviewer_decision": clean_decision,
        "responded_at": drill.responded_at.isoformat(),
        "message": "Drill completed successfully. No tool was executed."
    }
