import json
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.safety import (
    AgentModel,
    ActionModel,
    ApprovalModel,
    SecurityEventModel,
    UntrustedContentModel
)
from app.schemas.safety import (
    ToolCallRequest,
    ToolCallResponse,
    PendingApprovalResponse,
    ApprovalDecisionRequest,
    ApprovalDecisionResponse,
    BundleApprovalDecisionRequest,
    BundleApprovalDecisionResponse
)
from app.services.policy_engine import (
    evaluate_action,
    compute_action_fingerprint,
    DECISION_ALLOW,
    DECISION_HOLD,
    DECISION_BLOCK,
    TIER_X
)
from app.services.mock_tools import execute_mock_tool, MockToolExecutionError
from app.services.audit_service import create_audit_event
from app.core.auth import verify_reviewer_authorization
from app.services.oversight_service import (
    get_reviewer_budget_status,
    get_current_restriction_level,
    evaluate_and_apply_automatic_restrictions,
    RESTRICTION_LEVEL_1,
    RESTRICTION_LEVEL_2,
    RESTRICTION_LEVEL_3
)

def get_tier3_confirmation_phrase(action: ActionModel) -> str:
    """Computes deterministic confirmation phrase for Tier 3 review friction."""
    clean_target = str(action.target).replace(" ", "_").strip()
    if action.tool_name == "delete_records":
        return f"CONFIRM-DELETE-{clean_target}"
    elif action.tool_name == "send_email":
        return f"CONFIRM-EMAIL-{clean_target}"
    elif action.tool_name == "issue_refund":
        return f"CONFIRM-REFUND-{clean_target}"
    else:
        tool_tag = (action.tool_name or "ACTION").upper()
        return f"CONFIRM-{tool_tag}-{clean_target}"


router = APIRouter()

