export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type ActionStatus = 'PENDING' | 'APPROVED' | 'BLOCKED' | 'EXECUTED' | 'REJECTED';
export type AgentStatusType = 'ACTIVE' | 'PAUSED' | 'FROZEN';
export type SecurityEventTag = 'BLOCKED' | 'APPROVED' | 'WARNING' | 'INFO';

export interface Agent {
  id: string;
  name: string;
  type: string;
  status: AgentStatusType;
  health_score: number;
  sparklineData?: number[];
}

export interface PendingAction {
  id: number;
  action_type: string;
  description?: string;
  agent_name: string;
  target: string;
  risk_level: RiskLevel;
  status: ActionStatus;
  timestamp: string;
  risk_tier?: string;
  required_confirmation_phrase?: string;
}

export interface SecurityEvent {
  id: number;
  time_str: string;
  title: string;
  description: string;
  status_tag: SecurityEventTag;
}

export interface SafetyDrill {
  id: string;
  title: string;
  date_str: string;
  status: 'Completed' | 'Pending' | 'Failed';
}

export interface OversightHealthData {
  reviewer_health: number;
  reviewer_health_status: string;
  reviewer_attention_rate: number;
  approval_budget_used: number;
  approval_budget_total: number;
  active_restrictions: number;
  gateway_health: number;
}

export interface RiskActivityPoint {
  time: string;
  total: number;
  blocked: number;
  pending: number;
}

export interface FatigueTrendPoint {
  date: string;
  approvals: number;
  fatigueRisk: number;
}

export interface DashboardData {
  gateway_health: number;
  healthy_percent: number;
  warning_percent: number;
  critical_percent: number;
  total_actions: number;
  total_actions_delta: string;
  blocked_actions: number;
  blocked_actions_delta: string;
  pending_approvals: number;
  pending_approvals_delta: string;
  agents: Agent[];
  pending_actions: PendingAction[];
  recent_events: SecurityEvent[];
  oversight: OversightHealthData;
}

// ================= Stage 2 Gateway & Approval Types =================

export interface ToolCallRequest {
  agent_id: string;
  session_id: string;
  tool_name: string;
  action_details: Record<string, any>;
  untrusted_content_ids?: string[];
}

export interface ToolCallResponse {
  action_id: number;
  decision: 'ALLOW' | 'BLOCK' | 'HOLD';
  risk_score: number;
  risk_tier: string;
  risk_level: RiskLevel;
  reason: string;
  policy_matches: string[];
  execution_status: 'EXECUTED' | 'BLOCKED' | 'PENDING_APPROVAL' | 'FAILED';
  timestamp: string;
  fingerprint?: string;
  execution_result?: Record<string, any>;
}

export interface PendingApprovalItem {
  action_id: number;
  tool_name: string;
  action_type: string;
  agent_id: string;
  agent_name: string;
  target: string;
  action_details: Record<string, any>;
  risk_tier: string;
  risk_score: number;
  risk_level: RiskLevel;
  reason: string;
  fingerprint: string;
  created_at: string;
  expires_at: string;
  seconds_remaining: number;
  required_confirmation_phrase?: string;
}

export interface ApprovalDecisionResponse {
  action_id: number;
  decision: 'APPROVED' | 'REJECTED';
  status: string;
  executed: boolean;
  execution_result?: Record<string, any>;
  message: string;
}

export interface UntrustedContentItem {
  id: string;
  title: string;
  content_text: string;
  trust_label: string;
  source: string;
  created_at: string;
}

// ================= Stage 2 Cryptographic Audit Types =================

export interface AuditEventItem {
  id: number;
  sequence_number?: number | null;
  time_str: string;
  title: string;
  description: string;
  status_tag: SecurityEventTag;
  prev_hash?: string | null;
  current_hash?: string | null;
}

export type AuditVerificationStatus = 'VALID' | 'INVALID' | 'UNVERIFIABLE' | 'NOT_FOUND';

export interface AuditVerificationResult {
  event_id: number;
  status: AuditVerificationStatus;
  stored_hash?: string | null;
  computed_hash?: string | null;
  prev_hash?: string | null;
  expected_prev_hash?: string | null;
  sequence_number?: number | null;
  reason: string;
}

export interface AuditChainVerificationResult {
  status: 'VALID' | 'INVALID' | 'UNVERIFIABLE';
  total_events: number;
  valid_count: number;
  invalid_count: number;
  unverifiable_count: number;
  broken_links: Array<Record<string, any>>;
  message: string;
  verified_at: string;
}

// ================= Stage 3 Oversight Intelligence & Evidence Types =================

export interface ReviewerBudgetData {
  budget_total: number;
  budget_used: number;
  budget_remaining: number;
  utilization_rate: number;
  status: 'HEALTHY' | 'WARNING' | 'EXHAUSTED' | string;
  window_hours: number;
  is_exhausted: boolean;
  is_warning: boolean;
  active_reviewer: string;
}

export interface AttentionDrillItem {
  id: string;
  title: string;
  description: string;
  scenario_type: string;
  target: string;
  action_details?: Record<string, any>;
  expected_decision: string;
  is_simulation: boolean;
  status: 'PENDING' | 'PASSED' | 'FAILED' | string;
  reviewer_decision?: string | null;
  reviewer_id?: string | null;
  reviewer_notes?: string | null;
  responded_at?: string | null;
  created_at: string;
}

export interface DrillSubmissionResponse {
  drill_id: string;
  status: string;
  is_correct: boolean;
  scenario_type: string;
  reviewer_decision: string;
  responded_at: string;
  message: string;
}

export interface OversightHealthMetricItem {
  metric: string;
  measured_value: string;
  points_earned: number;
  max_points: number;
  explanation: string;
}

export interface OversightHealthResponseStage3 {
  score: number;
  status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'INSUFFICIENT_DATA';
  data_sufficiency: 'SUFFICIENT' | 'INSUFFICIENT_DATA';
  breakdown: OversightHealthMetricItem[];
  budget: ReviewerBudgetData;
  drills: {
    total_drills: number;
    passed_drills: number;
    failed_drills: number;
    pass_rate: number | null;
    status: string;
  };
  rapid_approvals: number;
  pending_backlog: number;
  calculated_at: string;
}

export interface RestrictionHistoryItem {
  id: number;
  level: number;
  level_name: string;
  reason: string;
  authorized_by: string;
  is_override: boolean;
  created_at: string;
}

export interface RestrictionStatusResponse {
  current_level: number;
  level_name: string;
  reason: string;
  history: RestrictionHistoryItem[];
}

export interface EvidenceReportData {
  report_id: string;
  generated_at: string;
  reporting_period: string;
  total_actions: number;
  allow_count: number;
  block_count: number;
  hold_count: number;
  risk_tier_distribution: Record<string, number>;
  approved_count: number;
  rejected_count: number;
  budget_used: number;
  budget_total: number;
  oversight_score: number;
  oversight_status: string;
  data_sufficiency: string;
  drill_pass_rate: number | null;
  active_restriction_level: number;
  restriction_level_name: string;
  paused_agents: string[];
  audit_chain_status: string;
  valid_blocks: number;
  invalid_blocks: number;
  unverifiable_blocks: number;
  total_audit_records: number;
}


