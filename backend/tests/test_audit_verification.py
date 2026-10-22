import pytest
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.session import Base, get_db
from app.models.safety import SecurityEventModel
from app.services.audit_service import (
    GENESIS_PREV_HASH,
    compute_audit_hash,
    create_audit_event,
    verify_single_event_record,
    verify_audit_event_by_id,
    verify_entire_audit_chain
)

# Isolated in-memory SQLite database setup for testing to prevent mutating demo/prod database
TEST_DATABASE_URL = "sqlite:///:memory:"

@pytest.fixture
def isolated_db_session():
    """Provides an isolated in-memory SQLite database session for audit tests."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

def test_canonical_hash_determinism():
    """Test 1: Canonical SHA-256 calculation is deterministic and sensitive to any modification."""
    hash1 = compute_audit_hash(
        sequence_number=1,
        prev_hash=GENESIS_PREV_HASH,
        title="Test Event",
        description="A deterministic test action",
        status_tag="APPROVED",
        time_str="12:00 PM",
        metadata={"key": "value"}
    )
    
    # Identical inputs must yield identical hash
    hash2 = compute_audit_hash(
        sequence_number=1,
        prev_hash=GENESIS_PREV_HASH,
        title="Test Event",
        description="A deterministic test action",
        status_tag="APPROVED",
        time_str="12:00 PM",
        metadata={"key": "value"}
    )
    assert hash1 == hash2
    assert len(hash1) == 64

    # Any change to description alters hash
    hash_diff_desc = compute_audit_hash(
        sequence_number=1,
        prev_hash=GENESIS_PREV_HASH,
        title="Test Event",
        description="A deterministic test action - MODIFIED",
        status_tag="APPROVED",
        time_str="12:00 PM",
        metadata={"key": "value"}
    )
    assert hash1 != hash_diff_desc

    # Any change to prev_hash alters hash
    hash_diff_prev = compute_audit_hash(
        sequence_number=1,
        prev_hash="deadbeef" * 8,
        title="Test Event",
        description="A deterministic test action",
        status_tag="APPROVED",
        time_str="12:00 PM",
        metadata={"key": "value"}
    )
    assert hash1 != hash_diff_prev

def test_genesis_event_creation_and_verification(isolated_db_session):
    """Test 2: First event chains to GENESIS anchor and verifies as VALID."""
    db = isolated_db_session
    event = create_audit_event(
        db=db,
        title="Genesis Test Event",
        description="First block in isolated audit chain",
        status_tag="INFO",
        time_str="10:00 AM"
    )

    assert event.sequence_number == 1
    assert event.prev_hash == GENESIS_PREV_HASH
    assert event.current_hash is not None
    assert len(event.current_hash) == 64

    # Verify directly
    result = verify_single_event_record(event, expected_predecessor=None)
    assert result["status"] == "VALID"
    assert result["event_id"] == event.id
    assert result["computed_hash"] == event.current_hash
    assert result["stored_hash"] == event.current_hash

def test_chained_events_sequential_verification(isolated_db_session):
    """Test 3: Multiple sequentially chained events verify cleanly."""
    db = isolated_db_session
    ev1 = create_audit_event(db, "Action 1", "First simulated action", "APPROVED", time_str="10:01 AM")
    ev2 = create_audit_event(db, "Action 2", "Second simulated action", "BLOCKED", time_str="10:02 AM")
    ev3 = create_audit_event(db, "Action 3", "Third simulated action", "WARNING", time_str="10:03 AM")

    assert ev2.prev_hash == ev1.current_hash
    assert ev3.prev_hash == ev2.current_hash
    assert ev1.sequence_number == 1
    assert ev2.sequence_number == 2
    assert ev3.sequence_number == 3

    # Verify full chain
    chain_res = verify_entire_audit_chain(db)
    assert chain_res["status"] == "VALID"
    assert chain_res["total_events"] == 3
    assert chain_res["valid_count"] == 3
    assert chain_res["invalid_count"] == 0
    assert chain_res["unverifiable_count"] == 0
    assert len(chain_res["broken_links"]) == 0

def test_legacy_record_reported_unverifiable(isolated_db_session):
    """Test 4: Pre-Stage 2 legacy records lacking cryptographic hashes are honestly marked UNVERIFIABLE."""
    db = isolated_db_session
    # Create legacy event directly without hash proof
    legacy_event = SecurityEventModel(
        time_str="09:00 AM",
        title="Legacy Unhashed Event",
        description="Created prior to SHA-256 chain implementation",
        status_tag="INFO",
        prev_hash=None,
        current_hash=None,
        sequence_number=None
    )
    db.add(legacy_event)
    db.commit()
    db.refresh(legacy_event)

    result = verify_single_event_record(legacy_event, expected_predecessor=None)
    assert result["status"] == "UNVERIFIABLE"
    assert "Legacy record" in result["reason"]
    assert result["stored_hash"] is None
    assert result["computed_hash"] is None

    # Full chain assessment with legacy records
    chain_res = verify_entire_audit_chain(db)
    assert chain_res["status"] == "UNVERIFIABLE"
    assert chain_res["unverifiable_count"] == 1
    assert chain_res["valid_count"] == 0

def test_tampered_record_contents_detected_as_invalid(isolated_db_session):
    """Test 5: Content tampering (e.g. modifying description) is detected and reported as INVALID."""
    db = isolated_db_session
    ev = create_audit_event(
        db,
        title="Payment Authorized",
        description="Legitimate transfer of $50.00",
        status_tag="APPROVED",
        time_str="11:00 AM"
    )

    # Tamper with description in DB
    ev.description = "MALICIOUS OVERRIDE: transfer $500,000.00 to offshore"
    db.commit()
    db.refresh(ev)

    result = verify_single_event_record(ev, expected_predecessor=None)
    assert result["status"] == "INVALID"
    assert "Content tampering detected" in result["reason"]
    assert result["computed_hash"] != result["stored_hash"]

def test_tampered_stored_hash_detected_as_invalid(isolated_db_session):
    """Test 6: Tampering directly with the stored current_hash is detected as INVALID."""
    db = isolated_db_session
    ev = create_audit_event(
        db,
        title="Access Granted",
        description="Normal access grant",
        status_tag="APPROVED",
        time_str="11:15 AM"
    )

    # Tamper with the stored hash
    ev.current_hash = "f" * 64
    db.commit()
    db.refresh(ev)

    result = verify_single_event_record(ev, expected_predecessor=None)
    assert result["status"] == "INVALID"
    assert "Content tampering detected" in result["reason"]

def test_broken_chain_link_detected_as_invalid(isolated_db_session):
    """Test 7: Tampering with prev_hash breaks the chain linkage and marks ledger INVALID."""
    db = isolated_db_session
    ev1 = create_audit_event(db, "Event 1", "Predecessor", "INFO", time_str="11:20 AM")
    ev2 = create_audit_event(db, "Event 2", "Successor", "APPROVED", time_str="11:21 AM")

    # Tamper with block 2's prev_hash
    ev2.prev_hash = "0" * 64
    db.commit()
    db.refresh(ev2)

    # Individual verification of block 2 detects broken predecessor pointer
    res = verify_single_event_record(ev2, expected_predecessor=ev1)
    assert res["status"] == "INVALID"
    assert "Broken chain link" in res["reason"]

    # Full chain verification fails with INVALID and records the broken link
    chain_res = verify_entire_audit_chain(db)
    assert chain_res["status"] == "INVALID"
    assert chain_res["invalid_count"] >= 1
    assert len(chain_res["broken_links"]) >= 1

@pytest.mark.anyio
async def test_audit_api_endpoints_isolated():
    """Test 8: FastAPI endpoints for listing, single verification, and chain audit work properly."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        # Seed test events in isolated DB
        db = TestingSessionLocal()
        ev1 = create_audit_event(db, "API Test 1", "Desc 1", "INFO", time_str="12:00 PM")
        ev2 = create_audit_event(db, "API Test 2", "Desc 2", "APPROVED", time_str="12:05 PM")
        legacy = SecurityEventModel(
            time_str="08:00 AM",
            title="Old Legacy",
            description="No hash",
            status_tag="INFO"
        )
        db.add(legacy)
        db.commit()
        db.refresh(legacy)
        
        # Save attributes before session closes to avoid DetachedInstanceError
        ev1_id = ev1.id
        ev1_hash = ev1.current_hash
        legacy_id = legacy.id
        db.close()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Test listing events
            res = await client.get("/api/v1/audit/events")
            assert res.status_code == 200
            events = res.json()
            assert len(events) == 3

            # 2. Test verify valid event
            res_val = await client.post(f"/api/v1/audit/verify/{ev1_id}")
            assert res_val.status_code == 200
            val_data = res_val.json()
            assert val_data["status"] == "VALID"
            assert val_data["computed_hash"] == ev1_hash

            # 3. Test verify legacy event
            res_leg = await client.post(f"/api/v1/audit/verify/{legacy_id}")
            assert res_leg.status_code == 200
            leg_data = res_leg.json()
            assert leg_data["status"] == "UNVERIFIABLE"

            # 4. Test verify non-existent event
            res_404 = await client.post("/api/v1/audit/verify/999999")
            assert res_404.status_code == 404

            # 5. Test chain verification
            res_chain = await client.post("/api/v1/audit/verify-chain")
            assert res_chain.status_code == 200
            chain_data = res_chain.json()
            assert chain_data["status"] == "VALID"
            assert chain_data["valid_count"] == 2
            assert chain_data["unverifiable_count"] == 1
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)

