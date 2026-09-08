import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.entities import (
    Inventory, PurchaseRequest, PurchaseRequestItem, PRStatus, Item, Department
)
from app.schemas.domain import InventoryAnalysisResult, DuplicateMatch

ACTIVE_PR_STATUSES = [
    PRStatus.SUBMITTED.value,
    PRStatus.UNDER_REVIEW.value,
    PRStatus.REVISION_REQUIRED.value,
    PRStatus.APPROVED_FOR_RFQ.value,
    PRStatus.RFQ_ISSUED.value,
    PRStatus.QUOTATION_RECEIVED.value,
    PRStatus.VENDOR_SELECTION_PENDING.value,
    PRStatus.FINAL_APPROVAL_PENDING.value,
    PRStatus.APPROVED.value,
]

def analyze_inventory(db: Session, item_id: uuid.UUID, requested_quantity: float) -> InventoryAnalysisResult:
    """
    Deterministic inventory analysis.
    Compares requested quantity against available quantity.
    """
    inventory_record = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    available_quantity = float(inventory_record.available_quantity) if inventory_record else 0.0
    
    if available_quantity >= requested_quantity:
        coverage_status = "SUFFICIENT"
        shortage_quantity = 0.0
    else:
        coverage_status = "INSUFFICIENT"
        shortage_quantity = float(requested_quantity - available_quantity)
        
    return InventoryAnalysisResult(
        requested_quantity=float(requested_quantity),
        available_quantity=available_quantity,
        shortage_quantity=shortage_quantity,
        coverage_status=coverage_status
    )

def detect_duplicate_requests(
    db: Session,
    item_id: uuid.UUID,
    department_id: uuid.UUID,
    requested_quantity: float,
    current_pr_id: Optional[uuid.UUID] = None,
    threshold_percent: float = settings.DUPLICATE_QUANTITY_THRESHOLD_PERCENT
) -> List[DuplicateMatch]:
    """
    Deterministic duplicate PR detection.
    Matches active PRs for the same item and department where quantity difference is within threshold.
    Excludes terminal states (COMPLETED, REJECTED, PO_GENERATED).
    """
    query = (
        db.query(PurchaseRequest, PurchaseRequestItem, Item, Department)
        .join(PurchaseRequestItem, PurchaseRequest.id == PurchaseRequestItem.purchase_request_id)
        .join(Item, PurchaseRequestItem.item_id == Item.id)
        .join(Department, PurchaseRequest.department_id == Department.id)
        .filter(
            PurchaseRequestItem.item_id == item_id,
            PurchaseRequest.department_id == department_id,
            PurchaseRequest.status.in_(ACTIVE_PR_STATUSES)
        )
    )

    if current_pr_id:
        query = query.filter(PurchaseRequest.id != current_pr_id)

    matches: List[DuplicateMatch] = []

    for pr, pr_item, item, dept in query.all():
        existing_qty = float(pr_item.quantity)
        req_qty = float(requested_quantity)
        
        max_qty = max(existing_qty, req_qty)
        if max_qty > 0:
            diff_pct = (abs(existing_qty - req_qty) / max_qty) * 100.0
        else:
            diff_pct = 0.0

        if diff_pct <= threshold_percent:
            matches.append(
                DuplicateMatch(
                    id=pr.id,
                    reference_number=pr.reference_number,
                    department_name=dept.name,
                    item_name=item.name,
                    existing_quantity=existing_qty,
                    requested_quantity=req_qty,
                    status=pr.status,
                    request_date=pr.created_at,
                    selected_vendor_name=pr.selected_vendor.name if pr.selected_vendor else None,
                    difference_percentage=round(diff_pct, 1)
                )
            )

    # Sort matches by lowest difference percentage
    matches.sort(key=lambda m: m.difference_percentage)
    return matches
