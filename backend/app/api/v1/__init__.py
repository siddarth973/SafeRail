from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.gateway import router as gateway_router
from app.api.v1.agents import router as agents_router
from app.api.v1.untrusted import router as untrusted_router
from app.api.v1.audit import router as audit_router
from app.api.v1.oversight import router as oversight_router
from app.api.v1.evidence import router as evidence_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(dashboard_router, tags=["Dashboard"])
api_router.include_router(gateway_router, tags=["Gateway & Approvals"])
api_router.include_router(agents_router, tags=["Agent Lifecycle"])
api_router.include_router(untrusted_router, tags=["Untrusted Content"])
api_router.include_router(audit_router, tags=["Audit & Cryptographic Chain"])
api_router.include_router(oversight_router, tags=["Oversight Intelligence"])
api_router.include_router(evidence_router, tags=["Evidence & Compliance Reports"])
