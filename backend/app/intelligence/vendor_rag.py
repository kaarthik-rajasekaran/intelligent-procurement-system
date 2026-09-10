"""
RAG + LLM Vendor Recommendation Engine
=======================================
Implements the new vendor recommendation pipeline:

  [1] Deterministic eligibility filtering
  [2] Structured quantitative evidence preparation (with recency weighting)
  [3] RAG retrieval — 3-level cosine similarity search on review embeddings
  [4] LLM-based contextual comparison with structured JSON output
  [5] Deterministic validation (anti-hallucination — rejects invented vendors)
  [6] Fallback to analytical scoring when LLM is unavailable

IMPORTANT: This does NOT replace evaluate_quotations(). The quotation
evaluation system is completely separate and must NOT be modified.
"""
import json
import logging
import math
import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict, Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    Vendor, VendorPerformance, VendorItemPerformance, VendorBadge,
    VendorReview, VendorReviewEmbedding, Item, BadgeType
)
from app.schemas.domain import RAGVendorRecommendation
from app.intelligence.analytical import compute_vendor_badges, get_vendor_recommendations

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Evidence confidence classification rules (deterministic)
# ---------------------------------------------------------------------------
def _classify_evidence_confidence(
    review_count: int,
    has_item_specific_reviews: bool,
    most_recent_period: Optional[str]
) -> str:
    """
    Deterministic evidence confidence classification.
    Returns HIGH | MEDIUM | LOW — never an invented percentage.
    
    Rules:
      HIGH:   >= 3 reviews with >= 1 item-specific review and recent (within 2 quarters)
      MEDIUM: >= 2 reviews OR (1+ item-specific review but older data)
      LOW:    0-1 reviews OR all reviews are more than 4 quarters old
    """
    if review_count == 0:
        return "LOW"

    # Parse period recency (e.g., "Q2-2026")
    is_recent = False
    if most_recent_period:
        try:
            parts = most_recent_period.split("-")
            q = int(parts[0][1])
            yr = int(parts[1])
            now = datetime.utcnow()
            # "Recent" = within the last 2 calendar quarters (~6 months)
            period_approx = datetime(yr, q * 3, 1)
            is_recent = (now - period_approx) < timedelta(days=180)
        except Exception:
            is_recent = False

    if review_count >= 3 and has_item_specific_reviews and is_recent:
        return "HIGH"
    elif review_count >= 2 or (has_item_specific_reviews and review_count >= 1):
        return "MEDIUM"
    else:
        return "LOW"


def _compute_final_recommendation_score(
    analytical_score: float,
    quant_evidence: Dict[str, Any],
    llm_status: str,
    confidence: str,
) -> float:
    """
    Canonical final recommendation score — the single source of truth for vendor ranking.

    Formula (transparent, always deterministic from component parts):
      Component A (40%): Historical Performance Score from VendorPerformance weighted formula
      Component B (40%): Review Evidence Score = avg(quality, delivery, price) from VendorReview × 10
      Component C (20%): Evidence Confidence bonus (HIGH=100, MEDIUM=65, LOW=30)

    LLM modifier (applied after component sum):
      CAUTION      → × 0.85  (15% reduction — LLM identified significant contextual risk)
      ACCEPTABLE   → × 1.00  (no change)
      RECOMMENDED  → × 1.05  (5% boost — LLM confirmed contextual strength, capped at 100)

    This ensures rank is ALWAYS explainable mathematically. The LLM never directly sets
    rank — it informs it through recommendation_status only.
    """
    # Component A: Historical Performance (weighted formula from VendorPerformance table)
    component_a = analytical_score * 0.40

    # Component B: Review Evidence Score (from quarterly VendorReview data)
    review_ratings = []
    if quant_evidence.get("avg_quality") is not None:
        review_ratings.append(float(quant_evidence["avg_quality"]) * 10.0)
    if quant_evidence.get("avg_delivery") is not None:
        review_ratings.append(float(quant_evidence["avg_delivery"]) * 10.0)
    if quant_evidence.get("avg_price") is not None:
        review_ratings.append(float(quant_evidence["avg_price"]) * 10.0)

    if review_ratings:
        review_evidence_score = sum(review_ratings) / len(review_ratings)
    else:
        # No review data — fall back to analytical score as proxy
        review_evidence_score = analytical_score
    component_b = review_evidence_score * 0.40

    # Component C: Evidence Confidence bonus
    confidence_score = {"HIGH": 100.0, "MEDIUM": 65.0, "LOW": 30.0}.get(confidence, 50.0)
    component_c = confidence_score * 0.20

    raw_score = component_a + component_b + component_c

    # LLM modifier — recommendation_status adjusts the score without fully overriding it
    if llm_status == "CAUTION":
        raw_score = raw_score * 0.85
    elif llm_status == "RECOMMENDED":
        raw_score = min(100.0, raw_score * 1.05)
    # ACCEPTABLE: no change (× 1.00)

    return round(min(100.0, max(0.0, raw_score)), 1)


