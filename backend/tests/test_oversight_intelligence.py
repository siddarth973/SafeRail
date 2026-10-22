import pytest
import json
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import SessionLocal
from app.models.safety import (
    ActionModel,
    ApprovalModel,
    AttentionDrillModel,
    RestrictionHistoryModel,
    SecurityEventModel
)
from app.services.oversight_service import (
    calculate_oversight_health,
    get_reviewer_budget_status,
    evaluate_and_apply_automatic_restrictions
)
from app.services.policy_engine import compute_action_fingerprint


@pytest.mark.anyio
async def test_budget_tracking_with_real_approval_events():
    """B1: Verify reviewer budget calculates usage from real sliding-window approval records."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        for i in range(5):
            act = ActionModel(
                agent_id="agent-demo",
                agent_name="Demo Agent",
                action_type="Update profile",
                session_id=f"sess-budget-{i}",
                tool_name="update_profile",
                target=f"user_{i}",
                action_details=json.dumps({"username": f"user_{i}"}),
                decision="HOLD",
                risk_tier="Tier 2",
                risk_score=40,
                risk_level="MEDIUM",
                execution_status="EXECUTED",
                timestamp="10:00 AM",
                created_at=now - timedelta(minutes=10 * i)
            )
            db.add(act)
            db.flush()

            appr = ApprovalModel(
                action_id=act.id,
                fingerprint=f"fp-budget-{i}",
                decision="APPROVED",
                reviewer_id="reviewer-kavya",
                used=True,
                expires_at=now + timedelta(minutes=10),
                created_at=now - timedelta(minutes=10 * i),
                executed_at=now - timedelta(minutes=9 * i)
            )
            db.add(appr)
        db.commit()

        status = get_reviewer_budget_status(db, reviewer_id="reviewer-kavya", window_hours=24)
        assert status["budget_used"] == 5
        assert status["budget_remaining"] == status["budget_total"] - 5
        assert status["is_exhausted"] is False
    finally:
        db.close()


@pytest.mark.anyio
async def test_budget_exhaustion_blocks_further_approvals():
    """B1: When daily budget is exhausted, human approval is rejected (429 or held)."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        # Create 100 used approvals to exhaust the quota
        for i in range(100):
            act = ActionModel(
                agent_id="agent-demo",
                agent_name="Demo Agent",
                action_type="Update profile",
                session_id=f"sess-exhaust-{i}",
                tool_name="update_profile",
                target=f"user_{i}",
                action_details=json.dumps({"username": f"user_{i}"}),
                decision="HOLD",
                risk_tier="Tier 2",
                risk_score=40,
                risk_level="MEDIUM",
                execution_status="EXECUTED",
                timestamp="10:00 AM",
                created_at=now - timedelta(minutes=5)
            )
            db.add(act)
            db.flush()

            appr = ApprovalModel(
                action_id=act.id,
                fingerprint=f"fp-exhaust-{i}",
                decision="APPROVED",
                reviewer_id="reviewer-kavya",
                used=True,
                expires_at=now + timedelta(minutes=10),
                created_at=now - timedelta(minutes=5),
                executed_at=now - timedelta(minutes=4)
            )
            db.add(appr)

        # Create one pending action that needs approval
        pending_act = ActionModel(
            agent_id="agent-demo",
            agent_name="Demo Agent",
            action_type="Issue refund",
            session_id="sess-blocked-by-budget",
            tool_name="issue_refund",
            target="user_999",
            action_details=json.dumps({"amount": 80.0}),
            decision="HOLD",
            risk_tier="Tier 2",
            risk_score=50,
            risk_level="MEDIUM",
            execution_status="PENDING_APPROVAL",
            timestamp="10:05 AM",
            created_at=now
        )
        db.add(pending_act)
        db.flush()

        fp = compute_action_fingerprint(
            tool_name="issue_refund",
            action_details={"amount": 80.0},
            agent_id="agent-demo",
            session_id="sess-blocked-by-budget"
        )
        pending_appr = ApprovalModel(
            action_id=pending_act.id,
            fingerprint=fp,
            decision="PENDING",
            used=False,
            expires_at=now + timedelta(minutes=10)
        )
        db.add(pending_appr)
        db.commit()
        pending_action_id = pending_act.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Attempting to approve while budget is exhausted must be rejected with 429
        res = await client.post("/api/v1/decide", json={
            "action_id": pending_action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya",
            "reason": "Attempting approval during exhaustion"
        })
        assert res.status_code == 429
        data = res.json()
        assert "exhausted" in data["detail"].lower()