# ==============================================================================
# SAFE-RAIL STAGE 2 DEDICATED AUDIT TAMPERING VERIFICATION TESTS (TASKS 3A - 3F)
# All tests execute against an isolated in-memory SQLite database.
# ==============================================================================

def test_tampering_scenario_3a_newly_created_chained_record_verifies_as_valid(isolated_db_session):
    """
    Scenario 3A: A newly created, correctly chained record verifies as VALID.
    Proves that appending a new block to an existing chain computes the proper SHA-256
    hash, binds to the predecessor hash, and verifies as VALID both at the service layer
    and via the verification API.
    """
    db = isolated_db_session
    # 1. Establish initial chained blocks
    ev1 = create_audit_event(db, "System Boot", "SafeRail gateway initial boot", "INFO", time_str="09:00 AM")
    ev2 = create_audit_event(db, "Policy Init", "Policy engine rules loaded", "APPROVED", time_str="09:05 AM")
    assert ev2.prev_hash == ev1.current_hash

    # 2. Append a newly created, correctly chained record
    new_event = create_audit_event(
        db=db,
        title="Tool Call Intercepted",
        description="read_ticket executed for support dispatch",
        status_tag="APPROVED",
        time_str="09:10 AM",
        metadata={"tool": "read_ticket", "ticket_id": "TICKET-101"}
    )

    # 3. Verify linkage and cryptographic fields
    assert new_event.sequence_number == 3
    assert new_event.prev_hash == ev2.current_hash
    assert new_event.current_hash is not None
    assert len(new_event.current_hash) == 64

    # 4. Prove single verification returns VALID
    record_result = verify_single_event_record(new_event, expected_predecessor=ev2)
    assert record_result["status"] == "VALID"
    assert record_result["computed_hash"] == new_event.current_hash
    assert record_result["stored_hash"] == new_event.current_hash
    assert record_result["prev_hash"] == ev2.current_hash
    assert record_result["expected_prev_hash"] == ev2.current_hash
    assert "verified successfully" in record_result["reason"]

    # 5. Prove database by-ID verification returns VALID
    id_result = verify_audit_event_by_id(db, new_event.id)
    assert id_result["status"] == "VALID"
    assert id_result["event_id"] == new_event.id
    assert id_result["computed_hash"] == new_event.current_hash

