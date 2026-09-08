from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base, SessionLocal
from app.services.seed_data import seed_database
from app.api.routes.auth import router as auth_router
from app.api.routes.catalog import catalog_router, inventory_router
from app.api.routes.vendors import router as vendors_router
from app.api.routes.procurement import router as procurement_router
from app.api.routes.rfqs import router as rfqs_router
from app.api.routes.quotations import router as quotations_router
from app.api.routes.purchase_orders import router as po_router
from app.api.routes.notifications import router as notif_router
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.ai import router as ai_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.admin_db import router as admin_db_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Procurement Management System API (Deterministic + Analytical + Generative Intelligence)",
    version="2.0.0",
    lifespan=lifespan
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes under /api/v1
api_v1_prefix = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(catalog_router, prefix=api_v1_prefix)
app.include_router(inventory_router, prefix=api_v1_prefix)
app.include_router(vendors_router, prefix=api_v1_prefix)
app.include_router(procurement_router, prefix=api_v1_prefix)
app.include_router(rfqs_router, prefix=api_v1_prefix)
app.include_router(quotations_router, prefix=api_v1_prefix)
app.include_router(po_router, prefix=api_v1_prefix)
app.include_router(notif_router, prefix=api_v1_prefix)
app.include_router(knowledge_router, prefix=api_v1_prefix)
app.include_router(ai_router, prefix=api_v1_prefix)
app.include_router(recommendations_router, prefix=api_v1_prefix)
app.include_router(admin_db_router, prefix=api_v1_prefix)

@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": "2.0.0",
        "status": "online",
        "docs_url": "/docs",
        "ai_enabled": settings.AI_ENABLED
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
