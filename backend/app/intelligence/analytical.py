import uuid
from datetime import datetime, date
from typing import List, Optional, Tuple
import numpy as np
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    Vendor, VendorPerformance, VendorItemPerformance, HistoricalPrice, Quotation, RFQ, BadgeType
)
from app.schemas.domain import (
    VendorRecommendationOut, VendorFactorBreakdown,
    QuotationEvaluationItem, QuotationAnalysisOut,
    QuotationEvaluationItemV2, QuotationAnalysisOutV2
)

def compute_vendor_badges(overall_score: float, quality: float, delivery: float, price: float) -> List[str]:
    """
    Deterministic rule-based vendor badges based on performance thresholds.
    """
    badges = []
    if overall_score >= 90.0:
        badges.append(BadgeType.PREFERRED_VENDOR.value)
    if delivery >= 90.0:
        badges.append(BadgeType.HIGH_RELIABILITY.value)
    if quality >= 90.0:
        badges.append(BadgeType.QUALITY_LEADER.value)
    if price >= 90.0:
        badges.append(BadgeType.COST_EFFICIENT.value)
    if overall_score < 60.0:
        badges.append(BadgeType.NEEDS_ATTENTION.value)
    return badges

def get_vendor_recommendations(db: Session, item_id: uuid.UUID) -> List[VendorRecommendationOut]:
    """
    Analytical vendor recommendation engine.
    Calculates explainable weighted vendor scores for all eligible vendors.
    """
    # Fetch all active vendors
    vendors = db.query(Vendor).filter(Vendor.is_active == True).all()
    if not vendors:
        return []

    scored_vendors = []

    for vendor in vendors:
        # Check if vendor has eligibility mapping for this item, or treat all active if mapping is empty
        if vendor.eligible_items and not any(item.id == item_id for item in vendor.eligible_items):
            continue

        # Get latest vendor performance record
        perf = (
            db.query(VendorPerformance)
            .filter(VendorPerformance.vendor_id == vendor.id)
            .order_by(VendorPerformance.measurement_period.desc())
            .first()
        )

        # Get item-specific performance
        item_perf = (
            db.query(VendorItemPerformance)
            .filter(
                VendorItemPerformance.vendor_id == vendor.id,
                VendorItemPerformance.item_id == item_id
            )
            .order_by(VendorItemPerformance.measurement_period.desc())
            .first()
        )

        # Base factors (default to 75.0 if vendor is new)
        quality = float(perf.quality_score) if perf else 75.0
        delivery = float(perf.delivery_reliability_score) if perf else 75.0
        item_spec = float(item_perf.item_specific_score) if item_perf else quality
        price = float(perf.price_competitiveness_score) if perf else 75.0
        fulfillment = float(perf.historical_fulfillment_score) if perf else 75.0
        responsiveness = float(perf.responsiveness_score) if perf else 75.0

        # Weighted calculation
        overall_score = (
            settings.WEIGHT_QUALITY * quality +
            settings.WEIGHT_DELIVERY_RELIABILITY * delivery +
            settings.WEIGHT_ITEM_SPECIFIC * item_spec +
            settings.WEIGHT_PRICE_COMPETITIVENESS * price +
            settings.WEIGHT_HISTORICAL_FULFILLMENT * fulfillment +
            settings.WEIGHT_RESPONSIVENESS * responsiveness
        )

        badges = compute_vendor_badges(overall_score, quality, delivery, price)
        confidence = "HIGH" if (perf and item_perf) else ("MEDIUM" if perf else "LOW")

        explanation_parts = []
        if quality >= 88:
            explanation_parts.append(f"Outstanding quality rating ({round(quality, 1)}%)")
        if delivery >= 88:
            explanation_parts.append(f"Exceptional delivery punctuality ({round(delivery, 1)}%)")
        if price >= 88:
            explanation_parts.append(f"Highly competitive pricing ({round(price, 1)}%)")
        if not explanation_parts:
            explanation_parts.append(f"Balanced performance across categories (Score: {round(overall_score, 1)})")

        scored_vendors.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "overall_score": round(overall_score, 1),
            "quality": round(quality, 1),
            "delivery": round(delivery, 1),
            "item_specific": round(item_spec, 1),
            "price": round(price, 1),
            "fulfillment": round(fulfillment, 1),
            "responsiveness": round(responsiveness, 1),
            "badges": badges,
            "explanation": " • ".join(explanation_parts),
            "confidence": confidence
        })

    # Sort with deterministic tie-breaking: overall_score DESC, delivery DESC, quality DESC, vendor_name ASC
    scored_vendors.sort(
        key=lambda v: (v["overall_score"], v["delivery"], v["quality"], v["vendor_name"]),
        reverse=True
    )

    results = []
    for rank, sv in enumerate(scored_vendors, start=1):
        results.append(
            VendorRecommendationOut(
                rank=rank,
                vendor_id=sv["vendor_id"],
                vendor_name=sv["vendor_name"],
                overall_score=sv["overall_score"],
                badges=sv["badges"],
                factor_breakdown=VendorFactorBreakdown(
                    quality=sv["quality"],
                    delivery_reliability=sv["delivery"],
                    item_specific=sv["item_specific"],
                    price_competitiveness=sv["price"],
                    historical_fulfillment=sv["fulfillment"],
                    responsiveness=sv["responsiveness"]
                ),
                explanation=sv["explanation"],
                score_confidence=sv["confidence"]
            )
        )

    return results

