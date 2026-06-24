"""
FastAPI Main Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="TikTok Affiliate Automation API",
    description="API quản lý tự động tạo video TikTok cho Shopee Affiliate",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "tiktok-affiliate-api"}


# Import routers (sẽ thêm dần)
# from app.api import products, videos, analytics
# app.include_router(products.router, prefix="/api/products", tags=["products"])
# app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
