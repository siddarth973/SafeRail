import csv
import io
import json
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import (
    ActionModel,
    ApprovalModel,
    AgentModel,
    SecurityEventModel,
    AttentionDrillModel,
    RestrictionHistoryModel
)
from app.schemas.safety import EvidenceReportResponse
from app.services.oversight_service import (
    calculate_oversight_health,
    get_reviewer_budget_status,
    get_drill_metrics,
    get_current_restriction_level,
    RESTRICTION_NAMES
)
from app.services.audit_service import verify_entire_audit_chain

router = APIRouter()

def generate_evidence_report_data(db: Session, period: str = "24h") -> dict:
    """
    Feature B6: Generates comprehensive compliance and oversight evidence report.
    All metrics are derived directly from actual database records (no hardcoded fixtures).
    """
    now = datetime.utcnow()
    if period == "24h":
        cutoff = now - timedelta(hours=24)
        period_label = "Last 24 Hours"
    elif period == "7d":
        cutoff = now - timedelta(days=7)
        period_label = "Last 7 Days"
    else:
        cutoff = datetime(2000, 1, 1)
        period_label = "All Time (Complete History)"

    # 1. Action statistics
    actions = db.query(ActionModel).filter(ActionModel.created_at >= cutoff).all()
    total_actions = len(actions)
    allow_count = sum(1 for a in actions if a.decision == "ALLOW")
    block_count = sum(1 for a in actions if a.decision == "BLOCK")
    hold_count = sum(1 for a in actions if a.decision == "HOLD")

    tier_dist = {
        "Tier 0": sum(1 for a in actions if a.risk_tier == "Tier 0"),
        "Tier 1": sum(1 for a in actions if a.risk_tier == "Tier 1"),
        "Tier 2": sum(1 for a in actions if a.risk_tier == "Tier 2"),
        "Tier 3": sum(1 for a in actions if a.risk_tier == "Tier 3"),
        "Tier X": sum(1 for a in actions if a.risk_tier == "Tier X"),
    }

    # 2. Human approval outcomes
    approvals = db.query(ApprovalModel).filter(ApprovalModel.created_at >= cutoff).all()
    approved_count = sum(1 for ap in approvals if ap.decision == "APPROVED")
    rejected_count = sum(1 for ap in approvals if ap.decision == "REJECTED")

    # 3. Budget utilization
    budget = get_reviewer_budget_status(db, window_hours=24)

    # 4. Oversight health score
    health = calculate_oversight_health(db, window_hours=24)

    # 5. Attention drill performance
    drill_stats = get_drill_metrics(db)

    # 6. Safety restrictions & Agent status
    current_level = get_current_restriction_level(db)
    paused_agents = [ag.id for ag in db.query(AgentModel).filter(AgentModel.status.in_(["PAUSED", "FROZEN"])).all()]

    # 7. Cryptographic audit chain verification
    chain_audit = verify_entire_audit_chain(db)

    return {
        "report_id": f"SR-EVID-{now.strftime('%Y%m%d%H%M%S')}",
        "generated_at": now.isoformat(),
        "reporting_period": period_label,
        "total_actions": total_actions,
        "allow_count": allow_count,
        "block_count": block_count,
        "hold_count": hold_count,
        "risk_tier_distribution": tier_dist,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "budget_used": budget["budget_used"],
        "budget_total": budget["budget_total"],
        "oversight_score": health["score"],
        "oversight_status": health["status"],
        "data_sufficiency": health["data_sufficiency"],
        "drill_pass_rate": drill_stats["pass_rate"],
        "active_restriction_level": current_level,
        "restriction_level_name": RESTRICTION_NAMES.get(current_level, "NORMAL"),
        "paused_agents": paused_agents,
        "audit_chain_status": chain_audit["status"],
        "valid_blocks": chain_audit["valid_count"],
        "invalid_blocks": chain_audit["invalid_count"],
        "unverifiable_blocks": chain_audit["unverifiable_count"],
        "total_audit_records": chain_audit["total_events"]
    }

@router.get("/evidence/report", response_model=EvidenceReportResponse)
def get_evidence_report(
    period: str = Query("24h", description="Reporting period: 24h, 7d, or all"),
    db: Session = Depends(get_db)
):
    """
    Feature B6: Generates verifiable evidence report derived from real backend data.
    """
    data = generate_evidence_report_data(db, period=period)
    return EvidenceReportResponse(**data)

@router.get("/evidence/report.json")
def download_evidence_report_json(
    period: str = Query("24h", description="Reporting period: 24h, 7d, or all"),
    db: Session = Depends(get_db)
):
    """
    Feature B6: Downloads the evidence report as a JSON file.
    """
    data = generate_evidence_report_data(db, period=period)
    json_bytes = json.dumps(data, indent=2).encode('utf-8')
    filename = f"saferail-evidence-report-{period}-{datetime.utcnow().strftime('%Y%m%d')}.json"
    return Response(
        content=json_bytes,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/evidence/report.csv")
def download_evidence_report_csv(
    period: str = Query("24h", description="Reporting period: 24h, 7d, or all"),
    db: Session = Depends(get_db)
):
    """
    Feature B6: Downloads the evidence report as a structured CSV file.
    """
    data = generate_evidence_report_data(db, period=period)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["SafeRail Oversight & Compliance Evidence Report"])
    writer.writerow(["Report ID", data["report_id"]])
    writer.writerow(["Generated At", data["generated_at"]])
    writer.writerow(["Reporting Period", data["reporting_period"]])
    writer.writerow([])
    writer.writerow(["Gateway Action Metrics", "Count"])
    writer.writerow(["Total Actions Evaluated", data["total_actions"]])
    writer.writerow(["Actions Permitted (ALLOW)", data["allow_count"]])
    writer.writerow(["Actions Held for Review (HOLD)", data["hold_count"]])
    writer.writerow(["Actions Blocked (BLOCK)", data["block_count"]])
    writer.writerow([])
    writer.writerow(["Risk Tier Distribution", "Count"])
    for tier, count in data["risk_tier_distribution"].items():
        writer.writerow([tier, count])
    writer.writerow([])
    writer.writerow(["Human Review Decisions", "Count"])
    writer.writerow(["Human Approved", data["approved_count"]])
    writer.writerow(["Human Rejected", data["rejected_count"]])
    writer.writerow([])
    writer.writerow(["Oversight Intelligence Metrics", "Value"])
    writer.writerow(["Oversight Health Score", f"{data['oversight_score']}/100 ({data['oversight_status']})"])
    writer.writerow(["Data Sufficiency", data["data_sufficiency"]])
    writer.writerow(["Approval Budget Used", f"{data['budget_used']} / {data['budget_total']}"])
    writer.writerow(["Attention Drill Pass Rate", f"{data['drill_pass_rate']}%" if data['drill_pass_rate'] is not None else "N/A"])
    writer.writerow(["Active Restriction Level", f"Level {data['active_restriction_level']} ({data['restriction_level_name']})"])
    writer.writerow(["Paused Agents", ", ".join(data["paused_agents"]) if data["paused_agents"] else "None"])
    writer.writerow([])
    writer.writerow(["Cryptographic Audit Verification", "Count"])
    writer.writerow(["Overall Chain Consensus", data["audit_chain_status"]])
    writer.writerow(["Valid Signed Blocks", data["valid_blocks"]])
    writer.writerow(["Invalid / Broken Blocks", data["invalid_blocks"]])
    writer.writerow(["Unverifiable Legacy Records", data["unverifiable_blocks"]])
    writer.writerow(["Total Audit Ledger Entries", data["total_audit_records"]])

    csv_data = output.getvalue().encode('utf-8')
    filename = f"saferail-evidence-report-{period}-{datetime.utcnow().strftime('%Y%m%d')}.csv"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
