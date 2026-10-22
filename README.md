# SafeRail — AI Agent Safety & Control
> **DevHost 2026 Problem Statement 2.1: AI Agent Safety and Control**

SafeRail is an enterprise-grade AI safety gateway and oversight intelligence platform designed to intercept, analyze, gate, and monitor autonomous AI agent actions in real time.

---

## 🛡️ Architecture Overview

SafeRail consists of three unified architectural pillars:
1. **Core Gateway Interception & Sandbox Engine (Stage 1 & 2)**: Evaluates all tool calls before dispatch through a deterministic policy engine, binding approved actions to single-use SHA-256 canonical fingerprints.
2. **Cryptographic Audit Chain (Stage 2 Verification)**: Every security event, gateway decision, and review is linked via sequential SHA-256 hash pointers, enabling deterministic detection of database tampering and broken links.
3. **Oversight Intelligence & Reviewer Integrity (Stage 3)**: Evaluates reviewer fatigue and workload through an approval budget in a sliding 24-hour window, enforces risk-matched friction (Tier 3 confirmation phrases), injects synthetic attention drills that never execute mock tools, calculates a deterministic 4-pillar health score, and automatically tightens safety restrictions under degraded oversight.

```
                              [Simulated AI Agent]
                                       │
                                       ▼
                       [POST /api/v1/tool_call]  ◄── Gateway Interception (Fail-Closed)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
             [Active Safety Restrictions]    [Untrusted-Content Inspection]
             (Levels 0–3, Emergency Lock)    (Exfiltration / Prompt Injections)
                        │                             │
                        └──────────────┬──────────────┘
                                       ▼
                        [Deterministic Policy Engine]
                        (Tiers 0, 1, 2, 3, Tier X)
                                       │
     ┌─────────────────────────────────┼─────────────────────────────────┐
     ▼                                 ▼                                 ▼
  [ALLOW]                           [HOLD]                            [BLOCK]
Executes isolated mock tool   Binds canonical SHA-256          Prohibits execution
in sandbox (read_ticket,      fingerprint, generates           Logs incident to
safe email, refund <= $100)   single-use approval token        tamper-evident audit log
                                       │
                                       ▼
                        [Oversight Intelligence Checks]
                        ├─► 24h Approval Budget Check (Exhaustion -> 429)
                        ├─► Risk-Matched Friction (Tier 3 -> Confirmation Phrase)
                        ├─► Synthetic Attention Drills (Isolated Simulations)
                        └─► Rapid Approval Detection (<3s Rubber-Stamping)
                                       │
                                       ▼
                             [POST /api/v1/decide]
                         Human Reviewer Verification
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
                   [APPROVED]                     [REJECTED]
             Executes exact action           Blocks execution &
             once (single-use)               records justification
```

---

## 🔒 Key Stage 3 Features: Oversight Intelligence

### 1. Reviewer Approval Budget (Feature B1)
- **Sliding Window Calculation**: Tracks real approved actions from `ApprovalModel` over a rolling 24-hour window.
- **Quota Enforcement**: Default threshold of 100 approvals/day. When quota is exhausted (`is_exhausted = True`), additional Tier 2 and Tier 3 approval attempts are held under cool-down (`429 Too Many Requests`) to prevent fatigue-driven rubber-stamping.
- **Safe Tier 1 Bundling**: Allows reviewers to batch-approve up to 10 low-risk Tier 1 actions at once (`POST /api/v1/approvals/bundle-decide`). Rejects higher-risk Tier 2/3 actions or requests when elevated restrictions are active.

### 2. Risk-Matched Review Friction (Feature B2)
- **Tier 0**: Fully automated read-only execution (`read_ticket`).
- **Tier 1**: Low-risk reversible modifications (`update_profile`, refund <= $100). Eligible for safe bundling.
- **Tier 2**: Standard human approval requiring review and optional justification note (`issue_refund` $100–$500).
- **Tier 3**: High-risk operations (`delete_records`, external email, high-value refunds > $500). Requires the reviewer to type an exact, dynamically generated confirmation phrase (e.g. `CONFIRM-DELETE-CUSTOMER_ARCHIVE_TABLE`) to prevent accidental or automated approval.
- **Tier X**: Prohibited operations (`export_customers`, prompt injections, paused agents). Directly blocked without human override.

### 3. Synthetic Attention Drills (Feature B3)
- **Safe Canaries**: Unannounced simulated actions seeded into the reviewer queue (`is_simulation = True`).
- **Isolation Guarantee**: Submitting drill responses **never executes mock tools**, modifies user records, or dispatches emails.
- **Vigilance Measurement**: Correctly rejecting a canary marks the drill `PASSED`. Fatigued approval marks it `FAILED`, lowering the reviewer's health score. All responses are logged with timestamps in the audit trail.

### 4. Deterministic 4-Pillar Oversight Health Score (Feature B4)
Calculates a transparent 0–100 score across 4 weighted pillars (25 points each):
1. **Attention Drill Pass Rate (0–25 pts)**: Reviewer accuracy on synthetic security drills.
2. **Approval Budget Compliance (0–25 pts)**: Workload tracking against the sliding 24-hour quota.
3. **Approval Velocity Consistency (0–25 pts)**: Rubber-stamping detector flagging decisions made in under 3 seconds.
4. **High-Risk Queue Throughput (0–25 pts)**: Aging monitor for pending Tier 3 actions (>5 minutes).
- **Honest Data Sufficiency**: If zero reviews or drills have occurred in the active window, the system returns `data_sufficiency = "INSUFFICIENT_DATA"` rather than claiming false 100% health.