# ---------------------------------------------------------------------------
# Step 1: Deterministic vendor eligibility filtering
# ---------------------------------------------------------------------------
def _get_eligible_vendors(db: Session, item_id: uuid.UUID) -> List[Vendor]:
    """
    Returns active vendors that are mapped to the given item via vendor_item_mapping.
    If no specific mapping exists for this item, returns all active vendors.
    """
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    eligible = []
    for vendor in vendors:
        if vendor.eligible_items:
            if any(str(item.id) == str(item_id) for item in vendor.eligible_items):
                eligible.append(vendor)
        # If a vendor has no item mappings at all, include as eligible
        elif not vendor.eligible_items:
            eligible.append(vendor)
    return eligible if eligible else vendors


# ---------------------------------------------------------------------------
# Step 2: Quantitative evidence preparation
# ---------------------------------------------------------------------------
QUARTER_WEIGHTS = {
    "Q2-2026": 1.00, "Q1-2026": 0.85,
    "Q4-2025": 0.70, "Q3-2025": 0.55,
    "Q2-2025": 0.40, "Q1-2025": 0.30,
    "Q4-2024": 0.20, "Q3-2024": 0.15,
}

def _get_period_weight(period: str) -> float:
    """Get recency weight for a review period. Unknown periods get 0.1."""
    return QUARTER_WEIGHTS.get(period, 0.10)


