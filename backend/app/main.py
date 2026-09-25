import time
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.admin import router as admin_router
from app.api.v1.agents import router as agents_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.auth import router as auth_router
from app.api.v1.conversations import router as conversations_router
from app.api.v1.tickets import router as tickets_router
from app.core.config import settings
from app.core.exceptions import DomainException
from app.schemas.api import ProblemDetail

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Enterprise-grade AI-assisted complaint operations platform with policy governance, RAG, and automated ticketing.",
    version="2.0.0"
)

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Observability & Correlation ID Middleware
@app.middleware("http")
async def add_correlation_and_timing(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Sec"] = f"{process_time:.4f}"
    return response

# 3. Global RFC 7807 Error Handlers
@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    problem = ProblemDetail(
        title=exc.title,
        status=exc.status_code,
        detail=exc.detail,
        instance=str(request.url.path)
    )
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump())

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    problem = ProblemDetail(
        title="HTTP Error",
        status=exc.status_code,
        detail=str(exc.detail),
        instance=str(request.url.path)
    )
    return JSONResponse(status_code=exc.status_code, content=problem.model_dump())

# 4. Mount API v1 Routers
app.include_router(auth_router, prefix="/v1")
app.include_router(conversations_router, prefix="/v1")
app.include_router(tickets_router, prefix="/v1")
app.include_router(agents_router, prefix="/v1")
app.include_router(analytics_router, prefix="/v1")
app.include_router(admin_router, prefix="/v1")

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "2.0.0",
        "policy_version": settings.POLICY_VERSION
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "Welcome to Intelligent Complaint Management & AI Ticketing Platform API",
        "documentation": "/docs",
        "openapi": "/openapi.json",
        "version": "2.0.0"
    }