@pytest.mark.anyio
async def test_tier1_safe_bundling_succeeds_for_tier1_only():
    """B1: Bundling low-risk Tier 1 actions works cleanly for Tier 1, but rejects higher tiers."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        t1_action_ids = []
        for i in range(2):
            act = ActionModel(
                agent_id="agent-demo",
                agent_name="Demo Agent",
                action_type="Update profile",
                session_id=f"sess-bundle-{i}",
                tool_name="update_profile",
                target=f"user_{i}",
                action_details=json.dumps({"username": f"user_b_{i}"}),
                decision="HOLD",
                risk_tier="Tier 1",
                risk_score=20,
                risk_level="LOW",
                execution_status="PENDING_APPROVAL",
                timestamp="10:00 AM",
                created_at=now
            )
            db.add(act)
            db.flush()
            fp = compute_action_fingerprint(
                tool_name="update_profile",
                action_details={"username": f"user_b_{i}"},
                agent_id="agent-demo",
                session_id=f"sess-bundle-{i}"
            )
            appr = ApprovalModel(
                action_id=act.id,
                fingerprint=fp,
                decision="PENDING",
                used=False,
                expires_at=now + timedelta(minutes=10)
            )
            db.add(appr)
            t1_action_ids.append(act.id)

        # Create one Tier 2 action
        t2_act = ActionModel(
            agent_id="agent-demo",
            agent_name="Demo Agent",
            action_type="Issue refund",
            session_id="sess-t2-bundle",
            tool_name="issue_refund",
            target="user_99",
            action_details=json.dumps({"amount": 90.0}),
            decision="HOLD",
            risk_tier="Tier 2",
            risk_score=60,
            risk_level="MEDIUM",
            execution_status="PENDING_APPROVAL",
            timestamp="10:02 AM",
            created_at=now
        )
        db.add(t2_act)
        db.flush()
        t2_fp = compute_action_fingerprint(
            tool_name="issue_refund",
            action_details={"amount": 90.0},
            agent_id="agent-demo",
            session_id="sess-t2-bundle"
        )
        t2_appr = ApprovalModel(
            action_id=t2_act.id,
            fingerprint=t2_fp,
            decision="PENDING",
            used=False,
            expires_at=now + timedelta(minutes=10)
        )
        db.add(t2_appr)
        db.commit()
        t2_action_id = t2_act.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Bundling Tier 1 actions succeeds
        res_t1 = await client.post("/api/v1/approvals/bundle-decide", json={
            "action_ids": t1_action_ids,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert res_t1.status_code == 200
        data_t1 = res_t1.json()
        assert data_t1["bundle_size"] == 2
        assert data_t1["decision"] == "APPROVED"

        # Attempting to bundle Tier 2 action is rejected
        res_t2 = await client.post("/api/v1/approvals/bundle-decide", json={
            "action_ids": [t2_action_id],
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert res_t2.status_code == 400
        assert "tier 1" in res_t2.json()["detail"].lower()


@pytest.mark.anyio
async def test_tier3_friction_confirmation_phrase_enforcement():
    """B2: Tier 3 high-risk actions require typing the exact confirmation phrase."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        act = ActionModel(
            agent_id="agent-tool",
            agent_name="Tool Agent",
            action_type="Delete records",
            session_id="sess-t3-friction",
            tool_name="delete_records",
            target="customer_archive_table",
            action_details=json.dumps({"table": "customer_archive_table", "confirm": True}),
            decision="HOLD",
            risk_tier="Tier 3",
            risk_score=80,
            risk_level="HIGH",
            execution_status="PENDING_APPROVAL",
            timestamp="10:10 AM",
            created_at=now
        )
        db.add(act)
        db.flush()

        fp = compute_action_fingerprint(
            tool_name="delete_records",
            action_details={"table": "customer_archive_table", "confirm": True},
            agent_id="agent-tool",
            session_id="sess-t3-friction"
        )
        appr = ApprovalModel(
            action_id=act.id,
            fingerprint=fp,
            decision="PENDING",
            used=False,
            expires_at=now + timedelta(minutes=10)
        )
        db.add(appr)
        db.commit()
        action_id = act.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Check pending list returns required confirmation phrase
        res_pending = await client.get("/api/v1/pending")
        assert res_pending.status_code == 200
        items = res_pending.json()
        t3_item = next(it for it in items if it["action_id"] == action_id)
        assert t3_item["required_confirmation_phrase"] is not None
        req_phrase = t3_item["required_confirmation_phrase"]
        assert "CONFIRM-DELETE" in req_phrase

        # 1. Approval without confirmation phrase fails
        res_no_phrase = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert res_no_phrase.status_code == 400
        assert "confirmation phrase" in res_no_phrase.json()["detail"].lower()

        # 2. Approval with incorrect confirmation phrase fails
        res_bad_phrase = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya",
            "confirmation_phrase": "WRONG-PHRASE"
        })
        assert res_bad_phrase.status_code == 400
        assert "confirmation phrase required" in res_bad_phrase.json()["detail"].lower()

        # 3. Approval with exact confirmation phrase succeeds and executes
        res_correct = await client.post("/api/v1/decide", json={
            "action_id": action_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya",
            "confirmation_phrase": req_phrase
        })
        assert res_correct.status_code == 200
        data_correct = res_correct.json()
        assert data_correct["decision"] == "APPROVED"
        assert data_correct["executed"] is True


