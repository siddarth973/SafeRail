from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

class HealthCheckResponse(BaseModel):
    status: str
    app_name: str
    tagline: str
    version: str
    database: str
    timestamp: datetime

class AgentSchema(BaseModel):
    id: str
    name: str
    type: str
    status: str
    health_score: int

class PendingActionSchema(BaseModel):
    id: int
    action_type: str
    description: Optional[str] = None
    agent_name: str
    target: str
    risk_level: str
    status: str
    timestamp: str

class SecurityEventSchema(BaseModel):
    id: int
    sequence_number: Optional[int] = None
    time_str: str
    title: str
    description: str
    status_tag: str
    prev_hash: Optional[str] = None
    current_hash: Optional[str] = None

class OversightHealthSchema(BaseModel):
    reviewer_health: int
    reviewer_health_status: str
    reviewer_attention_rate: int
    approval_budget_used: int
    approval_budget_total: int
    active_restrictions: int
    gateway_health: int

class DashboardSummaryResponse(BaseModel):
    gateway_health: int
    healthy_percent: int
    warning_percent: int
    critical_percent: int
    total_actions: int
    total_actions_delta: str
    blocked_actions: int
    blocked_actions_delta: str
    pending_approvals: int
    pending_approvals_delta: str
    agents: List[AgentSchema]
    pending_actions: List[PendingActionSchema]
    recent_events: List[SecurityEventSchema]
    oversight: OversightHealthSchema

# ==================== Stage 2 Schemas ====================

class ToolCallRequest(BaseModel):
    agent_id: str = Field(..., description="Unique ID of the agent proposing the action")
    session_id: str = Field(default="session-001", description="Current execution session ID")
    tool_name: str = Field(..., description="Target mock tool to execute")
    action_details: Dict[str, Any] = Field(..., description="Parameters and payload of the action")
    untrusted_content_ids: Optional[List[str]] = Field(default=None, description="Optional referenced untrusted content IDs")

class ToolCallResponse(BaseModel):
    action_id: int
    decision: str  # ALLOW, BLOCK, HOLD
    risk_score: int
    risk_tier: str  # Tier 0, Tier 1, Tier 2, Tier 3, Tier X
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    reason: str
    policy_matches: List[str]
    execution_status: str  # EXECUTED, BLOCKED, PENDING_APPROVAL, FAILED
    timestamp: str
    fingerprint: Optional[str] = None
    execution_result: Optional[Dict[str, Any]] = None

class PendingApprovalResponse(BaseModel):
    action_id: int
    tool_name: str
    action_type: str
    agent_id: str
    agent_name: str
    target: str
    action_details: Dict[str, Any]
    risk_tier: str
    risk_score: int
    risk_level: str
    reason: str
    fingerprint: str
    created_at: str
    expires_at: str
    seconds_remaining: int
    required_confirmation_phrase: Optional[str] = None

class ApprovalDecisionRequest(BaseModel):
    action_id: int
    decision: str = Field(..., description="'APPROVED' or 'REJECTED'")
    reviewer_id: str = Field(default="reviewer-kavya", description="ID of the reviewing administrator")
    reason: Optional[str] = Field(default=None, description="Optional review justification")
    confirmation_phrase: Optional[str] = Field(default=None, description="Phrase required for Tier 3 confirmation friction")


class ApprovalDecisionResponse(BaseModel):
    action_id: int
    decision: str
    status: str
    executed: bool
    execution_result: Optional[Dict[str, Any]] = None
    message: str

class BundleApprovalDecisionRequest(BaseModel):
    action_ids: List[int] = Field(..., min_length=1, max_length=10, description="List of eligible Tier 1 action IDs to bundle")
    decision: str = Field(..., description="'APPROVED' or 'REJECTED'")
    reviewer_id: str = Field(default="reviewer-kavya", description="Reviewer ID")
    reason: Optional[str] = Field(default=None, description="Review justification for the bundle")

class BundleApprovalDecisionResponse(BaseModel):
    bundle_size: int
    decision: str
    decisions: List[ApprovalDecisionResponse]
    message: str