def prepare_quantitative_evidence(
    db: Session,
    vendor: Vendor,
    item_id: uuid.UUID,
    quantity: float
) -> Dict[str, Any]:
    """
    Aggregate structured review scores with recency weighting.
    Also checks quantity-context signals (bulk order issues).
    """
    # Fetch all reviews for this vendor
    all_reviews = db.query(VendorReview).filter(
        VendorReview.vendor_id == vendor.id
    ).all()

    # Split: item-specific vs general
    item_reviews = [r for r in all_reviews if str(r.item_id) == str(item_id)]
    general_reviews = [r for r in all_reviews if r.item_id is None]

    # Use item reviews if available, else fall back to general
    primary_reviews = item_reviews if item_reviews else general_reviews

    if not primary_reviews:
        # Fall back to VendorPerformance table (old system) for quantitative data
        perf = (
            db.query(VendorPerformance)
            .filter(VendorPerformance.vendor_id == vendor.id)
            .order_by(VendorPerformance.measurement_period.desc())
            .first()
        )
        if perf:
            return {
                "review_count": 0,
                "has_item_specific": False,
                "most_recent_period": None,
                "avg_quality": float(perf.quality_score) / 10.0,
                "avg_delivery": float(perf.delivery_reliability_score) / 10.0,
                "avg_responsiveness": float(perf.responsiveness_score) / 10.0,
                "avg_price": float(perf.price_competitiveness_score) / 10.0,
                "trend_direction": "STABLE",
                "on_time_rate": None,
                "bulk_order_issues": [],
                "quality_ratings_over_time": [],
                "source": "VENDOR_PERFORMANCE_TABLE",
            }
        return {
            "review_count": 0,
            "has_item_specific": False,
            "most_recent_period": None,
            "avg_quality": None, "avg_delivery": None,
            "avg_responsiveness": None, "avg_price": None,
            "trend_direction": "UNKNOWN", "on_time_rate": None,
            "bulk_order_issues": [],
            "quality_ratings_over_time": [],
            "source": "NO_DATA",
        }

    # Recency-weighted averages across primary reviews
    total_weight = 0.0
    w_quality = w_delivery = w_responsiveness = w_price = 0.0
    on_time_count = 0
    total_with_time = 0
    quality_over_time = []  # for trend detection
    bulk_issues = []

    for r in sorted(primary_reviews, key=lambda x: x.review_period):
        weight = _get_period_weight(r.review_period)
        total_weight += weight
        w_quality += float(r.quality_rating) * weight
        w_delivery += float(r.delivery_rating) * weight
        w_responsiveness += float(r.responsiveness_rating) * weight
        w_price += float(r.price_rating) * weight

        if r.fulfilled_on_time is not None:
            total_with_time += 1
            if r.fulfilled_on_time:
                on_time_count += 1

        quality_over_time.append((r.review_period, float(r.quality_rating)))

        # Bulk order issue detection: flag if large order (> 15 units) had delivery/quality problems
        order_qty = float(r.order_quantity) if r.order_quantity else 0
        if order_qty >= 15 and (float(r.delivery_rating) < 7.0 or not r.fulfilled_on_time):
            bulk_issues.append({
                "period": r.review_period,
                "order_quantity": order_qty,
                "delivery_rating": float(r.delivery_rating),
                "fulfilled_on_time": r.fulfilled_on_time,
                "issue_summary": (r.specific_issues or r.qualitative_feedback)[:200]
            })

    avg_q = w_quality / total_weight if total_weight > 0 else None
    avg_d = w_delivery / total_weight if total_weight > 0 else None
    avg_r = w_responsiveness / total_weight if total_weight > 0 else None
    avg_p = w_price / total_weight if total_weight > 0 else None
    on_time_rate = (on_time_count / total_with_time * 100) if total_with_time > 0 else None

    # Trend detection: compare last 2 vs earlier ratings
    trend = "STABLE"
    if len(quality_over_time) >= 3:
        sorted_qt = sorted(quality_over_time, key=lambda x: x[0])
        recent_avg = sum(v for _, v in sorted_qt[-2:]) / 2
        older_avg = sum(v for _, v in sorted_qt[:-2]) / max(1, len(sorted_qt) - 2)
        if recent_avg - older_avg > 0.5:
            trend = "IMPROVING"
        elif older_avg - recent_avg > 0.5:
            trend = "DECLINING"

    most_recent = max(r.review_period for r in primary_reviews) if primary_reviews else None

    # Flag bulk order risk in current request context
    bulk_risk_for_this_order = []
    if quantity >= 15:
        bulk_risk_for_this_order = [b for b in bulk_issues if b["order_quantity"] >= quantity * 0.7]

    return {
        "review_count": len(primary_reviews),
        "has_item_specific": len(item_reviews) > 0,
        "most_recent_period": most_recent,
        "avg_quality": round(avg_q, 2) if avg_q else None,
        "avg_delivery": round(avg_d, 2) if avg_d else None,
        "avg_responsiveness": round(avg_r, 2) if avg_r else None,
        "avg_price": round(avg_p, 2) if avg_p else None,
        "trend_direction": trend,
        "on_time_rate": round(on_time_rate, 1) if on_time_rate is not None else None,
        "bulk_order_issues": bulk_risk_for_this_order,
        "quality_ratings_over_time": quality_over_time,
        "source": "VENDOR_REVIEW_TABLE",
    }


# ---------------------------------------------------------------------------
# Step 3: RAG retrieval — cosine similarity on review embeddings
# ---------------------------------------------------------------------------
def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (norm_a * norm_b)