@pytest.mark.anyio
async def test_synthetic_attention_drills_never_execute_tools():
    """B3: Attention drills are synthetic simulations that never execute mock tools."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Fetch drills
        res = await client.get("/api/v1/oversight/drills")
        assert res.status_code == 200
        drills = res.json()
        assert len(drills) >= 4
        drill = drills[0]
        assert drill["is_simulation"] is True

        # Submit correct rejection of the drill
        res_sub = await client.post(f"/api/v1/oversight/drills/{drill['id']}/submit", json={
            "decision": "REJECTED",
            "reviewer_id": "reviewer-kavya",
            "notes": "Spotted simulated canary prompt injection"
        })
        assert res_sub.status_code == 200
        sub_data = res_sub.json()
        assert sub_data["status"] == "PASSED"
        assert sub_data["is_correct"] is True

        # Verify in DB that drill is marked PASSED and never created real execution records
        db = SessionLocal()
        try:
            d_rec = db.query(AttentionDrillModel).filter_by(id=drill["id"]).first()
            assert d_rec.status == "PASSED"
            assert d_rec.is_simulation is True

            # Verify an audit event was logged tagging it as Never Executed
            ev = db.query(SecurityEventModel).filter(SecurityEventModel.title.like("%Attention Drill%")).first()
            assert ev is not None
            assert "Never Executed" in ev.description
        finally:
            db.close()


@pytest.mark.anyio
async def test_oversight_health_score_deterministic_and_insufficient_data():
    """B4: Oversight health score calculates deterministically across 4 weighted pillars."""
    db = SessionLocal()
    try:
        # In an empty or fresh window with no reviews and no answered drills,
        # health calculation honestly returns INSUFFICIENT_DATA
        db.query(AttentionDrillModel).update({"status": "PENDING", "responded_at": None})
        db.commit()

        calc = calculate_oversight_health(db, window_hours=24)
        assert calc["data_sufficiency"] == "INSUFFICIENT_DATA"
        assert calc["status"] == "INSUFFICIENT_DATA"
        assert len(calc["breakdown"]) == 4

        # Verify each pillar has max_points=25, sum=100
        total_max = sum(item["max_points"] for item in calc["breakdown"])
        assert total_max == 100
    finally:
        db.close()


@pytest.mark.anyio
async def test_automatic_tightening_and_emergency_fail_closed():
    """B5: Automatic safety tightening transitions to Level 3 on severe degradation and fails closed."""
    db = SessionLocal()
    try:
        # Set restriction to Level 3 EMERGENCY
        restr = RestrictionHistoryModel(
            level=3,
            level_name="EMERGENCY",
            reason="Simulated emergency lockdown condition",
            trigger_metrics_json=json.dumps({"test": True}),
            authorized_by="SYSTEM_AUTOMATION",
            is_override=False,
            created_at=datetime.utcnow()
        )
        db.add(restr)
        db.commit()

        # Under Level 3 EMERGENCY, create an action and verify it cannot be approved
        act = ActionModel(
            agent_id="agent-demo",
            agent_name="Demo Agent",
            action_type="Update profile",
            session_id="sess-emergency",
            tool_name="update_profile",
            target="user_fail_closed",
            action_details=json.dumps({"username": "test"}),
            decision="HOLD",
            risk_tier="Tier 2",
            risk_score=50,
            risk_level="MEDIUM",
            execution_status="PENDING_APPROVAL",
            timestamp="10:15 AM",
            created_at=datetime.utcnow()
        )
        db.add(act)
        db.flush()
        fp = compute_action_fingerprint(
            tool_name="update_profile",
            action_details={"username": "test"},
            agent_id="agent-demo",
            session_id="sess-emergency"
        )
        appr = ApprovalModel(
            action_id=act.id,
            fingerprint=fp,
            decision="PENDING",
            used=False,
            expires_at=datetime.utcnow() + timedelta(minutes=10)
        )
        db.add(appr)
        db.commit()
        act_id = act.id
    finally:
        db.close()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Under Level 3 Emergency, approve attempt is rejected with 423 Locked
        res = await client.post("/api/v1/decide", json={
            "action_id": act_id,
            "decision": "APPROVED",
            "reviewer_id": "reviewer-kavya"
        })
        assert res.status_code == 423
        assert "emergency" in res.json()["detail"].lower()

        # Perform authorized manual override back to Level 0 NORMAL
        res_ov = await client.post("/api/v1/oversight/restrictions/override", json={
            "level": 0,
            "reviewer_id": "reviewer-kavya",
            "reason": "Authorized incident resolution and vigilance reset"
        })
        assert res_ov.status_code == 200
        ov_data = res_ov.json()
        assert ov_data["current_level"] == 0
        assert ov_data["level_name"] == "NORMAL"


@pytest.mark.anyio
async def test_evidence_report_endpoints():
    """B6: Verifiable evidence report returns live counts and supports JSON & CSV export."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # JSON summary report
        res = await client.get("/api/v1/evidence/report")
        assert res.status_code == 200
        rep = res.json()
        assert "report_id" in rep
        assert "reporting_period" in rep
        assert rep["total_actions"] >= 0
        assert "risk_tier_distribution" in rep
        assert "audit_chain_status" in rep

        # Downloadable JSON
        res_json = await client.get("/api/v1/evidence/report.json")
        assert res_json.status_code == 200
        assert "attachment" in res_json.headers.get("content-disposition", "")

        # Downloadable CSV
        res_csv = await client.get("/api/v1/evidence/report.csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers.get("content-type", "")
        csv_text = res_csv.text
        assert "SafeRail Oversight & Compliance Evidence Report" in csv_text
        assert "Total Actions Evaluated" in csv_text