def evaluate_quotations(db: Session, purchase_request_id: uuid.UUID) -> QuotationAnalysisOut:
    """
    Weighted quotation evaluation algorithm.
    Weights: Price (40%), Delivery Lead Time (20%), Vendor Reliability (20%), Quality (20%).
    """
    # Fetch all quotations submitted for this PR's RFQs
    quotes = (
        db.query(Quotation, RFQ, Vendor)
        .join(RFQ, Quotation.rfq_id == RFQ.id)
        .join(Vendor, Quotation.vendor_id == Vendor.id)
        .filter(RFQ.purchase_request_id == purchase_request_id)
        .all()
    )

    if not quotes:
        return QuotationAnalysisOut(
            purchase_request_id=purchase_request_id,
            pr_reference="N/A",
            evaluations=[],
            recommended_vendor_id=None,
            recommended_vendor_name=None
        )

    pr_ref = quotes[0][1].purchase_request.reference_number if quotes[0][1].purchase_request else "PR"

    # Find lowest quote and shortest lead time
    min_unit_price = min(float(q[0].quoted_unit_price) for q in quotes)
    min_lead_time = min(int(q[0].lead_time_days) for q in quotes)
    if min_lead_time <= 0:
        min_lead_time = 1

    evaluation_items = []

    for quote, rfq, vendor in quotes:
        unit_price = float(quote.quoted_unit_price)
        lead_time = max(int(quote.lead_time_days), 1)

        # Normalized Price Score: (min / actual) * 100
        price_score = (min_unit_price / unit_price) * 100.0 if unit_price > 0 else 0.0

        # Normalized Delivery Score: (min / actual) * 100
        delivery_score = (min_lead_time / lead_time) * 100.0

        # Vendor historical performance
        perf = (
            db.query(VendorPerformance)
            .filter(VendorPerformance.vendor_id == vendor.id)
            .order_by(VendorPerformance.measurement_period.desc())
            .first()
        )

        reliability_score = float(perf.delivery_reliability_score) if perf else 75.0
        quality_score = float(perf.quality_score) if perf else 75.0

        # Final weighted composite score
        final_score = (
            settings.QUOTE_WEIGHT_PRICE * price_score +
            settings.QUOTE_WEIGHT_DELIVERY * delivery_score +
            settings.QUOTE_WEIGHT_RELIABILITY * reliability_score +
            settings.QUOTE_WEIGHT_QUALITY * quality_score
        )

        badges = [b.badge_type for b in vendor.badges]

        evaluation_items.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "quoted_unit_price": round(unit_price, 2),
            "total_price": round(float(quote.total_price), 2),
            "lead_time_days": lead_time,
            "price_score": round(price_score, 1),
            "delivery_score": round(delivery_score, 1),
            "reliability_score": round(reliability_score, 1),
            "quality_score": round(quality_score, 1),
            "final_weighted_score": round(final_score, 1),
            "badges": badges
        })

    # Sort: final_weighted_score DESC, reliability_score DESC, delivery_score DESC, price ASC
    evaluation_items.sort(
        key=lambda e: (e["final_weighted_score"], e["reliability_score"], e["delivery_score"], -e["quoted_unit_price"]),
        reverse=True
    )

    eval_results: List[QuotationEvaluationItem] = []
    recommended_id = None
    recommended_name = None

    for rank, item in enumerate(evaluation_items, start=1):
        is_rec = (rank == 1)
        if is_rec:
            recommended_id = item["vendor_id"]
            recommended_name = item["vendor_name"]

        eval_results.append(
            QuotationEvaluationItem(
                rank=rank,
                vendor_id=item["vendor_id"],
                vendor_name=item["vendor_name"],
                quoted_unit_price=item["quoted_unit_price"],
                total_price=item["total_price"],
                lead_time_days=item["lead_time_days"],
                price_score=item["price_score"],
                delivery_score=item["delivery_score"],
                reliability_score=item["reliability_score"],
                quality_score=item["quality_score"],
                final_weighted_score=item["final_weighted_score"],
                is_recommended=is_rec,
                vendor_badges=item["badges"]
            )
        )

    return QuotationAnalysisOut(
        purchase_request_id=purchase_request_id,
        pr_reference=pr_ref,
        evaluations=eval_results,
        recommended_vendor_id=recommended_id,
        recommended_vendor_name=recommended_name
    )