def test_tampering_scenario_3b_modifying_contents_of_signed_record_returns_invalid(isolated_db_session):
    """
    Scenario 3B: Modifying the contents of a signed record causes verification to return INVALID.
    Proves that altering description, title, or status tag after block creation is immediately
    detected as content tampering.
    """
    db = isolated_db_session
    ev = create_audit_event(
        db=db,
        title="Authorization Granted",
        description="Authorized financial transaction for customer_4821 amount $50.00",
        status_tag="APPROVED",
        time_str="10:00 AM",
        metadata={"amount": 50.0}
    )
    original_hash = ev.current_hash

    # Sub-test B1: Tamper with description
    ev.description = "MALICIOUS OVERRIDE: Wire transfer $500,000.00 to offshore account"
    db.commit()
    db.refresh(ev)

    res_desc = verify_single_event_record(ev, expected_predecessor=None)
    assert res_desc["status"] == "INVALID"
    assert "Content tampering detected" in res_desc["reason"]
    assert res_desc["stored_hash"] == original_hash
    assert res_desc["computed_hash"] != original_hash

    # Sub-test B2: Tamper with title
    ev.description = "Authorized financial transaction for customer_4821 amount $50.00"  # restore
    ev.title = "Forged Admin Override"
    db.commit()
    db.refresh(ev)

    res_title = verify_single_event_record(ev, expected_predecessor=None)
    assert res_title["status"] == "INVALID"
    assert "Content tampering detected" in res_title["reason"]

    # Sub-test B3: Tamper with status tag
    ev.title = "Authorization Granted"  # restore
    ev.status_tag = "BLOCKED"
    db.commit()
    db.refresh(ev)

    res_tag = verify_single_event_record(ev, expected_predecessor=None)
    assert res_tag["status"] == "INVALID"
    assert "Content tampering detected" in res_tag["reason"]

    # Verify by ID also reports INVALID
    id_res = verify_audit_event_by_id(db, ev.id)
    assert id_res["status"] == "INVALID"