@router.post("/tool_call", response_model=ToolCallResponse)
def handle_tool_call(request: ToolCallRequest, db: Session = Depends(get_db)):
    """
    Core Security Gateway Interceptor (Feature A1).
    Every simulated agent action passes through here before any tool execution.
    Applies fail-closed logic: if safety checks fail or error occurs, action is blocked.
    """
    timestamp_str = datetime.utcnow().strftime("%I:%M %p")
    
    # 1. Lookup agent and check status
    agent = db.query(AgentModel).filter(AgentModel.id == request.agent_id).first()
    agent_status = agent.status if agent else "ACTIVE"
    agent_name = agent.name if agent else f"Agent ({request.agent_id})"

    # Fail-closed wrapper around policy evaluation
    try:
        eval_result = evaluate_action(
            tool_name=request.tool_name,
            action_details=request.action_details,
            agent_id=request.agent_id,
            agent_status=agent_status,
            session_id=request.session_id,
            untrusted_content_ids=request.untrusted_content_ids,
            db=db
        )
    except Exception as eval_err:
        # Gateway FAIL-CLOSED behavior on unexpected evaluation exception
        block_action = ActionModel(
            agent_id=request.agent_id,
            session_id=request.session_id,
            tool_name=request.tool_name,
            action_type=request.tool_name.replace("_", " ").title(),
            description=f"Action aborted: Gateway fail-closed error ({str(eval_err)})",
            agent_name=agent_name,
            target=str(request.action_details.get("target") or request.action_details.get("to") or "unknown"),
            action_details=json.dumps(request.action_details),
            risk_score=100,
            risk_tier=TIER_X,
            risk_level="HIGH",
            policy_matches=json.dumps(["POL-FAIL-CLOSED-ERROR"]),
            reason=f"Gateway fail-closed: internal evaluation error ({str(eval_err)})",
            decision=DECISION_BLOCK,
            status="BLOCKED",
            execution_status="BLOCKED",
            timestamp=timestamp_str
        )
        db.add(block_action)
        db.commit()
        db.refresh(block_action)

        create_audit_event(
            db=db,
            title="Gateway Fail-Closed",
            description=f"Blocked {request.tool_name} for {agent_name}: internal error",
            status_tag="BLOCKED",
            time_str=timestamp_str,
            metadata={"agent_id": request.agent_id, "action_id": block_action.id}
        )

        return ToolCallResponse(
            action_id=block_action.id,
            decision=DECISION_BLOCK,
            risk_score=100,
            risk_tier=TIER_X,
            risk_level="HIGH",
            reason=f"Gateway fail-closed: policy evaluation error ({str(eval_err)})",
            policy_matches=["POL-FAIL-CLOSED-ERROR"],
            execution_status="BLOCKED",
            timestamp=timestamp_str,
            fingerprint=None,
            execution_result=None
        )

    # Determine display target for dashboard consistency
    target = (
        request.action_details.get("to")
        or request.action_details.get("target")
        or request.action_details.get("customer_id")
        or request.action_details.get("ticket_id")
        or request.action_details.get("record_type")
        or request.action_details.get("user_id")
        or "system_config"
    )

    action_type = request.tool_name.replace("_", " ").title()
    desc = f"{action_type} for {target}"
    if request.tool_name == "issue_refund":
        desc = f"Process refund - ${float(request.action_details.get('amount', 0)):.2f}"
    elif request.tool_name == "send_email":
        desc = f"Send email to {target}"
    elif request.tool_name == "delete_records":
        desc = f"Delete {target} data"
    elif request.tool_name == "update_profile":
        desc = f"Change user profile - {target}"

    # Compute exact-action canonical fingerprint
    fingerprint = compute_action_fingerprint(
        tool_name=request.tool_name,
        action_details=request.action_details,
        agent_id=request.agent_id,
        session_id=request.session_id
    )

    execution_status = "PENDING_APPROVAL"
    execution_result = None

    active_level = get_current_restriction_level(db)
    if active_level >= RESTRICTION_LEVEL_3:
        # Emergency lockdown (Level 3): fail-closed posture freezes automated executions
        if eval_result.decision == DECISION_ALLOW:
            eval_result.decision = DECISION_BLOCK
            eval_result.reason = f"Emergency oversight lockdown active (Restriction Level 3). Automated execution of '{request.tool_name}' halted fail-closed."
            eval_result.policy_matches.append("POL-EMERGENCY-LOCKDOWN")
            execution_status = "BLOCKED"

    if eval_result.decision == DECISION_ALLOW:
        execution_status = "EXECUTED"
        # Execute mock tool in safe sandbox
        try:
            execution_result = execute_mock_tool(
                tool_name=request.tool_name,
                action_details=request.action_details,
                db=db
            )
        except Exception as tool_err:
            execution_status = "FAILED"
            execution_result = {"error": str(tool_err)}

    elif eval_result.decision == DECISION_BLOCK:
        execution_status = "BLOCKED"

    # Persist Action in database
    action = ActionModel(
        agent_id=request.agent_id,
        session_id=request.session_id,
        tool_name=request.tool_name,
        action_type=action_type,
        description=desc,
        agent_name=agent_name,
        target=str(target),
        action_details=json.dumps(request.action_details),
        untrusted_content_ids=json.dumps(request.untrusted_content_ids or []),
        risk_score=eval_result.risk_score,
        risk_tier=eval_result.risk_tier,
        risk_level=eval_result.risk_level,
        policy_matches=json.dumps(eval_result.policy_matches),
        reason=eval_result.reason,
        decision=eval_result.decision,
        status="PENDING" if eval_result.decision == DECISION_HOLD else ("APPROVED" if eval_result.decision == DECISION_ALLOW else "BLOCKED"),
        execution_status=execution_status,
        fingerprint=fingerprint,
        timestamp=timestamp_str
    )
    db.add(action)
    db.commit()
    db.refresh(action)

    # If action requires approval (HOLD), create Approval record with 10-minute expiry
    if eval_result.decision == DECISION_HOLD:
        approval = ApprovalModel(
            action_id=action.id,
            fingerprint=fingerprint,
            decision="PENDING",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
            used=False
        )
        db.add(approval)
        db.commit()

        # Log Security Warning/Hold
        create_audit_event(
            db=db,
            title="Action Held for Approval",
            description=f"{action_type}: {desc} ({eval_result.risk_tier})",
            status_tag="WARNING",
            time_str=timestamp_str,
            metadata={"action_id": action.id, "fingerprint": fingerprint, "risk_tier": eval_result.risk_tier}
        )

    elif eval_result.decision == DECISION_BLOCK:
        # Log Security Block
        create_audit_event(
            db=db,
            title="Action Blocked",
            description=f"{action_type}: {desc} ({eval_result.reason})",
            status_tag="BLOCKED",
            time_str=timestamp_str,
            metadata={"action_id": action.id, "reason": eval_result.reason}
        )

    elif eval_result.decision == DECISION_ALLOW:
        # Log Allowed Execution
        create_audit_event(
            db=db,
            title="Action Permitted",
            description=f"{action_type}: {desc}",
            status_tag="APPROVED",
            time_str=timestamp_str,
            metadata={"action_id": action.id}
        )

    return ToolCallResponse(
        action_id=action.id,
        decision=eval_result.decision,
        risk_score=eval_result.risk_score,
        risk_tier=eval_result.risk_tier,
        risk_level=eval_result.risk_level,
        reason=eval_result.reason,
        policy_matches=eval_result.policy_matches,
        execution_status=execution_status,
        timestamp=timestamp_str,
        fingerprint=fingerprint,
        execution_result=execution_result
    )