def retrieve_qualitative_evidence(
    db: Session,
    vendor: Vendor,
    item_id: uuid.UUID,
    category: str,
    query_embedding: List[float],
    top_k: int = 4
) -> List[str]:
    """
    3-level RAG retrieval hierarchy for a specific vendor:
      Level 1: item-specific embeddings for this vendor
      Level 2: category-level embeddings for this vendor
      Level 3: general vendor embeddings
    
    Returns top_k most relevant review text snippets.
    """
    # Level 1: exact item match for this vendor
    item_embs = db.query(VendorReviewEmbedding).filter(
        VendorReviewEmbedding.vendor_id == vendor.id,
        VendorReviewEmbedding.item_id == item_id
    ).all()

    # Level 2: category match for this vendor  
    cat_embs = db.query(VendorReviewEmbedding).filter(
        VendorReviewEmbedding.vendor_id == vendor.id,
        VendorReviewEmbedding.category == category,
        VendorReviewEmbedding.item_id == None
    ).all()

    # Level 3: general vendor reviews
    gen_embs = db.query(VendorReviewEmbedding).filter(
        VendorReviewEmbedding.vendor_id == vendor.id,
        VendorReviewEmbedding.item_id == None,
        VendorReviewEmbedding.category.notin_([category])
    ).all()

    # Prioritize: item > category > general, with similarity scoring within each level
    scored = []
    for emb in item_embs:
        if emb.embedding_json:
            try:
                vec = json.loads(emb.embedding_json)
                sim = _cosine_similarity(query_embedding, vec)
                # Boost item-specific embeddings by 0.2 for priority
                scored.append((sim + 0.20, emb.chunk_text))
            except Exception:
                scored.append((0.50, emb.chunk_text))  # include without boosting

    for emb in cat_embs:
        if emb.embedding_json:
            try:
                vec = json.loads(emb.embedding_json)
                sim = _cosine_similarity(query_embedding, vec)
                scored.append((sim + 0.10, emb.chunk_text))
            except Exception:
                scored.append((0.30, emb.chunk_text))

    for emb in gen_embs:
        if emb.embedding_json:
            try:
                vec = json.loads(emb.embedding_json)
                sim = _cosine_similarity(query_embedding, vec)
                scored.append((sim, emb.chunk_text))
            except Exception:
                scored.append((0.10, emb.chunk_text))

    # Sort by score descending, take top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    return [text for _, text in scored[:top_k]]


# ---------------------------------------------------------------------------
# Step 4: LLM reasoning with anti-hallucination validation
# ---------------------------------------------------------------------------
_LLM_SYSTEM_PROMPT = """You are a procurement analyst generating structured vendor recommendations.

CRITICAL RULES — FOLLOW EXACTLY:
1. Base your recommendation ONLY on the evidence provided below.
2. Do NOT invent any vendor that is not in the CANDIDATE VENDORS list.
3. Do NOT fabricate scores or evidence not present in the data.
4. Do NOT output confidence percentages. Use only: HIGH, MEDIUM, or LOW.
5. Return valid JSON only — no markdown, no prose outside the JSON.
6. Include at most 3 vendors in your response.
7. recommendation_status must be one of: RECOMMENDED, ACCEPTABLE, CAUTION.
"""

def _build_llm_prompt(
    item_name: str,
    item_category: str,
    quantity: float,
    candidate_vendors: List[Dict],
) -> str:
    """Build the structured grounded prompt for the LLM."""
    candidate_block = ""
    for cv in candidate_vendors:
        q_ev = cv["quantitative"]
        rag_evidence = cv["qualitative_evidence"]

        candidate_block += f"\n--- VENDOR: {cv['name']} (ID: {cv['vendor_id']}) ---\n"
        candidate_block += f"Analytical Score: {cv['analytical_score']}/100\n"
        candidate_block += f"Badges: {', '.join(cv['badges']) if cv['badges'] else 'None'}\n"

        if q_ev.get("review_count", 0) > 0:
            candidate_block += f"Review Count: {q_ev['review_count']} reviews\n"
            candidate_block += f"Most Recent Period: {q_ev.get('most_recent_period', 'Unknown')}\n"
            candidate_block += f"Item-Specific Reviews: {'Yes' if q_ev.get('has_item_specific') else 'No (general reviews only)'}\n"
            if q_ev.get("avg_quality"):
                candidate_block += f"Avg Quality Rating: {q_ev['avg_quality']}/10\n"
            if q_ev.get("avg_delivery"):
                candidate_block += f"Avg Delivery Rating: {q_ev['avg_delivery']}/10\n"
            if q_ev.get("avg_price"):
                candidate_block += f"Avg Price Rating: {q_ev['avg_price']}/10\n"
            if q_ev.get("on_time_rate") is not None:
                candidate_block += f"On-Time Delivery Rate: {q_ev['on_time_rate']}%\n"
            candidate_block += f"Trend: {q_ev.get('trend_direction', 'UNKNOWN')}\n"
            if q_ev.get("bulk_order_issues"):
                candidate_block += "⚠ BULK ORDER ISSUES DETECTED:\n"
                for issue in q_ev["bulk_order_issues"]:
                    candidate_block += f"  - Order qty {issue['order_quantity']}: {issue['issue_summary'][:150]}\n"
        else:
            candidate_block += "Quantitative Evidence: No structured reviews available (using performance database only)\n"

        if rag_evidence:
            candidate_block += "Qualitative Evidence (relevant review excerpts):\n"
            for i, excerpt in enumerate(rag_evidence[:3], 1):
                # Trim to avoid prompt bloat
                trimmed = excerpt[:400].replace("\n", " ")
                candidate_block += f"  [{i}] {trimmed}\n"
        else:
            candidate_block += "Qualitative Evidence: No review text available\n"

    prompt = f"""
PROCUREMENT ITEM: {item_name}
CATEGORY: {item_category}
REQUESTED QUANTITY: {quantity} units

CANDIDATE VENDORS (only rank vendors from this list):
{candidate_block}

TASK: Analyze the evidence above and produce a ranked recommendation.
Output a JSON object in EXACTLY this format:
{{
  "recommendations": [
    {{
      "vendor_id": "<exact vendor ID from the list above>",
      "vendor_name": "<exact vendor name from the list above>",
      "rank": 1,
      "recommendation_status": "RECOMMENDED",
      "reasoning_summary": "<2-3 sentence contextual reasoning based on evidence>",
      "key_strengths": ["<strength 1>", "<strength 2>"],
      "potential_risks": ["<risk 1>"] 
    }},
    {{
      "vendor_id": "...",
      "vendor_name": "...",
      "rank": 2,
      "recommendation_status": "ACCEPTABLE",
      "reasoning_summary": "...",
      "key_strengths": [...],
      "potential_risks": [...]
    }}
  ]
}}

Rules:
- Include 2-3 vendors maximum, ordered by rank 1, 2, 3.
- If a vendor has conflicting evidence, set recommendation_status to CAUTION and explain in reasoning_summary.
- If bulk order issues exist and the requested quantity is large, factor this into potential_risks.
- key_strengths and potential_risks must each be a list of strings (can be empty list []).
- Return ONLY valid JSON. No other text.
"""
    return prompt