def test_tampering_scenario_3c_replacing_stored_hash_returns_invalid(isolated_db_session):
    """
    Scenario 3C: Replacing a stored SHA-256 hash with an incorrect value causes verification to return INVALID.
    Proves that direct database modification of the current_hash column is rejected.
    """
    db = isolated_db_session
    ev = create_audit_event(
        db=db,
        title="Access Granted",
        description="Standard privileged operator logon",
        status_tag="APPROVED",
        time_str="11:00 AM"
    )

    # Sub-test C1: Replace with arbitrary 64-character hex string
    ev.current_hash = "deadbeef" * 8
    db.commit()
    db.refresh(ev)

    res = verify_single_event_record(ev, expected_predecessor=None)
    assert res["status"] == "INVALID"
    assert "Content tampering detected" in res["reason"]
    assert res["stored_hash"] == "deadbeef" * 8

    # Sub-test C2: Replace with forged or corrupt hash string
    ev.current_hash = "forged_non_matching_hash"
    db.commit()
    db.refresh(ev)

    res2 = verify_single_event_record(ev, expected_predecessor=None)
    assert res2["status"] == "INVALID"
    assert res2["stored_hash"] == "forged_non_matching_hash"

    id_res = verify_audit_event_by_id(db, ev.id)
    assert id_res["status"] == "INVALID"

def test_tampering_scenario_3d_breaking_previous_hash_reference_returns_invalid(isolated_db_session):
    """
    Scenario 3D: Breaking a record's previous-hash reference causes verification to return INVALID.
    Proves that if an attacker alters the prev_hash link, the chain break is immediately flagged.
    """
    db = isolated_db_session
    ev1 = create_audit_event(db, "Genesis Action", "Root block event", "INFO", time_str="11:30 AM")
    ev2 = create_audit_event(db, "Subsequent Action", "Chained block event", "APPROVED", time_str="11:35 AM")

    # Break ev2's predecessor reference
    ev2.prev_hash = "0" * 64
    db.commit()
    db.refresh(ev2)

    res = verify_single_event_record(ev2, expected_predecessor=ev1)
    assert res["status"] == "INVALID"
    assert "Broken chain link" in res["reason"]
    assert res["prev_hash"] == "0" * 64
    assert res["expected_prev_hash"] == ev1.current_hash

    id_res = verify_audit_event_by_id(db, ev2.id)
    assert id_res["status"] == "INVALID"
    assert "Broken chain link" in id_res["reason"]

