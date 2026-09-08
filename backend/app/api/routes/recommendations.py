"""
Recommendation Snapshot API
============================
Implements the GENERATE ONCE → PERSIST → REUSE pattern.

Endpoints:
  POST /purchase-requests/{pr_id}/recommendation         — Employee saves snapshot (after PR creation)
  GET  /purchase-requests/{pr_id}/recommendation         — Supervisor reads snapshot (zero LLM)
  POST /purchase-requests/{pr_id}/recommendation/refresh — Supervisor explicitly refreshes (LLM call)

Cost model:
  - Save:    zero LLM (data comes from frontend state, already generated)
  - Get:     zero LLM (reads from DB)
  - Refresh: ONE LLM call (full RAG pipeline re-run)
"""

import json
import logging
from typing import Optional
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.entities import (
    PurchaseRequest, PurchaseRequestItem, PRRecommendationSnapshot, Item, UserRole
)
from app.schemas.domain import RecommendationSnapshotCreate, RecommendationSnapshotOut, RAGVendorRecommendation
from app.intelligence.vendor_rag import get_vendor_recommendations_rag
from app.intelligence import recommendation_cache
from app.ai.provider import get_llm_provider
from app.api.deps import get_current_user, require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/purchase-requests", tags=["Recommendation Snapshots"])

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _snapshot_to_out(snap: PRRecommendationSnapshot) -> RecommendationSnapshotOut:
    """Convert ORM model to Pydantic response schema."""
    all_candidates: list[RAGVendorRecommendation] = []
    if snap.all_candidates_json:
        try:
            raw = json.loads(snap.all_candidates_json)
            all_candidates = [RAGVendorRecommendation(**c) for c in raw]
        except Exception as e:
            logger.warning(f"[Snapshot] Failed to deserialize all_candidates_json: {e}")

    key_strengths: list[str] = []
    if snap.key_strengths_json:
        try:
            key_strengths = json.loads(snap.key_strengths_json)
        except Exception:
            pass

    potential_risks: list[str] = []
    if snap.potential_risks_json:
        try:
            potential_risks = json.loads(snap.potential_risks_json)
        except Exception:
            pass

    return RecommendationSnapshotOut(
        id=snap.id,
        purchase_request_id=snap.purchase_request_id,
        version=snap.version,
        item_id=snap.item_id,
        item_name=snap.item_name,
        category=snap.category,
        quantity=float(snap.quantity) if snap.quantity is not None else None,
        recommended_vendor_id=snap.recommended_vendor_id,
        recommended_vendor_name=snap.recommended_vendor_name,
        all_candidates=all_candidates,
        evidence_confidence=snap.evidence_confidence,
        reasoning_summary=snap.reasoning_summary,
        key_strengths=key_strengths,
        potential_risks=potential_risks,
        avg_quality_rating=float(snap.avg_quality_rating) if snap.avg_quality_rating is not None else None,
        avg_delivery_rating=float(snap.avg_delivery_rating) if snap.avg_delivery_rating is not None else None,
        avg_price_rating=float(snap.avg_price_rating) if snap.avg_price_rating is not None else None,
        trend_direction=snap.trend_direction,
        review_count=snap.review_count or 0,
        final_recommendation_score=float(snap.final_recommendation_score) if snap.final_recommendation_score is not None else (float(snap.analytical_score) if snap.analytical_score is not None else 0.0),
        analytical_score=float(snap.analytical_score) if snap.analytical_score is not None else 0.0,
        source=snap.source or "ANALYTICAL_FALLBACK",
        is_stale=snap.is_stale,
        triggered_by=snap.triggered_by,
        created_at=snap.created_at,
    )


def _check_stale(snap: PRRecommendationSnapshot, pr: PurchaseRequest, db: Session) -> bool:
    """
    Deterministically decide if a snapshot is stale:
    - Snapshot is older than 24 hours, OR
    - Current PR item_id differs from snapshot item_id, OR
    - Current PR quantity differs from snapshot quantity by >5%
    """
    if not snap:
        return False

    # Time-based stale: older than 24h
    age = datetime.utcnow() - snap.created_at
    if age > timedelta(hours=24):
        return True

    # Item changed
    pr_item = pr.items[0] if pr.items else None
    if pr_item:
        current_item_id = str(pr_item.item_id)
        if snap.item_id and current_item_id != snap.item_id:
            return True

        if snap.quantity is not None:
            current_qty = float(pr_item.quantity)
            snap_qty = float(snap.quantity)
            if snap_qty > 0:
                pct_diff = abs(current_qty - snap_qty) / snap_qty
                if pct_diff > 0.05:  # >5% change
                    return True

    return False


