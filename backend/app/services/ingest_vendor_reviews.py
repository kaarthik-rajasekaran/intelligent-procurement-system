"""
Vendor Review Ingestion Service
================================
Reads the simulated Google Form export CSV (vendor_reviews.csv),
resolves vendor names and item names to database IDs,
creates VendorReview records, generates embeddings for qualitative text,
and stores VendorReviewEmbedding records.

This is fully idempotent — re-running will skip already-ingested rows.
"""
import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.entities import Vendor, Item, VendorReview, VendorReviewEmbedding

logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "vendor_reviews" / "vendor_reviews.csv"


def _get_vendor_map(db: Session) -> dict:
    """Return {vendor_name: vendor} map."""
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    return {v.name: v for v in vendors}


def _get_item_map(db: Session) -> dict:
    """Return {item_name: item} map."""
    items = db.query(Item).all()
    return {i.name: i for i in items}


def _cosine_similarity_placeholder(text: str) -> list:
    """Local embedding fallback using deterministic hash (no LLM)."""
    import hashlib
    import math
    seed_bytes = hashlib.sha256(text.encode("utf-8")).digest()
    # Build a 64-dim vector from hash bytes
    vec = []
    for i in range(0, min(64, len(seed_bytes)), 1):
        val = (seed_bytes[i % len(seed_bytes)] - 128) / 128.0
        vec.append(val)
    while len(vec) < 64:
        vec.append(0.0)
    # Normalize
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]


def ingest_vendor_reviews(db: Session, llm_provider=None) -> int:
    """
    Ingest vendor reviews from CSV into the database.
    
    Args:
        db: Database session
        llm_provider: Optional LLM provider for generating embeddings.
                      Falls back to deterministic hash embeddings if None.
    
    Returns:
        Number of new reviews ingested.
    """
    if not CSV_PATH.exists():
        logger.warning(f"[VendorReviewIngestion] CSV not found at {CSV_PATH}. Skipping ingestion.")
        return 0

    vendor_map = _get_vendor_map(db)
    item_map = _get_item_map(db)
    ingested = 0
    skipped = 0
    errors = 0

    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    logger.info(f"[VendorReviewIngestion] Processing {len(rows)} rows from CSV...")

    for idx, row in enumerate(rows):
        try:
            vendor_name = row.get("vendor_name", "").strip()
            item_name = row.get("item_name", "").strip()
            review_period = row.get("review_period", "").strip()
            reviewer_role = row.get("reviewer_role", "").strip()

            if not all([vendor_name, review_period, reviewer_role]):
                logger.warning(f"[VendorReviewIngestion] Row {idx+2}: Missing required fields. Skipping.")
                errors += 1
                continue

            vendor = vendor_map.get(vendor_name)
            if not vendor:
                logger.warning(f"[VendorReviewIngestion] Row {idx+2}: Vendor '{vendor_name}' not found in DB. Skipping.")
                errors += 1
                continue

            # Resolve item (nullable for general reviews)
            item = None
            if item_name and item_name.lower() not in ("general", "", "none"):
                item = item_map.get(item_name)
                if not item:
                    logger.warning(f"[VendorReviewIngestion] Row {idx+2}: Item '{item_name}' not found. Treating as general review.")

            # Idempotency check: skip if (vendor, item, period, role) already exists
            query = db.query(VendorReview).filter(
                VendorReview.vendor_id == vendor.id,
                VendorReview.review_period == review_period,
                VendorReview.reviewer_role == reviewer_role,
            )
            if item:
                query = query.filter(VendorReview.item_id == item.id)
            else:
                query = query.filter(VendorReview.item_id == None)

            if query.first():
                skipped += 1
                continue

            # Parse numeric fields
            def safe_float(val, default=5.0):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            def safe_bool(val):
                if isinstance(val, bool):
                    return val
                if str(val).upper() in ("TRUE", "YES", "1"):
                    return True
                if str(val).upper() in ("FALSE", "NO", "0"):
                    return False
                return None

            quality_rating = safe_float(row.get("quality_rating", ""), 5.0)
            delivery_rating = safe_float(row.get("delivery_rating", ""), 5.0)
            responsiveness_rating = safe_float(row.get("responsiveness_rating", ""), 5.0)
            price_rating = safe_float(row.get("price_rating", ""), 5.0)
            qualitative_feedback = row.get("qualitative_feedback", "").strip()
            specific_issues_raw = row.get("specific_issues", "").strip()
            specific_issues = specific_issues_raw if specific_issues_raw and specific_issues_raw.lower() not in ("none", "") else None
            order_quantity = safe_float(row.get("order_quantity", ""), None)
            fulfilled_on_time = safe_bool(row.get("fulfilled_on_time", ""))

            if not qualitative_feedback:
                logger.warning(f"[VendorReviewIngestion] Row {idx+2}: Empty qualitative_feedback. Skipping.")
                errors += 1
                continue

            # Create VendorReview record
            review = VendorReview(
                vendor_id=vendor.id,
                item_id=item.id if item else None,
                review_period=review_period,
                reviewer_role=reviewer_role,
                quality_rating=quality_rating,
                delivery_rating=delivery_rating,
                responsiveness_rating=responsiveness_rating,
                price_rating=price_rating,
                qualitative_feedback=qualitative_feedback,
                specific_issues=specific_issues,
                order_quantity=order_quantity if order_quantity is not None else None,
                fulfilled_on_time=fulfilled_on_time,
                created_at=datetime.utcnow()
            )
            db.add(review)
            db.flush()  # Get review.id without full commit

            # Build embedding text (rich context for RAG retrieval)
            item_context = item.name if item else "general vendor performance"
            item_category = item.category if item else "general"
            chunk_text = (
                f"Vendor: {vendor.name}. "
                f"Item: {item_context}. "
                f"Period: {review_period}. "
                f"Reviewer: {reviewer_role}. "
                f"Ratings — Quality: {quality_rating}/10, Delivery: {delivery_rating}/10, "
                f"Responsiveness: {responsiveness_rating}/10, Price: {price_rating}/10. "
                f"Review: {qualitative_feedback}"
            )
            if specific_issues:
                chunk_text += f" Issues noted: {specific_issues}"

            # Generate embedding
            embedding_vec = None
            if llm_provider:
                try:
                    embedding_vec = llm_provider.generate_embedding(chunk_text)
                except Exception as e:
                    logger.warning(f"[VendorReviewIngestion] Embedding generation failed for row {idx+2}: {e}. Using fallback.")

            if not embedding_vec:
                embedding_vec = _cosine_similarity_placeholder(chunk_text)

            embedding_record = VendorReviewEmbedding(
                review_id=review.id,
                vendor_id=vendor.id,
                item_id=item.id if item else None,
                category=item_category,
                embedding_json=json.dumps(embedding_vec),
                chunk_text=chunk_text,
                created_at=datetime.utcnow()
            )
            db.add(embedding_record)
            ingested += 1

        except Exception as e:
            logger.error(f"[VendorReviewIngestion] Error processing row {idx+2}: {e}")
            errors += 1
            continue

    db.commit()
    logger.info(
        f"[VendorReviewIngestion] Complete. Ingested: {ingested}, Skipped (already exists): {skipped}, Errors: {errors}"
    )
    return ingested
