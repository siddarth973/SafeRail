from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import AgentModel, OversightMetricModel
from app.schemas.safety import AgentResumeRequest, AgentStatusActionResponse
from app.services.audit_service import create_audit_event
from app.core.auth import verify_reviewer_authorization

router = APIRouter()

@router.post("/agents/{agent_id}/pause", response_model=AgentStatusActionResponse)
def pause_agent(agent_id: str, reason: Optional[str] = "Manual safety pause initiated", db: Session = Depends(get_db)):
    """
    Pauses an individual agent (Feature A5).
    Paused agents cannot execute new actions or pending approvals.
    """
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found.")

    agent.status = "PAUSED"
    agent.updated_at = datetime.utcnow()

    timestamp_str = datetime.utcnow().strftime("%I:%M %p")
    create_audit_event(
        db=db,
        title="Agent Paused",
        description=f"{agent.name} ({agent_id}) paused: {reason}",
        status_tag="WARNING",
        time_str=timestamp_str,
        metadata={"agent_id": agent.id, "reason": reason}
    )

    return AgentStatusActionResponse(
        agent_id=agent.id,
        status="PAUSED",
        message=f"Agent '{agent.name}' is now PAUSED. All further actions are blocked."
    )

@router.post("/agents/{agent_id}/resume", response_model=AgentStatusActionResponse)
def resume_agent(agent_id: str, request: AgentResumeRequest, db: Session = Depends(get_db)):
    """
    Resumes a paused agent (Feature A5).
    Requires authorized reviewer_id and typed justification.
    Checks reviewer health: if health score < 50, applies conservative rule rejecting resume.
    """
    agent = db.query(AgentModel).filter(AgentModel.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent '{agent_id}' not found.")

    # Enforce backend reviewer authorization
    verify_reviewer_authorization(request.reviewer_id, "agent resumption")

    if not request.reason or len(request.reason.strip()) < 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A meaningful typed justification (at least 5 characters) is required to resume an agent."
        )

    # Conservative Reviewer Health Guard (Feature B4/B5 prerequisite)
    oversight = db.query(OversightMetricModel).first()
    if oversight and oversight.reviewer_health < 50:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Conservative safety lock: Reviewer oversight health is degraded ({oversight.reviewer_health}/100). Secondary administrator authorization required."
        )

    agent.status = "ACTIVE"
    agent.updated_at = datetime.utcnow()

    timestamp_str = datetime.utcnow().strftime("%I:%M %p")
    create_audit_event(
        db=db,
        title="Agent Resumed",
        description=f"{agent.name} resumed by {request.reviewer_id}: {request.reason}",
        status_tag="INFO",
        time_str=timestamp_str,
        metadata={"agent_id": agent.id, "reviewer_id": request.reviewer_id, "reason": request.reason}
    )

    return AgentStatusActionResponse(
        agent_id=agent.id,
        status="ACTIVE",
        message=f"Agent '{agent.name}' successfully resumed by {request.reviewer_id}."
    )

@router.post("/agents/pause-all", response_model=dict)
def pause_all_agents(reason: Optional[str] = "Global emergency killswitch activated", db: Session = Depends(get_db)):
    """
    Emergency Killswitch: Pauses all agents across the entire system.
    """
    agents = db.query(AgentModel).all()
    count = 0
    for agent in agents:
        agent.status = "PAUSED"
        agent.updated_at = datetime.utcnow()
        count += 1

    timestamp_str = datetime.utcnow().strftime("%I:%M %p")
    create_audit_event(
        db=db,
        title="Emergency Killswitch",
        description=f"Global safety hold: All {count} agents paused ({reason})",
        status_tag="BLOCKED",
        time_str=timestamp_str,
        metadata={"agents_count": count, "reason": reason}
    )

    return {
        "status": "ALL_PAUSED",
        "agents_paused": count,
        "message": f"Global emergency killswitch activated. {count} agents paused."
    }
