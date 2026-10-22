import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey
from app.db.session import Base

class AgentModel(Base):
    __tablename__ = "agents"

    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(64), default="assistant")
    status = Column(String(32), default="ACTIVE")  # ACTIVE, PAUSED, FROZEN
    health_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class ActionModel(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    agent_id = Column(String(64), nullable=True, index=True)
    session_id = Column(String(64), nullable=True)
    tool_name = Column(String(64), nullable=True)
    action_type = Column(String(64), nullable=False)  # "Send email", "Issue refund", etc.
    description = Column(String(256), nullable=True)
    agent_name = Column(String(128), nullable=False)
    target = Column(String(256), nullable=False)
    action_details = Column(Text, nullable=True)  # JSON serialized parameters
    untrusted_content_ids = Column(Text, nullable=True)  # JSON list of untrusted content IDs
    risk_score = Column(Integer, default=50)
    risk_tier = Column(String(32), default="Tier 2")  # Tier 0, Tier 1, Tier 2, Tier 3, Tier X
    risk_level = Column(String(32), default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    policy_matches = Column(Text, nullable=True)  # JSON list of matching policy rules
    reason = Column(Text, nullable=True)
    decision = Column(String(32), default="HOLD")  # ALLOW, BLOCK, HOLD
    status = Column(String(32), default="PENDING")  # PENDING, APPROVED, BLOCKED, EXECUTED
    execution_status = Column(String(32), default="PENDING_APPROVAL")  # EXECUTED, BLOCKED, PENDING_APPROVAL, FAILED
    fingerprint = Column(String(64), nullable=True, index=True)  # Canonical SHA-256 fingerprint
    timestamp = Column(String(32), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ApprovalModel(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    action_id = Column(Integer, ForeignKey("actions.id"), nullable=False, index=True)
    fingerprint = Column(String(64), nullable=False, index=True)
    decision = Column(String(32), default="PENDING")  # PENDING, APPROVED, REJECTED
    reviewer_id = Column(String(64), nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    executed_at = Column(DateTime, nullable=True)

class UntrustedContentModel(Base):
    __tablename__ = "untrusted_contents"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    content_text = Column(Text, nullable=False)
    trust_label = Column(String(32), default="UNTRUSTED")  # TRUSTED, UNTRUSTED
    source = Column(String(64), default="support_ticket")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class ToolExecutionModel(Base):
    __tablename__ = "tool_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    action_id = Column(Integer, nullable=True, index=True)
    tool_name = Column(String(64), nullable=False)
    parameters_json = Column(Text, nullable=True)
    result_json = Column(Text, nullable=True)
    status = Column(String(32), default="SUCCESS")  # SUCCESS, FAILED
    executed_at = Column(DateTime, default=datetime.datetime.utcnow)

class SecurityEventModel(Base):
    __tablename__ = "security_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sequence_number = Column(Integer, nullable=True, index=True)
    time_str = Column(String(32), nullable=False)
    title = Column(String(128), nullable=False)
    description = Column(String(256), nullable=False)
    status_tag = Column(String(32), nullable=False)  # BLOCKED, APPROVED, WARNING, INFO
    prev_hash = Column(String(64), nullable=True)  # SHA-256 of preceding event block or "GENESIS"
    current_hash = Column(String(64), nullable=True, index=True)  # SHA-256 of canonical event serialization
    metadata_json = Column(Text, nullable=True)  # Additional audit context as JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OversightMetricModel(Base):
    __tablename__ = "oversight_metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    reviewer_health = Column(Integer, default=82)
    reviewer_health_status = Column(String(32), default="Good")
    reviewer_attention_rate = Column(Integer, default=78)
    approval_budget_used = Column(Integer, default=68)
    approval_budget_total = Column(Integer, default=100)
    active_restrictions = Column(Integer, default=1)
    gateway_health = Column(Integer, default=98)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class AttentionDrillModel(Base):
    __tablename__ = "attention_drills"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(128), nullable=False)
    description = Column(String(256), nullable=False)
    scenario_type = Column(String(64), nullable=False)  # suspicious_recipient, unusual_refund, sensitive_export, destructive_action, prompt_injection
    target = Column(String(128), nullable=False)
    action_details_json = Column(Text, nullable=True)
    expected_decision = Column(String(32), default="REJECTED")
    is_simulation = Column(Boolean, default=True)  # Clearly marked as simulated drill
    status = Column(String(32), default="PENDING")  # PENDING, PASSED, FAILED
    reviewer_decision = Column(String(32), nullable=True)
    reviewer_id = Column(String(64), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class OversightSnapshotModel(Base):
    __tablename__ = "oversight_snapshots"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    score = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False)  # HEALTHY, WARNING, POOR, CRITICAL, INSUFFICIENT_DATA
    data_sufficiency = Column(String(32), nullable=False)  # SUFFICIENT, INSUFFICIENT_DATA
    budget_utilization = Column(Float, default=0.0)
    drill_accuracy = Column(Float, nullable=True)
    rapid_approval_count = Column(Integer, default=0)
    pending_backlog_count = Column(Integer, default=0)
    metrics_json = Column(Text, nullable=True)
    snapshot_at = Column(DateTime, default=datetime.datetime.utcnow)

class RestrictionHistoryModel(Base):
    __tablename__ = "restriction_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    level = Column(Integer, default=0)  # 0: Normal, 1: Warning, 2: Poor, 3: Critical
    level_name = Column(String(32), default="NORMAL")  # NORMAL, ELEVATED, STRICT, EMERGENCY
    reason = Column(Text, nullable=False)
    trigger_metrics_json = Column(Text, nullable=True)
    authorized_by = Column(String(64), default="SYSTEM_AUTOMATION")
    is_override = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