def _get_pr_or_404(pr_id: uuid.UUID, db: Session) -> PurchaseRequest:
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found.")
    return pr


def _get_latest_snapshot(pr_id: uuid.UUID, db: Session) -> Optional[PRRecommendationSnapshot]:
    return (
        db.query(PRRecommendationSnapshot)
        .filter(PRRecommendationSnapshot.purchase_request_id == pr_id)
        .order_by(PRRecommendationSnapshot.version.desc())
        .first()
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /purchase-requests/{pr_id}/recommendation
# Employee saves the RAG result immediately after PR creation (zero LLM here)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{pr_id}/recommendation", response_model=RecommendationSnapshotOut)
def save_recommendation_snapshot(
    pr_id: uuid.UUID,
    payload: RecommendationSnapshotCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Persist the RAG vendor recommendation snapshot generated during PR creation.

    This endpoint receives the already-computed recommendation data from the frontend
    (which was produced when the employee clicked "Run Vendor Recommendation").
    No LLM calls are made here — this is purely a database write.

    Idempotent: if a snapshot already exists for this PR at version 1, it will be
    replaced rather than duplicated.
    """
    pr = _get_pr_or_404(pr_id, db)

    # Serialize complex fields
    all_candidates_json = json.dumps([c.model_dump(mode="json") for c in payload.all_candidates])
    key_strengths_json = json.dumps(payload.key_strengths)
    potential_risks_json = json.dumps(payload.potential_risks)

    # Check for existing version 1 snapshot (idempotent upsert)
    existing = (
        db.query(PRRecommendationSnapshot)
        .filter(
            PRRecommendationSnapshot.purchase_request_id == pr_id,
            PRRecommendationSnapshot.version == 1,
        )
        .first()
    )

    if existing:
        # Update in place (employee re-ran recommendation before submitting)
        existing.item_id = payload.item_id
        existing.item_name = payload.item_name
        existing.category = payload.category
        existing.quantity = payload.quantity
        existing.recommended_vendor_id = payload.recommended_vendor_id
        existing.recommended_vendor_name = payload.recommended_vendor_name
        existing.all_candidates_json = all_candidates_json
        existing.evidence_confidence = payload.evidence_confidence
        existing.reasoning_summary = payload.reasoning_summary
        existing.key_strengths_json = key_strengths_json
        existing.potential_risks_json = potential_risks_json
        existing.avg_quality_rating = payload.avg_quality_rating
        existing.avg_delivery_rating = payload.avg_delivery_rating
        existing.avg_price_rating = payload.avg_price_rating
        existing.trend_direction = payload.trend_direction
        existing.review_count = payload.review_count
        existing.final_recommendation_score = payload.final_recommendation_score
        existing.analytical_score = payload.analytical_score
        existing.source = payload.source
        existing.is_stale = False
        existing.triggered_by = "EMPLOYEE"
        existing.created_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        logger.info(f"[Snapshot] Updated v1 snapshot for PR {pr_id}")
        return _snapshot_to_out(existing)
    else:
        snap = PRRecommendationSnapshot(
            purchase_request_id=pr_id,
            version=1,
            item_id=payload.item_id,
            item_name=payload.item_name,
            category=payload.category,
            quantity=payload.quantity,
            recommended_vendor_id=payload.recommended_vendor_id,
            recommended_vendor_name=payload.recommended_vendor_name,
            all_candidates_json=all_candidates_json,
            evidence_confidence=payload.evidence_confidence,
            reasoning_summary=payload.reasoning_summary,
            key_strengths_json=key_strengths_json,
            potential_risks_json=potential_risks_json,
            avg_quality_rating=payload.avg_quality_rating,
            avg_delivery_rating=payload.avg_delivery_rating,
            avg_price_rating=payload.avg_price_rating,
            trend_direction=payload.trend_direction,
            review_count=payload.review_count,
            final_recommendation_score=payload.final_recommendation_score,
            analytical_score=payload.analytical_score,
            source=payload.source,
            is_stale=False,
            triggered_by="EMPLOYEE",
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        logger.info(f"[Snapshot] Created v1 snapshot for PR {pr_id}")
        return _snapshot_to_out(snap)


# ─────────────────────────────────────────────────────────────────────────────
# GET /purchase-requests/{pr_id}/recommendation
# Supervisor reads the latest snapshot — ZERO LLM CALLS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{pr_id}/recommendation", response_model=RecommendationSnapshotOut)
def get_recommendation_snapshot(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Retrieve the latest recommendation snapshot for a Purchase Request.

    Zero LLM calls. Pure DB read.
    Stale detection runs deterministically on every read.
    """
    pr = _get_pr_or_404(pr_id, db)
    snap = _get_latest_snapshot(pr_id, db)

    if not snap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI recommendation snapshot found for this purchase request. The employee did not run the vendor recommendation engine before submitting."
        )

    # Run stale check and persist if it changed
    is_now_stale = _check_stale(snap, pr, db)
    if is_now_stale and not snap.is_stale:
        snap.is_stale = True
        db.commit()
        db.refresh(snap)
        logger.info(f"[Snapshot] Marked snapshot v{snap.version} for PR {pr_id} as stale")

    return _snapshot_to_out(snap)


# ─────────────────────────────────────────────────────────────────────────────
# POST /purchase-requests/{pr_id}/recommendation/refresh
# Supervisor explicitly reruns LLM+RAG — THE ONLY SUPERVISOR-SIDE LLM CALL
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{pr_id}/recommendation/refresh", response_model=RecommendationSnapshotOut)
def refresh_recommendation_snapshot(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value])),
):
    """
    Re-run the full RAG+LLM recommendation pipeline and persist as a new version.

    This is the ONLY endpoint that triggers an LLM call on the supervisor side.
    All other supervisor-side actions (view snapshot, compare vendors) are zero-LLM.

    The new snapshot is saved as version = previous_max + 1.
    Historical versions are never overwritten.
    """
    pr = _get_pr_or_404(pr_id, db)

    # Get item context from PR
    pr_item = pr.items[0] if pr.items else None
    if not pr_item or not pr_item.item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refresh recommendation: purchase request has no associated item."
        )

    item = pr_item.item
    quantity = float(pr_item.quantity)

    # Bypass cache for a genuine fresh result
    recommendation_cache.invalidate(item.id)

    # Get LLM provider
    try:
        llm_provider = get_llm_provider()
    except Exception as e:
        logger.warning(f"[Snapshot Refresh] LLM provider init failed: {e}. Using None (analytical fallback).")
        llm_provider = None

    # Run the RAG pipeline
    try:
        recs = get_vendor_recommendations_rag(
            db=db,
            item_id=item.id,
            quantity=quantity,
            llm_provider=llm_provider,
        )
    except Exception as e:
        logger.error(f"[Snapshot Refresh] RAG pipeline failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Recommendation refresh failed: {str(e)}"
        )

    if not recs:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No vendor recommendations could be generated for this item."
        )

    # Cache fresh result
    recommendation_cache.set_cached(item.id, quantity, recs)

    # Top recommendation = rank 1
    top = recs[0]

    # Compute new version number
    existing_max = _get_latest_snapshot(pr_id, db)
    new_version = (existing_max.version + 1) if existing_max else 1

    snap = PRRecommendationSnapshot(
        purchase_request_id=pr_id,
        version=new_version,
        item_id=str(item.id),
        item_name=item.name,
        category=item.category,
        quantity=quantity,
        recommended_vendor_id=str(top.vendor_id),
        recommended_vendor_name=top.vendor_name,
        all_candidates_json=json.dumps([r.model_dump(mode="json") for r in recs]),
        evidence_confidence=top.evidence_confidence,
        reasoning_summary=top.reasoning_summary,
        key_strengths_json=json.dumps(top.key_strengths),
        potential_risks_json=json.dumps(top.potential_risks),
        avg_quality_rating=top.avg_quality_rating,
        avg_delivery_rating=top.avg_delivery_rating,
        avg_price_rating=top.avg_price_rating,
        trend_direction=top.trend_direction,
        review_count=top.review_count,
        final_recommendation_score=top.final_recommendation_score,
        analytical_score=top.analytical_score,
        source=top.source,
        is_stale=False,
        triggered_by="SUPERVISOR_REFRESH",
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    logger.info(f"[Snapshot] Supervisor refreshed recommendation for PR {pr_id} — new version v{new_version} (source={top.source})")
    return _snapshot_to_out(snap)
