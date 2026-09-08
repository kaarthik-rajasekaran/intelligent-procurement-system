from typing import List, Optional
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Vendor
from app.schemas.domain import VendorOut, VendorRecommendationOut, RAGVendorRecommendation
from app.intelligence.analytical import get_vendor_recommendations
from app.intelligence.vendor_rag import get_vendor_recommendations_rag
from app.intelligence import recommendation_cache
from app.ai.provider import get_llm_provider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendors", tags=["Vendors"])

@router.get("", response_model=List[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    results = []
    for v in vendors:
        badges = [b.badge_type for b in v.badges]
        results.append(
            VendorOut(
                id=v.id,
                name=v.name,
                email=v.email,
                phone=v.phone,
                is_active=v.is_active,
                badges=badges
            )
        )
    return results

@router.get("/recommendations", response_model=List[VendorRecommendationOut])
def recommend_vendors(
    item_id: uuid.UUID = Query(..., description="ID of item to recommend vendors for"),
    db: Session = Depends(get_db)
):
    """
    Analytical (deterministic weighted score) vendor recommendations.
    Used by the supervisor CheckingSheet for quick reference.
    """
    return get_vendor_recommendations(db, item_id)

@router.get("/recommendations/rag", response_model=List[RAGVendorRecommendation])
def recommend_vendors_rag(
    item_id: uuid.UUID = Query(..., description="ID of item to recommend vendors for"),
    quantity: float = Query(1.0, gt=0, description="Requested quantity (influences bulk-order risk assessment)"),
    db: Session = Depends(get_db)
):
    """
    RAG + LLM-powered vendor recommendation engine.
    
    Pipeline:
      1. Deterministic eligibility filtering
      2. Structured quantitative evidence (recency-weighted review aggregation)
      3. RAG retrieval (cosine similarity on qualitative review embeddings)
      4. LLM contextual reasoning with anti-hallucination validation
      5. Fallback to analytical scoring if LLM unavailable
    
    Evidence confidence: HIGH | MEDIUM | LOW (deterministic classification)
    Recommendation status: RECOMMENDED | ACCEPTABLE | CAUTION
    Source: LLM_RAG (when LLM succeeded) | ANALYTICAL_FALLBACK (when LLM unavailable)
    """
    # Check cache first (avoids repeated LLM calls during demos)
    cached = recommendation_cache.get_cached(item_id, quantity)
    if cached is not None:
        logger.info(f"[VendorRAG API] Cache hit for item_id={item_id}, qty={quantity}")
        return cached

    # Get LLM provider (may return MockLocalLLMProvider if not configured)
    try:
        llm_provider = get_llm_provider()
    except Exception as e:
        logger.warning(f"[VendorRAG API] LLM provider init failed: {e}. Using None (analytical fallback).")
        llm_provider = None

    # Run the RAG recommendation pipeline
    try:
        recs = get_vendor_recommendations_rag(
            db=db,
            item_id=item_id,
            quantity=quantity,
            llm_provider=llm_provider
        )
    except Exception as e:
        logger.error(f"[VendorRAG API] RAG pipeline failed: {e}. Falling back to analytical.")
        # Ultimate fallback — never let a recommendation failure break the PR creation flow
        from app.intelligence.vendor_rag import _analytical_fallback, _get_eligible_vendors, prepare_quantitative_evidence
        eligible = _get_eligible_vendors(db, item_id)
        quant = {str(v.id): prepare_quantitative_evidence(db, v, item_id, quantity) for v in eligible}
        recs = _analytical_fallback(db, eligible, item_id, quant)

    if not recs:
        # If absolutely nothing could be computed, return empty list (don't 500)
        logger.warning(f"[VendorRAG API] No recommendations produced for item_id={item_id}")
        return []

    # Cache the result
    recommendation_cache.set_cached(item_id, quantity, recs)
    return recs

@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: uuid.UUID, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found.")
    badges = [b.badge_type for b in v.badges]
    return VendorOut(
        id=v.id,
        name=v.name,
        email=v.email,
        phone=v.phone,
        is_active=v.is_active,
        badges=badges
    )
