"""
SafeRail Demonstration Authorization Service.

NOTE ON SECURITY POSTURE:
SafeRail enforces backend role and identity validation for all privileged reviewer
operations (approvals, agent lifecycle resumption, restriction overrides).
In this local/demonstration environment, authorized reviewer identities are verified
against an authorized administrative registry (AUTHORIZED_REVIEWERS).

PRODUCTION LIMITATION:
This demonstration authorization model does NOT replace enterprise SSO/OIDC/SAML
identity providers or cryptographically signed bearer tokens (JWT/mTLS).
A frontend-supplied reviewer ID is validated against the authorized registry, but
production environments require verified cryptographic identity claims.
"""

from typing import Optional, Set
from fastapi import HTTPException, status

AUTHORIZED_REVIEWERS: Set[str] = {
    "reviewer-kavya",
    "admin-security",
    "supervisor-rahul",
    "compliance-officer"
}

def is_authorized_reviewer(reviewer_id: Optional[str]) -> bool:
    """Checks whether the provided reviewer_id belongs to the authorized administrative registry."""
    if not reviewer_id or not isinstance(reviewer_id, str):
        return False
    return reviewer_id.strip() in AUTHORIZED_REVIEWERS

def verify_reviewer_authorization(reviewer_id: Optional[str], action_context: str = "privileged operation") -> str:
    """
    Enforces backend authorization for reviewer operations.
    Raises HTTP 403 Forbidden if the reviewer ID is missing or unauthorized.
    """
    clean_id = (reviewer_id or "").strip()
    if not clean_id or clean_id not in AUTHORIZED_REVIEWERS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Authorization denied: '{clean_id or 'anonymous'}' is not an authorized reviewer "
                f"for {action_context}. Backend identity validation rejected the request."
            )
        )
    return clean_id