class AgentResumeRequest(BaseModel):
    reviewer_id: str = Field(..., description="Authorized reviewer resuming the agent")
    reason: str = Field(..., description="Typed justification for resuming agent operations")

class AgentStatusActionResponse(BaseModel):
    agent_id: str
    status: str
    message: str

# ==================== Audit Verification Schemas ====================

class AuditVerificationResponse(BaseModel):
    event_id: int
    status: str  # VALID, INVALID, UNVERIFIABLE, NOT_FOUND
    stored_hash: Optional[str] = None
    computed_hash: Optional[str] = None
    prev_hash: Optional[str] = None
    expected_prev_hash: Optional[str] = None
    sequence_number: Optional[int] = None
    reason: str

class AuditChainVerificationResponse(BaseModel):
    status: str  # VALID, INVALID, UNVERIFIABLE
    total_events: int
    valid_count: int
    invalid_count: int
    unverifiable_count: int
    broken_links: List[Dict[str, Any]]
    message: str
    verified_at: str

# ==================== Stage 3 Oversight Intelligence Schemas ====================

class ReviewerBudgetResponse(BaseModel):
    budget_total: int
    budget_used: int
    budget_remaining: int
    utilization_rate: float
    status: str
    window_hours: int
    is_exhausted: bool
    is_warning: bool
    active_reviewer: str

class AttentionDrillResponse(BaseModel):
    id: str
    title: str
    description: str
    scenario_type: str
    target: str
    action_details: Optional[Dict[str, Any]] = None
    expected_decision: str
    is_simulation: bool
    status: str
    reviewer_decision: Optional[str] = None
    reviewer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    responded_at: Optional[str] = None
    created_at: str

class DrillSubmissionRequest(BaseModel):
    decision: str = Field(..., description="'APPROVED' or 'REJECTED'")
    reviewer_id: str = Field(default="reviewer-kavya", description="ID of the reviewing administrator")
    notes: Optional[str] = Field(default=None, description="Optional drill response justification")

class DrillSubmissionResponse(BaseModel):
    drill_id: str
    status: str
    is_correct: bool
    scenario_type: str
    reviewer_decision: str
    responded_at: str
    message: str

class OversightHealthMetricItem(BaseModel):
    metric: str
    measured_value: str
    points_earned: int
    max_points: int
    explanation: str

class OversightHealthResponse(BaseModel):
    score: int
    status: str
    data_sufficiency: str
    breakdown: List[OversightHealthMetricItem]
    budget: Dict[str, Any]
    drills: Dict[str, Any]
    rapid_approvals: int
    pending_backlog: int
    calculated_at: str

class RestrictionHistoryItem(BaseModel):
    id: int
    level: int
    level_name: str
    reason: str
    authorized_by: str
    is_override: bool
    created_at: str

class RestrictionStatusResponse(BaseModel):
    current_level: int
    level_name: str
    reason: str
    history: List[RestrictionHistoryItem]

class RestrictionOverrideRequest(BaseModel):
    level: int = Field(..., ge=0, le=3, description="Target restriction level: 0=NORMAL, 1=ELEVATED, 2=STRICT, 3=EMERGENCY")
    reviewer_id: str = Field(..., description="Authorized reviewer overriding restriction")
    reason: str = Field(..., description="Typed justification for manual restriction modification")

class EvidenceReportResponse(BaseModel):
    report_id: str
    generated_at: str
    reporting_period: str
    total_actions: int
    allow_count: int
    block_count: int
    hold_count: int
    risk_tier_distribution: Dict[str, int]
    approved_count: int
    rejected_count: int
    budget_used: int
    budget_total: int
    oversight_score: int
    oversight_status: str
    data_sufficiency: str
    drill_pass_rate: Optional[float] = None
    active_restriction_level: int
    restriction_level_name: str
    paused_agents: List[str]
    audit_chain_status: str
    valid_blocks: int
    invalid_blocks: int
    unverifiable_blocks: int
    total_audit_records: int