### 5. Automatic Safety Tightening (Feature B5)
- **Four Escalation Levels**:
  - **Level 0 (NORMAL)**: Baseline policy engine. Normal throughput.
  - **Level 1 (ELEVATED)**: Triggered on warning metrics. Tier 1 bundling disabled; scrutiny on sensitive tools.
  - **Level 2 (STRICT)**: Triggered on poor metrics or budget exhaustion. Tier 2 actions require cool-down and elevated friction.
  - **Level 3 (EMERGENCY)**: Triggered on critical score (<40), failed drills, or system failures. Fail-closed posture locks all approval executions.
- **Fail-Closed Fallback**: Any internal scoring error defaults directly to Level 3 EMERGENCY.
- **Authorized Manual Override**: Administrators can adjust restriction levels via `POST /api/v1/oversight/restrictions/override` with a typed justification, creating an immutable audit record.

### 6. Verifiable Compliance Evidence Reports (Feature B6)
- **Real-Time Synthesis**: Aggregates live database metrics across gateway actions, risk tiers, reviewer decisions, oversight health, and cryptographic audit proofs.
- **Export Formats**:
  - `GET /api/v1/evidence/report`: JSON summary for UI inspection.
  - `GET /api/v1/evidence/report.json`: Formatted downloadable JSON compliance package.
  - `GET /api/v1/evidence/report.csv`: Tabular CSV audit file for corporate compliance reviews.

---

## 🧪 Comprehensive Automated Test Suite (38/38 Passed)

All automated tests execute against an isolated in-memory SQLite database (`sqlite:///:memory:`) using the autouse fixture in `conftest.py`. The real production database (`saferail.db`, containing 169 records: 78 chained, 91 legacy) is strictly protected from modification.

```powershell
cd C:\Users\siddu\.gemini\antigravity\scratch\SafeRail\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

### Complete Test Matrix (38 Passing Tests):

#### Cryptographic Audit Hash Verification
1. `test_canonical_hash_determinism` ✅
2. `test_genesis_event_creation_and_verification` ✅
3. `test_chained_events_sequential_verification` ✅
4. `test_legacy_record_reported_unverifiable` ✅
5. `test_tampered_record_contents_detected_as_invalid` ✅
6. `test_tampered_stored_hash_detected_as_invalid` ✅
7. `test_broken_chain_link_detected_as_invalid` ✅
8. `test_audit_api_endpoints_isolated` ✅
9. `test_tampering_scenario_3a_newly_created_chained_record_verifies_as_valid` ✅
10. `test_tampering_scenario_3b_modifying_contents_of_signed_record_returns_invalid` ✅
11. `test_tampering_scenario_3c_replacing_stored_hash_returns_invalid` ✅
12. `test_tampering_scenario_3d_breaking_previous_hash_reference_returns_invalid` ✅
13. `test_tampering_scenario_3e_legacy_record_without_proof_returns_unverifiable` ✅
14. `test_tampering_scenario_3f_modifying_earlier_record_causes_chain_endpoint_integrity_failure` ✅

#### System Health & Dashboard API
15. `test_root_health_endpoint` ✅
16. `test_v1_health_endpoint` ✅
17. `test_v1_dashboard_summary` ✅

#### Oversight Intelligence (Stage 3)
18. `test_budget_tracking_with_real_approval_events` ✅ (Feature B1)
19. `test_budget_exhaustion_blocks_further_approvals` ✅ (Feature B1)
20. `test_tier1_safe_bundling_succeeds_for_tier1_only` ✅ (Feature B1)
21. `test_tier3_friction_confirmation_phrase_enforcement` ✅ (Feature B2)
22. `test_synthetic_attention_drills_never_execute_tools` ✅ (Feature B3)
23. `test_oversight_health_score_deterministic_and_insufficient_data` ✅ (Feature B4)
24. `test_automatic_tightening_and_emergency_fail_closed` ✅ (Feature B5)
25. `test_evidence_report_endpoints` ✅ (Feature B6)

#### Core Safety Gateway & Sandboxing (Stage 2)
26. `test_scenario_1_permitted_read_ticket_executes` ✅
27. `test_scenario_2_unauthorized_email_is_held_or_blocked` ✅
28. `test_scenario_3_prohibited_customer_export_blocked` ✅
29. `test_scenario_4_refund_exceeding_limit_requires_approval` ✅
30. `test_scenario_5_valid_approval_executes_exact_action` ✅
31. `test_scenario_6_tampering_invalidates_fingerprint` ✅
32. `test_scenario_7_expired_approvals_cannot_execute` ✅
33. `test_scenario_8_reusing_approval_fails` ✅
34. `test_scenario_9_rejecting_approval_prevents_execution` ✅
35. `test_scenario_10_paused_agent_cannot_execute` ✅
36. `test_scenario_11_fail_closed_on_safety_failure` ✅
37. `test_scenario_12_untrusted_content_influence_reflected` ✅
38. `test_scenario_13_database_error_prevents_unauthorized_execution` ✅

---

## 💻 Running SafeRail Locally

### 1. Start Backend Server
```powershell
cd C:\Users\siddu\.gemini\antigravity\scratch\SafeRail\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Health Check: `http://127.0.0.1:8000/health`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Oversight Health API: `http://127.0.0.1:8000/api/v1/oversight/health`
- Download Evidence JSON: `http://127.0.0.1:8000/api/v1/evidence/report.json`
- Download Evidence CSV: `http://127.0.0.1:8000/api/v1/evidence/report.csv`

### 2. Start Frontend Application
```powershell
cd C:\Users\siddu\.gemini\antigravity\scratch\SafeRail\frontend
npm run dev
```
- Dashboard UI: `http://localhost:5173`
- Oversight Health Page: `http://localhost:5173/#/oversight` (or via sidebar navigation)
- Evidence Reports Page: `http://localhost:5173/#/reports`