@router.get("/pending", response_model=List[PendingApprovalResponse])
def get_pending_approvals(db: Session = Depends(get_db)):
    """
    Returns all active actions placed on HOLD awaiting human review (Feature A4).
    Includes exact action details, canonical fingerprint, and time remaining.
    """
    now = datetime.utcnow()
    # Query pending approvals that are not expired and not used
    pending_approvals = (
        db.query(ApprovalModel, ActionModel)
        .join(ActionModel, ApprovalModel.action_id == ActionModel.id)
        .filter(
            ApprovalModel.decision == "PENDING",
            ApprovalModel.used == False,
            ApprovalModel.expires_at > now,
            ActionModel.status == "PENDING"
        )
        .all()
    )

    results = []
    for approval, action in pending_approvals:
        remaining_seconds = max(0, int((approval.expires_at - now).total_seconds()))
        details = {}
        try:
            details = json.loads(action.action_details) if action.action_details else {}
        except Exception:
            details = {"target": action.target}

        results.append(
            PendingApprovalResponse(
                action_id=action.id,
                tool_name=action.tool_name or "action",
                action_type=action.action_type,
                agent_id=action.agent_id or "unknown",
                agent_name=action.agent_name,
                target=action.target,
                action_details=details,
                risk_tier=action.risk_tier or "Tier 2",
                risk_score=action.risk_score or 50,
                risk_level=action.risk_level or "MEDIUM",
                reason=action.reason or "Awaiting reviewer authorization",
                fingerprint=approval.fingerprint,
                created_at=approval.created_at.strftime("%I:%M %p"),
                expires_at=approval.expires_at.strftime("%I:%M %p"),
                seconds_remaining=remaining_seconds,
                required_confirmation_phrase=get_tier3_confirmation_phrase(action) if action.risk_tier == "Tier 3" else None
            )
        )

    return results

