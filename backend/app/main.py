"""
FastAPI Main Application — Omni-Channel Affiliate Intelligence Platform
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Affiliate Intelligence API",
    description="TikTok Shop affiliate automation: product → script → video → publish",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
from app.api.ecommerce import router as ecommerce_router
from app.api.social import router as social_router
from app.api.pipeline import router as pipeline_router

app.include_router(ecommerce_router)
app.include_router(social_router)
app.include_router(pipeline_router)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "affiliate-intelligence-api",
        "version": "2.0.0",
    }


@app.on_event("startup")
async def startup():
    """Khởi tạo DB tables nếu chưa có."""
    from app.core.database import engine
    from app.models.models import Base
    Base.metadata.create_all(bind=engine)
