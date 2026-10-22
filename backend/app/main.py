from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.init_db import init_db
from app.api.v1 import api_router
from app.schemas.safety import HealthCheckResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite database and seed initial fixtures
    init_db()
    yield

# Also initialize DB eagerly so standalone test runners or immediate queries work seamlessly
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="SafeRail AI Agent Safety & Control Gateway - DevHost 2026",
    version=settings.VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root health endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
def root_health():
    return HealthCheckResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        tagline=settings.TAGLINE,
        version=settings.VERSION,
        database="connected",
        timestamp=datetime.utcnow()
    )

# Include API v1 routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