@router.post("/decide", response_model=ApprovalDecisionResponse)
def decide_approval(request: ApprovalDecisionRequest, db: Session = Depends(get_db)):
    """
    Reviewer Decision Endpoint with Exact-Action Fingerprint Binding (Feature A4).
    Validates:
      1. Action exists in PENDING state.
      2. Associated agent is not PAUSED or FROZEN.
      3. Approval exists, is PENDING, not used, and not expired.
      4. Canonical fingerprint matches exact stored action details (tamper detection).
    Executes mock tool only upon valid APPROVED decision.
    """
    decision_clean = request.decision.upper().strip()
    if decision_clean not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be either 'APPROVED' or 'REJECTED'."
        )

    # Enforce backend reviewer authorization
    verify_reviewer_authorization(request.reviewer_id, "action approval decision")

    action = db.query(ActionModel).filter(ActionModel.id == request.action_id).first()
    if not action:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action not found.")

    # Mandatory Tier X prohibitions can NEVER be approved under any oversight restriction level
    if action.risk_tier == "Tier X" or action.risk_score >= 90 or action.decision == "BLOCK":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mandatory Tier X prohibited actions cannot be approved under any oversight restriction level."
        )

    if action.status != "PENDING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Action is not pending approval (current status: {action.status})."
        )

    # Agent lifecycle check: cannot execute approvals for paused agent
    agent = db.query(AgentModel).filter(AgentModel.id == action.agent_id).first()
    if agent and agent.status in ("PAUSED", "FROZEN"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot approve action: Agent '{agent.id}' is currently {agent.status}. Resume agent first."
        )

    # Lookup approval record
    approval = db.query(ApprovalModel).filter(ApprovalModel.action_id == action.id).first()
    if not approval:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approval record associated with this action."
        )

    # Verify not already used
    if approval.used:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Approval token has already been used (single-use constraint)."
        )

    # Verify not expired
    now = datetime.utcnow()
    if approval.expires_at < now:
        action.status = "BLOCKED"
        action.execution_status = "BLOCKED"
        approval.used = True
        approval.decision = "EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Approval request has expired (time-bounded constraint: 10 minutes max)."
        )

    # Exact-Action Fingerprint Verification: Recompute and compare
    try:
        details_obj = json.loads(action.action_details) if action.action_details else {}
    except Exception:
        details_obj = {}

    expected_fingerprint = compute_action_fingerprint(
        tool_name=action.tool_name or "",
        action_details=details_obj,
        agent_id=action.agent_id or "",
        session_id=action.session_id or ""
    )

    if expected_fingerprint != approval.fingerprint:
        # Fingerprint mismatch -> Payload tampering detected!
        action.status = "BLOCKED"
        action.execution_status = "BLOCKED"
        approval.used = True
        approval.decision = "REJECTED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fingerprint mismatch: Action parameters or context were modified after approval generation."
        )

    timestamp_str = now.strftime("%I:%M %p")

    if decision_clean == "APPROVED":
        # Feature B5: Check if Emergency restriction lockdown is active
        active_level = get_current_restriction_level(db)
        if active_level >= RESTRICTION_LEVEL_3:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Emergency oversight lockdown active (Restriction Level 3). Human approvals are temporarily frozen."
            )

        # Feature B1: Check Reviewer Approval Budget exhaustion
        budget_status = get_reviewer_budget_status(db, reviewer_id=request.reviewer_id)
        if budget_status["is_exhausted"] and action.risk_tier in ("Tier 2", "Tier 3"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Reviewer approval budget exhausted ({budget_status['budget_used']}/{budget_status['budget_total']}). Additional high-risk reviews restricted to prevent rubber-stamping."
            )

        # Feature B2: Risk-Matched Review Friction
        if action.risk_tier == "Tier 3":
            expected_phrase = get_tier3_confirmation_phrase(action)
            supplied_phrase = (request.confirmation_phrase or "").strip()
            if supplied_phrase != expected_phrase:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Tier 3 elevated-risk review friction: Exact confirmation phrase required ('{expected_phrase}')."
                )
        elif active_level >= RESTRICTION_LEVEL_2 and action.risk_tier == "Tier 2":
            # Strict mode elevates Tier 2 to require confirmation phrase
            expected_phrase = f"CONFIRM-TIER2-{(action.tool_name or 'ACTION').upper()}"
            supplied_phrase = (request.confirmation_phrase or "").strip()
            if supplied_phrase != expected_phrase:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Strict oversight active (Level 2): Tier 2 confirmation phrase required ('{expected_phrase}')."
                )

        # Mark approval as used
        approval.decision = "APPROVED"
        approval.reviewer_id = request.reviewer_id
        approval.reason = request.reason or "Authorized by reviewer"
        approval.used = True
        approval.executed_at = now

        action.status = "APPROVED"
        action.execution_status = "EXECUTED"

        # Execute the exact approved mock tool
        execution_result = None
        try:
            execution_result = execute_mock_tool(
                tool_name=action.tool_name or "",
                action_details=details_obj,
                action_id=action.id,
                db=db
            )
        except Exception as e:
            action.execution_status = "FAILED"
            execution_result = {"error": str(e)}

        create_audit_event(
            db=db,
            title="Human Approval",
            description=f"{action.action_type}: Approved by {request.reviewer_id}",
            status_tag="APPROVED",
            time_str=timestamp_str,
            metadata={"action_id": action.id, "reviewer_id": request.reviewer_id}
        )

        try:
            evaluate_and_apply_automatic_restrictions(db)
        except Exception:
            pass

        return ApprovalDecisionResponse(
            action_id=action.id,
            decision="APPROVED",
            status="APPROVED",
            executed=True,
            execution_result=execution_result,
            message="Action approved and executed successfully."
        )

    else:
        # REJECTED
        approval.decision = "REJECTED"
        approval.reviewer_id = request.reviewer_id
        approval.reason = request.reason or "Rejected by reviewer"
        approval.used = True

        action.status = "BLOCKED"
        action.execution_status = "BLOCKED"

        create_audit_event(
            db=db,
            title="Approval Rejected",
            description=f"{action.action_type}: Blocked by reviewer {request.reviewer_id}",
            status_tag="BLOCKED",
            time_str=timestamp_str,
            metadata={"action_id": action.id, "reviewer_id": request.reviewer_id}
        )

        try:
            evaluate_and_apply_automatic_restrictions(db)
        except Exception:
            pass

        return ApprovalDecisionResponse(
            action_id=action.id,
            decision="REJECTED",
            status="BLOCKED",
            executed=False,
            execution_result=None,
            message="Action rejected by reviewer and prevented from execution."
        )

