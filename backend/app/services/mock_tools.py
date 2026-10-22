import json
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.safety import ToolExecutionModel, UntrustedContentModel

class MockToolExecutionError(Exception):
    pass

def execute_mock_tool(
    tool_name: str,
    action_details: Dict[str, Any],
    action_id: Optional[int] = None,
    db: Optional[Session] = None
) -> Dict[str, Any]:
    """
    Executes controlled mock tools in an isolated sandbox.
    Does not touch external systems, networks, real payment rails, or file systems.
    Records execution audit in tool_executions table.
    """
    result: Dict[str, Any] = {}
    
    if tool_name == "read_ticket":
        ticket_id = action_details.get("ticket_id", "TICKET-101")
        # Attempt to retrieve from untrusted contents table if available
        content_preview = "Standard support ticket requesting assistance."
        trust_label = "TRUSTED"
        if db:
            ticket = db.query(UntrustedContentModel).filter(UntrustedContentModel.id == ticket_id).first()
            if ticket:
                content_preview = ticket.content_text
                trust_label = ticket.trust_label

        result = {
            "ticket_id": ticket_id,
            "status": "OPEN",
            "trust_label": trust_label,
            "content": content_preview,
            "read_at": datetime.utcnow().isoformat()
        }

    elif tool_name == "send_email":
        to_addr = action_details.get("to")
        subject = action_details.get("subject", "No Subject")
        result = {
            "simulated_delivery": True,
            "recipient": to_addr,
            "subject": subject,
            "queued_in_mock_outbox": True,
            "message_id": f"mock-msg-{int(datetime.utcnow().timestamp())}"
        }

    elif tool_name == "issue_refund":
        customer_id = action_details.get("customer_id", "cust_unknown")
        amount = float(action_details.get("amount", 0.0))
        result = {
            "simulated_refund": True,
            "customer_id": customer_id,
            "amount": amount,
            "currency": "USD",
            "mock_tx_id": f"tx-ref-{int(datetime.utcnow().timestamp())}",
            "ledger_status": "POSTED"
        }

    elif tool_name == "export_customers":
        # Prohibited in normal paths, but safe mock if tested
        result = {
            "simulated_export": True,
            "records_count": 0,
            "notice": "Mock export sandbox only; no real customer records accessed."
        }

    elif tool_name == "delete_records":
        record_type = action_details.get("record_type", "record")
        record_id = action_details.get("record_id", "unknown")
        result = {
            "simulated_deletion": True,
            "record_type": record_type,
            "record_id": record_id,
            "deleted": True
        }

    elif tool_name == "update_profile":
        user_id = action_details.get("user_id", "user_unknown")
        updates = action_details.get("updates", {})
        result = {
            "simulated_update": True,
            "user_id": user_id,
            "updated_fields": list(updates.keys()),
            "status": "SUCCESS"
        }

    else:
        raise MockToolExecutionError(f"No mock handler available for tool '{tool_name}'")

    # Persist tool execution record if db session is active
    if db:
        try:
            exec_record = ToolExecutionModel(
                action_id=action_id,
                tool_name=tool_name,
                parameters_json=json.dumps(action_details),
                result_json=json.dumps(result),
                status="SUCCESS",
                executed_at=datetime.utcnow()
            )
            db.add(exec_record)
            db.commit()
        except Exception:
            db.rollback()

    return result