def test_tampering_scenario_3e_legacy_record_without_proof_returns_unverifiable(isolated_db_session):
    """
    Scenario 3E: A legacy record without cryptographic proof returns UNVERIFIABLE.
    Proves that pre-Stage 2 records lacking SHA-256 hashes are honestly reported as UNVERIFIABLE
    rather than falsely claiming validity.
    """
    db = isolated_db_session
    legacy_record = SecurityEventModel(
        time_str="08:30 AM",
        title="Legacy Unhashed Record",
        description="Recorded prior to SHA-256 cryptographic chain activation",
        status_tag="INFO",
        prev_hash=None,
        current_hash=None,
        sequence_number=None
    )
    db.add(legacy_record)
    db.commit()
    db.refresh(legacy_record)

    res = verify_single_event_record(legacy_record, expected_predecessor=None)
    assert res["status"] == "UNVERIFIABLE"
    assert res["stored_hash"] is None
    assert res["computed_hash"] is None
    assert "Legacy record: created without cryptographic hash chaining proof." in res["reason"]

    id_res = verify_audit_event_by_id(db, legacy_record.id)
    assert id_res["status"] == "UNVERIFIABLE"

    # Full chain assessment with only legacy records must be UNVERIFIABLE
    chain_res = verify_entire_audit_chain(db)
    assert chain_res["status"] == "UNVERIFIABLE"
    assert chain_res["valid_count"] == 0
    assert chain_res["unverifiable_count"] == 1
    assert "legacy entries without cryptographic proofs" in chain_res["message"]

@pytest.mark.anyio
async def test_tampering_scenario_3f_modifying_earlier_record_causes_chain_endpoint_integrity_failure():
    """
    Scenario 3F: Modifying an earlier record causes the chain verification endpoint
    to report the integrity failure instead of claiming the entire chain is valid.
    Proves via the FastAPI HTTP client and verify-chain endpoint that:
      1. An untampered multi-block chain reports VALID.
      2. Modifying an earlier historical block causes POST /api/v1/audit/verify-chain
         to return status: 'INVALID', broken_links: [...], and message indicating FAILED.
      3. Forging an earlier block's hash causes downstream link breakage at the successor block.
    """
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        db = TestingSessionLocal()
        # Create a sequential 4-block chain
        b1 = create_audit_event(db, "Block 1", "Genesis operational check", "INFO", time_str="12:00 PM")
        b2 = create_audit_event(db, "Block 2", "Gateway proxy started", "APPROVED", time_str="12:05 PM")
        b3 = create_audit_event(db, "Block 3", "Ticket T-900 read executed", "APPROVED", time_str="12:10 PM")
        b4 = create_audit_event(db, "Block 4", "Refund processed $45.00", "APPROVED", time_str="12:15 PM")
        b2_id = b2.id
        db.close()

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Verify that initially, the chain verification endpoint returns VALID
            res_initial = await client.post("/api/v1/audit/verify-chain")
            assert res_initial.status_code == 200
            initial_data = res_initial.json()
            assert initial_data["status"] == "VALID"
            assert initial_data["valid_count"] == 4
            assert initial_data["invalid_count"] == 0
            assert len(initial_data["broken_links"]) == 0

            # 2. Tamper with an EARLIER record (Block 2)
            db = TestingSessionLocal()
            target_b2 = db.query(SecurityEventModel).filter(SecurityEventModel.id == b2_id).first()
            target_b2.description = "MALICIOUS TAMPERING: Modified historical block #2"
            db.commit()
            db.close()

            # 3. Call chain verification endpoint again: it MUST report integrity failure
            res_tampered = await client.post("/api/v1/audit/verify-chain")
            assert res_tampered.status_code == 200
            tampered_data = res_tampered.json()

            # Crucial asserts proving Scenario F:
            assert tampered_data["status"] == "INVALID"  # NOT VALID!
            assert tampered_data["invalid_count"] >= 1
            assert len(tampered_data["broken_links"]) >= 1
            assert "Integrity check FAILED" in tampered_data["message"]
            
            # The broken link reports the exact event id that was tampered
            tampered_link = next((item for item in tampered_data["broken_links"] if item["event_id"] == b2_id), None)
            assert tampered_link is not None
            assert tampered_link["status"] == "INVALID"
            assert "Content tampering detected" in tampered_link["reason"]
            assert tampered_link["stored_hash"] != tampered_link["computed_hash"]
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)