@router.post("/approvals/bundle-decide", response_model=BundleApprovalDecisionResponse)
def decide_approval_bundle(request: BundleApprovalDecisionRequest, db: Session = Depends(get_db)):
    """
    Feature B1: Reviewer Approval Bundling for eligible low-risk items.
    Enforces strict safety boundaries:
      - Bundling allowed ONLY under Normal oversight (disabled when restriction level >= 1).
      - ONLY individually eligible Tier 1 items can be bundled.
      - Never bundles prohibited (Tier X) or high-risk (Tier 2/3) items.
      - Evaluates exact fingerprint and single-use token for EVERY action individually.
      - Never executes a blocked action.
    """
    decision_clean = request.decision.upper().strip()
    if decision_clean not in ("APPROVED", "REJECTED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Decision must be 'APPROVED' or 'REJECTED'."
        )

    # Enforce backend reviewer authorization
    verify_reviewer_authorization(request.reviewer_id, "approval bundling")

    # 1. Bundling disabled under warning/elevated restrictions
    active_level = get_current_restriction_level(db)
    if active_level >= RESTRICTION_LEVEL_1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Approval bundling is disabled when safety restrictions are active (Current Level: {active_level}). Actions must be inspected individually."
        )

    # 2. Check Reviewer Approval Budget
    budget_status = get_reviewer_budget_status(db, reviewer_id=request.reviewer_id)
    if budget_status["is_exhausted"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Reviewer approval budget exhausted. Bundled reviews restricted."
        )

    decisions_list = []
    for action_id in request.action_ids:
        action = db.query(ActionModel).filter(ActionModel.id == action_id).first()
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Action ID #{action_id} not found."
            )

        # Policy verification: only Tier 1 is eligible for bundling
        if action.risk_tier not in ("Tier 1", "Tier 0"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Action ID #{action_id} is '{action.risk_tier}'; only Tier 1 low-risk reversible actions are eligible for bundled approval."
            )

        # Reuse exact single decision logic
        single_req = ApprovalDecisionRequest(
            action_id=action_id,
            decision=decision_clean,
            reviewer_id=request.reviewer_id,
            reason=request.reason or f"Approved in bundle of {len(request.action_ids)} actions"
        )
        single_res = decide_approval(single_req, db)
        decisions_list.append(single_res)

    return BundleApprovalDecisionResponse(
        bundle_size=len(decisions_list),
        decision=decision_clean,
        decisions=decisions_list,
        message=f"Bundle of {len(decisions_list)} actions successfully processed with decision '{decision_clean}'."
    )

