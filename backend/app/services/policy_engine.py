import hashlib
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.safety import UntrustedContentModel

# Baseline Risk Tier Definitions
TIER_0 = "Tier 0"  # 0–9: Allow
TIER_1 = "Tier 1"  # 10–29: Allow
TIER_2 = "Tier 2"  # 30–59: Require human approval
TIER_3 = "Tier 3"  # 60–89: Require human approval with additional verification
TIER_X = "Tier X"  # 90–100: Mandatory Block

# Decisions
DECISION_ALLOW = "ALLOW"
DECISION_HOLD = "HOLD"
DECISION_BLOCK = "BLOCK"

# Permitted limits
MAX_AUTO_REFUND_LIMIT = 100.0
AUTHORIZED_EMAIL_DOMAINS = ["example.com", "saferail.internal", "company.org"]

@dataclass
class PolicyEvaluationResult:
    decision: str
    risk_score: int
    risk_tier: str
    risk_level: str
    reason: str
    policy_matches: List[str] = field(default_factory=list)
    untrusted_influence_detected: bool = False
    untrusted_matches: List[str] = field(default_factory=list)

def compute_action_fingerprint(
    tool_name: str,
    action_details: Dict[str, Any],
    agent_id: str,
    session_id: str
) -> str:
    """
    Computes a canonical SHA-256 fingerprint for exact-action binding.
    Uses deterministic JSON serialization with strictly sorted keys.
    """
    canonical_payload = {
        "action_details": action_details,
        "agent_id": str(agent_id),
        "session_id": str(session_id),
        "tool_name": str(tool_name)
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()

def score_to_tier_and_decision(score: int, override_block: bool = False) -> tuple[str, str, str]:
    """Maps numerical score to baseline tier, decision, and risk level."""
    if override_block or score >= 90:
        return TIER_X, DECISION_BLOCK, "HIGH"
    elif score >= 60:
        return TIER_3, DECISION_HOLD, "HIGH"
    elif score >= 30:
        return TIER_2, DECISION_HOLD, "MEDIUM"
    elif score >= 10:
        return TIER_1, DECISION_ALLOW, "LOW"
    else:
        return TIER_0, DECISION_ALLOW, "LOW"

def check_untrusted_content_influence(
    action_details: Dict[str, Any],
    untrusted_content_ids: Optional[List[str]],
    db: Optional[Session] = None
) -> tuple[bool, List[str]]:
    """
    Detects if the action parameters match or originate from untrusted content.
    Simple, explainable keyword and content matching for prototype safety.
    """
    detected = False
    matches = []

    # Direct ID reference
    if untrusted_content_ids:
        detected = True
        matches.extend([f"Referenced untrusted content ID: {cid}" for cid in untrusted_content_ids])

    # Check for known prompt-injection tokens in action details
    text_repr = json.dumps(action_details).lower()
    
    suspicious_patterns = [
        "attacker.com",
        "external-leak",
        "ignore previous rules",
        "exfiltrate",
        "drop table",
        "leak_secret"
    ]
    for pattern in suspicious_patterns:
        if pattern in text_repr:
            detected = True
            matches.append(f"Contains suspicious/injection keyword: '{pattern}'")

    # If DB session provided, check against seeded untrusted contents
    if db:
        try:
            untrusted_records = db.query(UntrustedContentModel).filter(
                UntrustedContentModel.trust_label == "UNTRUSTED"
            ).all()
            for record in untrusted_records:
                # If recipient or key matches untrusted target
                if "external-leak@attacker.com" in record.content_text and "external-leak@attacker.com" in text_repr:
                    detected = True
                    matches.append(f"Matches untrusted exfiltration target from {record.id}")
        except Exception:
            pass

    return detected, matches

def evaluate_action(
    tool_name: str,
    action_details: Dict[str, Any],
    agent_id: str,
    agent_status: str = "ACTIVE",
    session_id: str = "default_session",
    untrusted_content_ids: Optional[List[str]] = None,
    db: Optional[Session] = None
) -> PolicyEvaluationResult:
    """
    Deterministic Policy Evaluation Engine.
    Evaluates agent actions, applies deterministic policy rules, calculates risk score/tier,
    and returns a definitive decision (ALLOW, HOLD, BLOCK).
    """
    # Rule 0: Agent lifecycle check - PAUSED or FROZEN agents must not execute
    if agent_status in ("PAUSED", "FROZEN"):
        return PolicyEvaluationResult(
            decision=DECISION_BLOCK,
            risk_score=100,
            risk_tier=TIER_X,
            risk_level="HIGH",
            reason=f"Action prohibited: Agent '{agent_id}' is currently {agent_status}.",
            policy_matches=["POL-AGENT-01-LIFECYCLE-LOCK"]
        )

    # Check untrusted content influence
    is_untrusted, untrusted_reasons = check_untrusted_content_influence(
        action_details, untrusted_content_ids, db
    )

    policy_matches = []
    base_score = 10
    override_block = False
    reason = "Standard policy evaluation completed."

    # Tool-specific deterministic evaluations
    if tool_name == "read_ticket":
        policy_matches.append("POL-READ-01")
        if is_untrusted:
            base_score = 15
            reason = "Ticket read allowed; flagged for containing untrusted input."
        else:
            base_score = 5
            reason = "Ticket read allowed under standard read-only policy."

    elif tool_name == "send_email":
        policy_matches.append("POL-EMAIL-01")
        to_address = str(action_details.get("to", "")).lower()
        subject = str(action_details.get("subject", ""))
        body = str(action_details.get("body", ""))

        # Check domain authorization
        domain = to_address.split("@")[-1] if "@" in to_address else ""
        is_authorized_domain = any(domain.endswith(auth_dom) for auth_dom in AUTHORIZED_EMAIL_DOMAINS)

        if is_untrusted:
            base_score = 95
            override_block = True
            policy_matches.append("POL-EMAIL-UNTRUSTED-BLOCK")
            reason = f"Email dispatch BLOCKED: Action influenced by untrusted source instructions targeting '{to_address}'."
        elif not is_authorized_domain:
            base_score = 75
            policy_matches.append("POL-EMAIL-EXTERNAL-HOLD")
            reason = f"Email to external domain '{domain}' requires human review before dispatch."
        else:
            base_score = 15
            reason = f"Email to authorized recipient '{to_address}' permitted."

    elif tool_name == "issue_refund":
        policy_matches.append("POL-FIN-REFUND")
        amount = float(action_details.get("amount", 0.0))
        
        if amount <= 0:
            base_score = 95
            override_block = True
            policy_matches.append("POL-FIN-INVALID")
            reason = f"Refund of invalid amount (${amount}) is strictly prohibited."
        elif is_untrusted:
            base_score = 90
            override_block = True
            policy_matches.append("POL-FIN-UNTRUSTED")
            reason = "Refund request influenced by untrusted content is blocked."
        elif amount <= MAX_AUTO_REFUND_LIMIT:
            base_score = 20
            reason = f"Refund of ${amount:.2f} is within automated threshold (${MAX_AUTO_REFUND_LIMIT:.2f}) and allowed."
        elif amount <= 500.0:
            base_score = 45
            policy_matches.append("POL-FIN-APPROVAL-MID")
            reason = f"Refund of ${amount:.2f} exceeds automated limit of ${MAX_AUTO_REFUND_LIMIT:.2f} and requires human approval."
        else:
            base_score = 80
            policy_matches.append("POL-FIN-APPROVAL-HIGH")
            reason = f"High-value refund of ${amount:.2f} exceeds $500.00 and requires elevated supervisor approval."

    elif tool_name == "export_customers":
        policy_matches.append("POL-DATA-EXPORT-PROHIBITED")
        base_score = 98
        override_block = True
        reason = "Export of confidential customer database is strictly prohibited by policy POL-DATA-01."

    elif tool_name == "delete_records":
        policy_matches.append("POL-DATA-DELETE")
        target_record = str(action_details.get("record_type", ""))
        if is_untrusted:
            base_score = 95
            override_block = True
            policy_matches.append("POL-DELETE-UNTRUSTED")
            reason = "Record deletion initiated from untrusted source is blocked."
        else:
            base_score = 70
            reason = f"Deletion of {target_record} records is potentially destructive and requires human approval."

    elif tool_name == "update_profile":
        policy_matches.append("POL-USER-UPDATE")
        updates = action_details.get("updates", {})
        if "role" in updates or "permissions" in updates:
            base_score = 95
            override_block = True
            policy_matches.append("POL-PRIV-ESCALATION")
            reason = "Self-privilege escalation (role or permissions modification) is strictly blocked."
        else:
            base_score = 15
            reason = "Standard user profile attribute update permitted."

    else:
        # Unknown tool fallback - fail closed
        base_score = 95
        override_block = True
        policy_matches.append("POL-UNKNOWN-TOOL")
        reason = f"Unknown tool '{tool_name}' cannot be verified safely. Gateway failing closed."

    # Compute tier, decision, and risk level
    tier, decision, level = score_to_tier_and_decision(base_score, override_block)

    return PolicyEvaluationResult(
        decision=decision,
        risk_score=base_score,
        risk_tier=tier,
        risk_level=level,
        reason=reason,
        policy_matches=policy_matches,
        untrusted_influence_detected=is_untrusted,
        untrusted_matches=untrusted_reasons
    )