def evaluate_quotations_v2(db: Session, purchase_request_id: uuid.UUID) -> QuotationAnalysisOutV2:
    """
    V2 weighted quotation evaluation algorithm for the multi-vendor RFQ workflow.

    Scoring weights (from config):
      Price             35%  — normalized: lowest price = 100
      Delivery Date     20%  — normalized: earliest committed delivery date = 100
      Lead Time         15%  — normalized: shortest lead time = 100
      Reliability       15%  — vendor historical delivery reliability (0-100)
      Quality           15%  — vendor historical quality score (0-100)

    IMPORTANT: Original evaluate_quotations() is NOT modified. This V2 runs independently.
    Expired RFQs (status RFQ_EXPIRED) are excluded from evaluation.
    """
    # Fetch valid quotations (exclude expired RFQs)
    quotes = (
        db.query(Quotation, RFQ, Vendor)
        .join(RFQ, Quotation.rfq_id == RFQ.id)
        .join(Vendor, Quotation.vendor_id == Vendor.id)
        .filter(RFQ.purchase_request_id == purchase_request_id)
        .filter(RFQ.status.notin_(["RFQ_EXPIRED", "RFQ_CANCELLED"]))
        .all()
    )

    if not quotes:
        return QuotationAnalysisOutV2(
            purchase_request_id=purchase_request_id,
            pr_reference="N/A",
            evaluations=[],
            recommended_vendor_id=None,
            recommended_vendor_name=None
        )

    pr = quotes[0][1].purchase_request
    pr_ref = pr.reference_number if pr else "PR"

    # Normalize price
    min_unit_price = min(float(q[0].quoted_unit_price) for q in quotes)

    # Normalize lead time
    min_lead_time = min(int(q[0].lead_time_days) for q in quotes)
    if min_lead_time <= 0:
        min_lead_time = 1

    # Parse delivery dates — find the earliest
    def parse_delivery_date(date_str: Optional[str]) -> Optional[date]:
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None

    delivery_dates = [parse_delivery_date(q[0].expected_delivery_date) for q in quotes]
    valid_dates = [d for d in delivery_dates if d is not None]
    earliest_date = min(valid_dates) if valid_dates else None
    today = datetime.utcnow().date()

    evaluation_items = []

    for idx, (quote, rfq, vendor) in enumerate(quotes):
        unit_price = float(quote.quoted_unit_price)
        lead_time = max(int(quote.lead_time_days), 1)

        # Price score: lowest price = 100
        price_score = (min_unit_price / unit_price) * 100.0 if unit_price > 0 else 0.0

        # Lead time score: shortest lead time = 100
        lead_time_score = (min_lead_time / lead_time) * 100.0

        # Delivery date score: earliest delivery date = 100
        # If no delivery date provided → score 50 (neutral penalty)
        del_date = parse_delivery_date(quote.expected_delivery_date)
        if del_date is not None and earliest_date is not None:
            days_from_today = max((del_date - today).days, 1)
            earliest_days = max((earliest_date - today).days, 1)
            delivery_date_score = (earliest_days / days_from_today) * 100.0
            delivery_date_score = min(delivery_date_score, 100.0)
        else:
            delivery_date_score = 50.0  # Neutral: no date committed

        # Vendor historical performance
        perf = (
            db.query(VendorPerformance)
            .filter(VendorPerformance.vendor_id == vendor.id)
            .order_by(VendorPerformance.measurement_period.desc())
            .first()
        )
        reliability_score = float(perf.delivery_reliability_score) if perf else 75.0
        quality_score = float(perf.quality_score) if perf else 75.0

        # Final V2 weighted composite score
        final_score = (
            settings.QUOTE_V2_WEIGHT_PRICE * price_score +
            settings.QUOTE_V2_WEIGHT_DELIVERY_DATE * delivery_date_score +
            settings.QUOTE_V2_WEIGHT_LEAD_TIME * lead_time_score +
            settings.QUOTE_V2_WEIGHT_RELIABILITY * reliability_score +
            settings.QUOTE_V2_WEIGHT_QUALITY * quality_score
        )

        badges = [b.badge_type for b in vendor.badges]

        evaluation_items.append({
            "vendor_id": vendor.id,
            "vendor_name": vendor.name,
            "quoted_unit_price": round(unit_price, 2),
            "total_price": round(float(quote.total_price), 2),
            "lead_time_days": lead_time,
            "expected_delivery_date": quote.expected_delivery_date,
            "price_score": round(price_score, 1),
            "lead_time_score": round(lead_time_score, 1),
            "delivery_date_score": round(delivery_date_score, 1),
            "reliability_score": round(reliability_score, 1),
            "quality_score": round(quality_score, 1),
            "final_weighted_score": round(final_score, 1),
            "badges": badges,
        })

    # Sort: final_weighted_score DESC, delivery_date_score DESC, price ASC
    evaluation_items.sort(
        key=lambda e: (e["final_weighted_score"], e["delivery_date_score"], -e["quoted_unit_price"]),
        reverse=True
    )

    eval_results: List[QuotationEvaluationItemV2] = []
    recommended_id = None
    recommended_name = None

    for rank, item in enumerate(evaluation_items, start=1):
        is_rec = (rank == 1)
        if is_rec:
            recommended_id = item["vendor_id"]
            recommended_name = item["vendor_name"]

        eval_results.append(
            QuotationEvaluationItemV2(
                rank=rank,
                vendor_id=item["vendor_id"],
                vendor_name=item["vendor_name"],
                quoted_unit_price=item["quoted_unit_price"],
                total_price=item["total_price"],
                lead_time_days=item["lead_time_days"],
                expected_delivery_date=item["expected_delivery_date"],
                price_score=item["price_score"],
                lead_time_score=item["lead_time_score"],
                delivery_date_score=item["delivery_date_score"],
                reliability_score=item["reliability_score"],
                quality_score=item["quality_score"],
                final_weighted_score=item["final_weighted_score"],
                is_recommended=is_rec,
                vendor_badges=item["badges"]
            )
        )

    return QuotationAnalysisOutV2(
        purchase_request_id=purchase_request_id,
        pr_reference=pr_ref,
        evaluations=eval_results,
        recommended_vendor_id=recommended_id,
        recommended_vendor_name=recommended_name
    )