def _validate_llm_output(
    llm_json: dict,
    eligible_vendor_ids: List[str]
) -> List[dict]:
    """
    Anti-hallucination validation.
    Removes any vendor from LLM output that wasn't in the eligible candidate list.
    Ensures output structure is valid.
    """
    recommendations = llm_json.get("recommendations", [])
    valid = []
    for rec in recommendations:
        vid = str(rec.get("vendor_id", "")).strip()
        if vid in eligible_vendor_ids:
            # Ensure required fields exist
            rec.setdefault("recommendation_status", "ACCEPTABLE")
            rec.setdefault("reasoning_summary", "")
            rec.setdefault("key_strengths", [])
            rec.setdefault("potential_risks", [])
            valid.append(rec)
        else:
            logger.warning(f"[VendorRAG] LLM output contained unknown vendor_id '{vid}' — discarded (anti-hallucination).")
    return valid

# ---------------------------------------------------------------------------
# Step 5: Analytical fallback (when LLM is unavailable or fails)
# ---------------------------------------------------------------------------
def _analytical_fallback(
    db: Session,
    eligible_vendors: List[Vendor],
    item_id: uuid.UUID,
    quant_evidence: Dict[str, Any],
    quantity: float = 1.0
) -> List[RAGVendorRecommendation]:
    """
    Deterministic analytical recommendation fallback with rich item-grounded contextual reasoning.
    Uses multi-criteria weighted scoring + review evidence + real qualitative review snippets.
    Rank is always assigned by sorting final_recommendation_score DESC.
    """
    try:
        item = db.query(Item).filter(Item.id == item_id).first()
        item_name = item.name if item else "Requested Item"
        category = item.category if item else "General"

        analytical_recs = get_vendor_recommendations(db, item_id)
        intermediates = []

        for arec in analytical_recs[:5]:
            vendor_id_str = str(arec.vendor_id)
            q_ev = quant_evidence.get(vendor_id_str, {})
            vendor_obj = next((v for v in eligible_vendors if str(v.id) == vendor_id_str), None)

            confidence = _classify_evidence_confidence(
                q_ev.get("review_count", 0),
                q_ev.get("has_item_specific", False),
                q_ev.get("most_recent_period")
            )

            # Check if vendor has bulk order issues
            has_bulk_issue = bool(q_ev.get("bulk_order_issues"))

            # Determine baseline status
            if arec.rank == 1 and not has_bulk_issue:
                llm_status = "RECOMMENDED"
            elif has_bulk_issue and quantity >= 15:
                llm_status = "CAUTION"
            else:
                llm_status = "ACCEPTABLE"

            final_score = _compute_final_recommendation_score(
                analytical_score=arec.overall_score,
                quant_evidence=q_ev,
                llm_status=llm_status,
                confidence=confidence,
            )

            # Fetch qualitative review snippets from database
            review_snippets = []
            if vendor_obj:
                try:
                    query_emb = [0.1] * 64
                    review_snippets = retrieve_qualitative_evidence(
                        db=db,
                        vendor=vendor_obj,
                        item_id=item_id,
                        category=category,
                        query_embedding=query_emb,
                        top_k=2
                    )
                except Exception:
                    pass

            # Generate dynamic, rich contextual analysis
            strengths = []
            risks = []

            quality_val = q_ev.get("avg_quality") or (arec.factor_breakdown.quality / 10.0)
            delivery_val = q_ev.get("avg_delivery") or (arec.factor_breakdown.delivery_reliability / 10.0)
            on_time_rate = q_ev.get("on_time_rate") or arec.factor_breakdown.delivery_reliability
            trend = q_ev.get("trend_direction", "STABLE")

            if quality_val >= 8.5:
                strengths.append(f"Demonstrated {quality_val*10:.1f}% quality compliance rating for {item_name}")
            if on_time_rate >= 90:
                strengths.append(f"High on-time fulfillment reliability ({on_time_rate:.1f}% on-time rate)")
            if trend == "IMPROVING":
                strengths.append("Quarterly review evaluations reflect an improving fulfillment trajectory")
            if arec.badges:
                strengths.append(f"Recognized enterprise partner with badges: {', '.join(arec.badges)}")
            if not strengths:
                strengths.append(f"Established supplier for {category} category procurement")

            if has_bulk_issue and quantity >= 15:
                risks.append(f"Past reviews indicate delivery bottlenecks on large volume orders ({quantity:g}+ units)")
            elif delivery_val < 8.0:
                risks.append("Occasional fulfillment lead time variance observed in historical quarters")
            elif arec.factor_breakdown.price_competitiveness < 75:
                risks.append(f"Carries a slight unit price premium ({arec.factor_breakdown.price_competitiveness:.0f}% cost score)")
            else:
                risks.append("Standard SLA lead time tracking recommended")

            if llm_status == "RECOMMENDED":
                summary = (
                    f"{arec.vendor_name} is the top analytical choice for {item_name} (Composite: {final_score:.1f}/100). "
                    f"Maintains {quality_val*10:.1f}% quality rating and {on_time_rate:.1f}% delivery reliability."
                )
            elif llm_status == "CAUTION":
                summary = (
                    f"{arec.vendor_name} demonstrates acceptable overall capability ({final_score:.1f}/100), but cautions apply for {quantity:g} units "
                    f"due to past recorded bulk fulfillment bottlenecks."
                )
            else:
                summary = (
                    f"{arec.vendor_name} offers a competitive alternative option with a {final_score:.1f}/100 performance score in {category}."
                )

            intermediates.append({
                "arec": arec,
                "q_ev": q_ev,
                "confidence": confidence,
                "llm_status": llm_status,
                "final_score": final_score,
                "reasoning_summary": summary,
                "key_strengths": strengths[:3],
                "potential_risks": risks[:2],
                "review_insights": [s[:300] for s in review_snippets[:2]]
            })

        # Sort by final_recommendation_score DESC, tie-break by analytical_score DESC
        intermediates.sort(key=lambda x: (x["final_score"], x["arec"].overall_score), reverse=True)

        results = []
        for rank, item in enumerate(intermediates[:3], start=1):
            arec = item["arec"]
            q_ev = item["q_ev"]
            status_assigned = "RECOMMENDED" if rank == 1 and item["llm_status"] != "CAUTION" else item["llm_status"]

            results.append(RAGVendorRecommendation(
                rank=rank,
                vendor_id=arec.vendor_id,
                vendor_name=arec.vendor_name,
                recommendation_status=status_assigned,
                reasoning_summary=item["reasoning_summary"],
                key_strengths=item["key_strengths"],
                potential_risks=item["potential_risks"],
                evidence_confidence=item["confidence"],
                avg_quality_rating=q_ev.get("avg_quality"),
                avg_delivery_rating=q_ev.get("avg_delivery"),
                avg_responsiveness_rating=q_ev.get("avg_responsiveness"),
                avg_price_rating=q_ev.get("avg_price"),
                trend_direction=q_ev.get("trend_direction"),
                review_count=q_ev.get("review_count", 0),
                review_insights=item["review_insights"],
                final_recommendation_score=item["final_score"],
                analytical_score=arec.overall_score,
                badges=arec.badges,
                source="ANALYTICAL_FALLBACK"
            ))
        return results
    except Exception as e:
        logger.error(f"[VendorRAG] Analytical fallback error: {e}")
        return []



# ---------------------------------------------------------------------------
# Main entry point: get_vendor_recommendations_rag
# ---------------------------------------------------------------------------
def get_vendor_recommendations_rag(
    db: Session,
    item_id: uuid.UUID,
    quantity: float = 1.0,
    llm_provider=None
) -> List[RAGVendorRecommendation]:
    """
    Full RAG + LLM vendor recommendation pipeline.
    
    Args:
        db: Database session
        item_id: The item being procured
        quantity: Requested quantity (influences bulk-order risk assessment)
        llm_provider: LLM provider instance. If None, uses analytical fallback.
    
    Returns:
        List[RAGVendorRecommendation] — ranked, evidence-backed recommendations
    
    Guarantees:
        - Always returns a result (graceful fallback if LLM fails)
        - Never includes hallucinated vendors
        - Quotation evaluation (evaluate_quotations) is NOT affected
    """
    # --- Step 1: Deterministic eligibility ---
    eligible_vendors = _get_eligible_vendors(db, item_id)
    if not eligible_vendors:
        logger.warning(f"[VendorRAG] No eligible vendors found for item {item_id}")
        return []

    # Resolve item info for prompt context
    item = db.query(Item).filter(Item.id == item_id).first()
    item_name = item.name if item else "Unknown Item"
    item_category = item.category if item else "General"

    # --- Step 2: Quantitative evidence for all eligible vendors ---
    quant_evidence: Dict[str, Any] = {}
    for vendor in eligible_vendors:
        quant_evidence[str(vendor.id)] = prepare_quantitative_evidence(db, vendor, item_id, quantity)

    # --- Short-circuit: no LLM provider — use analytical fallback ---
    # --- Short-circuit: no LLM provider — use analytical fallback ---
    if llm_provider is None:
        logger.info("[VendorRAG] No LLM provider — using analytical fallback.")
        return _analytical_fallback(db, eligible_vendors, item_id, quant_evidence, quantity)

    # --- Step 3: Generate query embedding for RAG retrieval ---
    query_text = f"vendor performance {item_name} {item_category} quality delivery reliability"
    try:
        query_embedding = llm_provider.generate_embedding(query_text)
    except Exception as e:
        logger.warning(f"[VendorRAG] Embedding generation failed: {e}. Using analytical fallback.")
        return _analytical_fallback(db, eligible_vendors, item_id, quant_evidence, quantity)

    # --- Retrieve qualitative evidence for each vendor ---
    qualitative_evidence: Dict[str, List[str]] = {}
    for vendor in eligible_vendors:
        snippets = retrieve_qualitative_evidence(
            db, vendor, item_id, item_category, query_embedding, top_k=4
        )
        qualitative_evidence[str(vendor.id)] = snippets

    # --- Compute analytical scores for context ---
    analytical_scores: Dict[str, float] = {}
    badge_map: Dict[str, List[str]] = {}
    try:
        arecs = get_vendor_recommendations(db, item_id)
        for arec in arecs:
            analytical_scores[str(arec.vendor_id)] = arec.overall_score
            badge_map[str(arec.vendor_id)] = arec.badges
    except Exception:
        pass

    # --- Build candidate vendor data for LLM prompt ---
    eligible_vendor_ids = [str(v.id) for v in eligible_vendors]
    candidates = []
    for vendor in eligible_vendors:
        vid = str(vendor.id)
        candidates.append({
            "vendor_id": vid,
            "name": vendor.name,
            "analytical_score": analytical_scores.get(vid, 75.0),
            "badges": badge_map.get(vid, []),
            "quantitative": quant_evidence[vid],
            "qualitative_evidence": qualitative_evidence[vid],
        })

    # --- Step 4: LLM reasoning ---
    prompt = _build_llm_prompt(item_name, item_category, quantity, candidates)
    llm_raw = ""
    try:
        llm_raw = llm_provider.generate_text(
            prompt=prompt,
            system_prompt=_LLM_SYSTEM_PROMPT
        )
        # Extract JSON from response (handle cases where LLM wraps in markdown code blocks)
        json_str = llm_raw.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0].strip()
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0].strip()

        # Find first { and last } to extract JSON
        start_idx = json_str.find("{")
        end_idx = json_str.rfind("}") + 1
        if start_idx >= 0 and end_idx > start_idx:
            json_str = json_str[start_idx:end_idx]

        llm_output = json.loads(json_str)

    except json.JSONDecodeError as e:
        logger.warning(f"[VendorRAG] LLM returned invalid JSON ({e}). Raw: {llm_raw[:200]}. Using fallback.")
        return _analytical_fallback(db, eligible_vendors, item_id, quant_evidence, quantity)
    except Exception as e:
        logger.warning(f"[VendorRAG] LLM call failed: {e}. Using analytical fallback.")
        return _analytical_fallback(db, eligible_vendors, item_id, quant_evidence, quantity)

    # --- Step 5: Anti-hallucination validation ---
    validated_recs = _validate_llm_output(llm_output, eligible_vendor_ids)
    if not validated_recs:
        logger.warning("[VendorRAG] LLM output contained no valid vendor IDs after validation. Using fallback.")
        return _analytical_fallback(db, eligible_vendors, item_id, quant_evidence, quantity)


    # --- Step 6: Build final RAGVendorRecommendation objects ---
    results = []
    for llm_rec in validated_recs:
        vid = str(llm_rec["vendor_id"])
        q_ev = quant_evidence.get(vid, {})

        confidence = _classify_evidence_confidence(
            q_ev.get("review_count", 0),
            q_ev.get("has_item_specific", False),
            q_ev.get("most_recent_period")
        )

        # Get fresh review insights (the actual RAG snippets that backed this recommendation)
        review_insights = qualitative_evidence.get(vid, [])
        # Trim for frontend display
        trimmed_insights = [s[:300] for s in review_insights[:2]]

        llm_status = llm_rec.get("recommendation_status", "ACCEPTABLE")
        a_score = analytical_scores.get(vid, 75.0)

        # Compute canonical final_recommendation_score
        final_score = _compute_final_recommendation_score(
            analytical_score=a_score,
            quant_evidence=q_ev,
            llm_status=llm_status,
            confidence=confidence,
        )

        results.append(RAGVendorRecommendation(
            rank=0,  # Placeholder — will be assigned after sorting by final_recommendation_score
            vendor_id=uuid.UUID(vid),
            vendor_name=llm_rec.get("vendor_name", ""),
            recommendation_status=llm_status,
            reasoning_summary=llm_rec.get("reasoning_summary", ""),
            key_strengths=llm_rec.get("key_strengths", []),
            potential_risks=llm_rec.get("potential_risks", []),
            evidence_confidence=confidence,
            avg_quality_rating=q_ev.get("avg_quality"),
            avg_delivery_rating=q_ev.get("avg_delivery"),
            avg_responsiveness_rating=q_ev.get("avg_responsiveness"),
            avg_price_rating=q_ev.get("avg_price"),
            trend_direction=q_ev.get("trend_direction"),
            review_count=q_ev.get("review_count", 0),
            review_insights=trimmed_insights,
            final_recommendation_score=final_score,
            analytical_score=a_score,
            badges=badge_map.get(vid, []),
            source="LLM_RAG"
        ))

    # Sort by final_recommendation_score DESC (tie-break: analytical_score DESC, vendor_name ASC)
    # This is the canonical deterministic ranking — the LLM integer rank is discarded as rank-setter.
    # The LLM informs final_recommendation_score via recommendation_status modifier only.
    results.sort(
        key=lambda r: (r.final_recommendation_score, r.analytical_score, r.vendor_name),
        reverse=True
    )

    # Assign final ranks based on sorted position
    for i, rec in enumerate(results):
        rec.rank = i + 1

    logger.info(
        f"[VendorRAG] Generated {len(results)} LLM_RAG recommendations for item {item_name} "
        f"(qty: {quantity}). Ranking by final_recommendation_score: "
        + ", ".join(f"{r.vendor_name}={r.final_recommendation_score}" for r in results)
    )
    return results
