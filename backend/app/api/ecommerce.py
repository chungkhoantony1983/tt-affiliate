"""
E-commerce API endpoints:
  POST /api/ecommerce/sync     — trigger sync all platforms
  GET  /api/products/          — list products (paginated, filterable)
  GET  /api/products/{id}      — product detail
  GET  /api/products/top       — top priority products
"""
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Product
from app.services.ecommerce.sync_orchestrator import SyncOrchestrator
from app.services.ecommerce.product_ranker import ProductRanker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["ecommerce"])


@router.post("/ecommerce/sync")
async def trigger_sync(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Trigger product sync từ tất cả e-commerce platforms đã configure.
    Chạy background để không block response.
    """
    def run_sync():
        import logging
        from app.core.database import SessionLocal
        from app.services.ecommerce.sync_orchestrator import SyncOrchestrator
        db = SessionLocal()
        try:
            orchestrator = SyncOrchestrator(db)
            result = orchestrator.run()
            logging.getLogger(__name__).info(f"Sync completed: {result}")
        except Exception as e:
            logging.getLogger(__name__).error(f"Sync failed: {e}", exc_info=True)
        finally:
            db.close()

    background_tasks.add_task(run_sync)
    return {"message": "Sync started", "status": "running"}


@router.post("/ecommerce/sync/wait")
async def trigger_sync_wait(db: Session = Depends(get_db)):
    """
    Trigger sync và chờ kết quả (dùng cho testing / N8N workflow).
    """
    try:
        orchestrator = SyncOrchestrator(db)
        result = orchestrator.run()
        return {"message": "Sync completed", "result": result}
    except Exception as e:
        logger.error(f"Sync error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/products/")
def list_products(
    platform: Optional[str] = Query(None, description="Filter by platform: shopee, lazada"),
    category: Optional[str] = Query(None),
    is_priority: Optional[bool] = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("sales_count", description="sales_count | discount_percent | rating | created_at"),
    db: Session = Depends(get_db),
):
    """List sản phẩm với filter và pagination."""
    query = db.query(Product)

    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    if platform:
        query = query.filter(Product.source_platform == platform)
    if category:
        query = query.filter(Product.category.ilike(f"%{category}%"))
    if is_priority is not None:
        query = query.filter(Product.is_priority == is_priority)

    # Sort
    sort_column = {
        "sales_count": Product.sales_count,
        "discount_percent": Product.discount_percent,
        "rating": Product.rating,
        "created_at": Product.created_at,
    }.get(sort_by, Product.sales_count)

    query = query.order_by(sort_column.desc())

    total = query.count()
    products = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "products": [_serialize_product(p) for p in products],
    }


@router.get("/products/top")
def get_top_products(
    limit: int = Query(10, ge=1, le=50),
    platform: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lấy danh sách sản phẩm được ưu tiên tạo video nhất."""
    ranker = ProductRanker()
    products = ranker.get_top_products(db, limit=limit, platform=platform)
    return {
        "products": [_serialize_product(p) for p in products],
    }


@router.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Chi tiết một sản phẩm."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize_product(product)


def _serialize_product(p: Product) -> dict:
    """Serialize Product model sang dict."""
    return {
        "id": p.id,
        "source_platform": p.source_platform,
        "source_item_id": p.source_item_id,
        "name": p.name,
        "price": p.price,
        "original_price": p.original_price,
        "discount_percent": p.discount_percent,
        "category": p.category,
        "description": p.description[:500] if p.description else "",
        "image_urls": json.loads(p.image_urls) if p.image_urls else [],
        "affiliate_link": p.affiliate_link,
        "source_url": p.source_url,
        "stock": p.stock,
        "sales_count": p.sales_count,
        "rating": p.rating,
        "is_active": p.is_active,
        "is_priority": p.is_priority,
        "video_count": p.video_count,
        "last_synced": p.last_synced.isoformat() if p.last_synced else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }
