import numpy as np
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import (
    PurchaseRequest, PurchaseRequestItem, PurchaseRequestReview, User, UserRole,
    PRStatus, Item, Vendor, Department, RFQ, VendorSelectionDecision, Quotation,
    HistoricalPrice, PRRecommendationSnapshot
)
from app.schemas.domain import (
    PurchaseRequestCreate, PurchaseRequestUpdate, PurchaseRequestReturn, PurchaseRequestResubmit,
    PurchaseRequestOut, PurchaseRequestDetailOut, VendorSelectionRequest,
    FinalApprovalRequest, DuplicateMatch, PurchaseRequestReviewOut,
    QuotationAnalysisOut, QuotationAnalysisOutV2, RFQIssueRequest
)
from app.intelligence.deterministic import analyze_inventory, detect_duplicate_requests
from app.intelligence.analytical import (
    get_vendor_recommendations,
    evaluate_quotations, evaluate_quotations_v2
)
from app.services.workflow import transition_pr_status, validate_supervisor_authority
from app.services.notification_service import create_notification, record_audit
from app.api.deps import get_current_user, require_role

router = APIRouter(prefix="/purchase-requests", tags=["Procurement & Purchase Requests"])

def build_pr_out(pr: PurchaseRequest) -> PurchaseRequestOut:
    pr_item = pr.items[0] if pr.items else None
    return PurchaseRequestOut(
        id=pr.id,
        reference_number=pr.reference_number,
        requester_id=pr.requester_id,
        requester_name=pr.requester.name if pr.requester else "Unknown",
        department_id=pr.department_id,
        department_name=pr.department.name if pr.department else "Unknown",
        selected_vendor_id=pr.selected_vendor_id,
        selected_vendor_name=pr.selected_vendor.name if pr.selected_vendor else "Unknown",
        status=pr.status,
        notes=pr.notes,
        duplicate_acknowledged=pr.duplicate_acknowledged,
        item_id=pr_item.item_id if pr_item else None,
        item_name=pr_item.item.name if (pr_item and pr_item.item) else None,
        item_unit=pr_item.item.unit if (pr_item and pr_item.item) else None,
        quantity=float(pr_item.quantity) if pr_item else 0.0,
        created_at=pr.created_at,
        updated_at=pr.updated_at
    )

@router.post("", response_model=PurchaseRequestDetailOut)
def create_purchase_request(
    pr_in: PurchaseRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.EMPLOYEE.value, UserRole.ADMIN.value]))
):
    # Validate item and vendor
    item = db.query(Item).filter(Item.id == pr_in.item_id, Item.is_active == True).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified item not found or inactive.")

    vendor = db.query(Vendor).filter(Vendor.id == pr_in.selected_vendor_id, Vendor.is_active == True).first()
    if not vendor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specified vendor not found or inactive.")

    department_id = current_user.department_id
    if not department_id:
        dept = db.query(Department).first()
        department_id = dept.id if dept else None

    if not department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requester has no assigned department.")

    # Duplicate detection check
    duplicates = detect_duplicate_requests(
        db=db,
        item_id=item.id,
        department_id=department_id,
        requested_quantity=pr_in.quantity
    )
    if duplicates and not pr_in.duplicate_acknowledged:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Potential duplicate request detected: {len(duplicates)} active PR(s) with similar quantity exist in your department. Explicit acknowledgment is required."
        )

    # Generate reference number
    ref_num = f"PR-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"

    pr = PurchaseRequest(
        reference_number=ref_num,
        requester_id=current_user.id,
        department_id=department_id,
        selected_vendor_id=vendor.id,
        status=PRStatus.SUBMITTED.value,
        notes=pr_in.notes,
        duplicate_acknowledged=pr_in.duplicate_acknowledged
    )
    db.add(pr)
    db.commit()
    db.refresh(pr)

    pr_item = PurchaseRequestItem(
        purchase_request_id=pr.id,
        item_id=item.id,
        quantity=pr_in.quantity
    )
    db.add(pr_item)
    db.commit()

    # Record audit log
    record_audit(
        db=db,
        action="PR_CREATED",
        entity_type="PURCHASE_REQUEST",
        entity_id=pr.id,
        actor_id=current_user.id,
        metadata={"item": item.name, "quantity": pr_in.quantity, "vendor": vendor.name}
    )

    # Notify department supervisor
    dept = db.query(Department).filter(Department.id == department_id).first()
    if dept and dept.supervisors:
        for sup in dept.supervisors:
            create_notification(
                db=db,
                user_id=sup.id,
                notif_type="PR_SUBMITTED",
                title=f"New Purchase Request for Review: {ref_num}",
                message=f"{current_user.name} submitted {ref_num} for {pr_in.quantity}x {item.name}.",
                related_entity_type="PURCHASE_REQUEST",
                related_entity_id=pr.id
            )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.get("", response_model=List[PurchaseRequestOut])
def list_purchase_requests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(PurchaseRequest)

    if current_user.role == UserRole.EMPLOYEE.value:
        query = query.filter(PurchaseRequest.requester_id == current_user.id)
    elif current_user.role == UserRole.SUPERVISOR.value:
        if current_user.department_id:
            query = query.filter(PurchaseRequest.department_id == current_user.department_id)
    elif current_user.role == UserRole.VENDOR.value:
        return []

    prs = query.order_by(PurchaseRequest.created_at.desc()).all()
    return [build_pr_out(p) for p in prs]

@router.get("/duplicate-check", response_model=List[DuplicateMatch])
def check_duplicate_requests(
    item_id: uuid.UUID,
    quantity: float,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    department_id = current_user.department_id
    if not department_id:
        dept = db.query(Department).first()
        department_id = dept.id if dept else None

    if not department_id or quantity <= 0:
        return []

    return detect_duplicate_requests(
        db=db,
        item_id=item_id,
        department_id=department_id,
        requested_quantity=quantity
    )

@router.get("/{pr_id}", response_model=PurchaseRequestDetailOut)
def get_purchase_request_detail(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    pr_item = pr.items[0] if pr.items else None
    qty = float(pr_item.quantity) if pr_item else 1.0
    item_id = pr_item.item_id if pr_item else None

    # Deterministic Intelligence: Inventory & Duplicates
    inv_analysis = analyze_inventory(db, item_id, qty) if item_id else None
    # Duplicate warnings only apply to active requests that are not rejected or completed
    dup_matches = detect_duplicate_requests(
        db, item_id, pr.department_id, qty, current_pr_id=pr.id
    ) if (item_id and pr.status not in [PRStatus.REJECTED.value, PRStatus.PO_GENERATED.value, PRStatus.COMPLETED.value]) else []

    # Analytical Intelligence: Vendor Recommendations
    recommendations = get_vendor_recommendations(db, item_id) if item_id else []
    top_rec = recommendations[0] if recommendations else None

    # Review history
    reviews_out = []
    for r in pr.reviews:
        reviews_out.append(
            PurchaseRequestReviewOut(
                id=r.id,
                supervisor_id=r.supervisor_id,
                supervisor_name=r.supervisor.name if r.supervisor else "Supervisor",
                decision=r.decision,
                reason=r.reason,
                created_at=r.created_at
            )
        )

    base_out = build_pr_out(pr)
    return PurchaseRequestDetailOut(
        **base_out.dict(),
        inventory_analysis=inv_analysis,
        duplicate_matches=dup_matches,
        vendor_recommendation=top_rec,
        reviews=reviews_out
    )

@router.put("/{pr_id}", response_model=PurchaseRequestDetailOut)
def update_purchase_request(
    pr_id: uuid.UUID,
    pr_update: PurchaseRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    if pr.requester_id != current_user.id and current_user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester can modify this request.")

    if pr.status not in [PRStatus.DRAFT.value, PRStatus.REVISION_REQUIRED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot edit PR in status '{pr.status}'.")

    if pr_update.selected_vendor_id:
        pr.selected_vendor_id = pr_update.selected_vendor_id
    if pr_update.notes is not None:
        pr.notes = pr_update.notes

    if pr.items and pr.items[0]:
        item_or_qty_changed = False
        if pr_update.item_id:
            pr.items[0].item_id = pr_update.item_id
            item_or_qty_changed = True
        if pr_update.quantity:
            pr.items[0].quantity = pr_update.quantity
            item_or_qty_changed = True

        # Mark the latest recommendation snapshot as stale if item/qty changed
        if item_or_qty_changed:
            latest_snap = (
                db.query(PRRecommendationSnapshot)
                .filter(PRRecommendationSnapshot.purchase_request_id == pr.id)
                .order_by(PRRecommendationSnapshot.version.desc())
                .first()
            )
            if latest_snap and not latest_snap.is_stale:
                latest_snap.is_stale = True

    db.commit()
    db.refresh(pr)
    return get_purchase_request_detail(pr.id, db, current_user)

@router.delete("/{pr_id}", status_code=status.HTTP_200_OK)
def delete_purchase_request(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.EMPLOYEE.value, UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    # PO-generated or completed PRs cannot be deleted to preserve compliance/audit integrity
    if pr.status in [PRStatus.PO_GENERATED.value, PRStatus.COMPLETED.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete Purchase Request in '{pr.status}' status once official Purchase Order has been generated."
        )

    # If employee, can only delete their own request
    if current_user.role == UserRole.EMPLOYEE.value and pr.requester_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own requests.")

    record_audit(db, "PR_DELETED", "PURCHASE_REQUEST", pr.id, current_user.id, metadata={"reference": pr.reference_number})

    # Clean up associated RFQs, quotations, items and reviews
    for rfq in db.query(RFQ).filter(RFQ.purchase_request_id == pr.id).all():
        db.query(Quotation).filter(Quotation.rfq_id == rfq.id).delete()
        db.delete(rfq)
    db.query(PurchaseRequestItem).filter(PurchaseRequestItem.purchase_request_id == pr.id).delete()
    db.query(PurchaseRequestReview).filter(PurchaseRequestReview.purchase_request_id == pr.id).delete()
    db.delete(pr)
    db.commit()

    return {"message": f"Purchase Request {pr.reference_number} deleted successfully."}

@router.post("/{pr_id}/submit", response_model=PurchaseRequestDetailOut)
def submit_purchase_request(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    if pr.status not in [PRStatus.DRAFT.value, PRStatus.REVISION_REQUIRED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot submit PR in status '{pr.status}'.")

    pr.status = PRStatus.SUBMITTED.value
    db.commit()

    record_audit(db, "PR_RESUBMITTED", "PURCHASE_REQUEST", pr.id, current_user.id)
    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/resubmit", response_model=PurchaseRequestDetailOut)
def resubmit_purchase_request(
    pr_id: uuid.UUID,
    resubmit_in: Optional[PurchaseRequestResubmit] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    if pr.requester_id != current_user.id and current_user.role not in [UserRole.SUPERVISOR.value, UserRole.ADMIN.value]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the requester or an administrator can resubmit this request.")

    if pr.status not in [PRStatus.DRAFT.value, PRStatus.REVISION_REQUIRED.value]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot resubmit PR in status '{pr.status}'.")

    # Apply updates if provided
    if resubmit_in:
        if resubmit_in.selected_vendor_id:
            vendor = db.query(Vendor).filter(Vendor.id == resubmit_in.selected_vendor_id).first()
            if not vendor:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Selected vendor not found.")
            pr.selected_vendor_id = vendor.id

        if resubmit_in.notes is not None:
            pr.notes = resubmit_in.notes

        if resubmit_in.quantity and pr.items:
            pr.items[0].quantity = resubmit_in.quantity
            # Mark recommendation snapshot as stale if quantity changed
            latest_snap = (
                db.query(PRRecommendationSnapshot)
                .filter(PRRecommendationSnapshot.purchase_request_id == pr.id)
                .order_by(PRRecommendationSnapshot.version.desc())
                .first()
            )
            if latest_snap and not latest_snap.is_stale:
                latest_snap.is_stale = True

    pr.status = PRStatus.SUBMITTED.value
    db.commit()
    db.refresh(pr)

    record_audit(
        db=db,
        action="PR_RESUBMITTED",
        entity_type="PURCHASE_REQUEST",
        entity_id=pr.id,
        actor_id=current_user.id,
        metadata={"quantity": float(pr.items[0].quantity) if pr.items else None, "notes": pr.notes}
    )

    # Notify department supervisors
    dept = db.query(Department).filter(Department.id == pr.department_id).first()
    if dept and dept.supervisors:
        for sup in dept.supervisors:
            create_notification(
                db=db,
                user_id=sup.id,
                notif_type="PR_RESUBMITTED",
                title=f"Purchase Request Resubmitted: {pr.reference_number}",
                message=f"{current_user.name} has revised and resubmitted {pr.reference_number} for supervisor review.",
                related_entity_type="PURCHASE_REQUEST",
                related_entity_id=pr.id
            )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/return", response_model=PurchaseRequestDetailOut)
def return_purchase_request(
    pr_id: uuid.UUID,
    ret_in: PurchaseRequestReturn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    transition_pr_status(
        db=db,
        pr=pr,
        target_status=PRStatus.REVISION_REQUIRED,
        actor=current_user,
        decision_type="RETURNED_FOR_REVISION",
        reason=ret_in.reason
    )

    record_audit(db, "PR_RETURNED", "PURCHASE_REQUEST", pr.id, current_user.id, metadata={"reason": ret_in.reason})

    create_notification(
        db=db,
        user_id=pr.requester_id,
        notif_type="PR_RETURNED",
        title=f"Purchase Request Returned: {pr.reference_number}",
        message=f"Supervisor {current_user.name} requested revision: {ret_in.reason}",
        related_entity_type="PURCHASE_REQUEST",
        related_entity_id=pr.id
    )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/reject", response_model=PurchaseRequestDetailOut)
def reject_purchase_request(
    pr_id: uuid.UUID,
    rej_in: PurchaseRequestReturn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    if not rej_in.reason or len(rej_in.reason.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rejecting a PR requires a mandatory, substantive reason."
        )

    transition_pr_status(
        db=db,
        pr=pr,
        target_status=PRStatus.REJECTED,
        actor=current_user,
        decision_type="REJECTED",
        reason=rej_in.reason
    )

    record_audit(db, "PR_REJECTED", "PURCHASE_REQUEST", pr.id, current_user.id, metadata={"reason": rej_in.reason})

    create_notification(
        db=db,
        user_id=pr.requester_id,
        notif_type="PR_REJECTED",
        title=f"Purchase Request Rejected: {pr.reference_number}",
        message=f"Supervisor {current_user.name} rejected this request: {rej_in.reason}",
        related_entity_type="PURCHASE_REQUEST",
        related_entity_id=pr.id
    )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/approve-to-proceed", response_model=PurchaseRequestDetailOut)
def approve_to_proceed(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    """
    Stage 1 supervisor action: Approve the PR for the RFQ process.
    This transitions the PR to UNDER_REVIEW status to signal the supervisor
    is ready to select vendors and issue RFQs.

    The actual RFQ issuance is done via POST /{pr_id}/issue-rfqs, where the
    supervisor explicitly selects 1–3 vendors and sets a deadline.
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    if pr.status not in [PRStatus.SUBMITTED.value, PRStatus.UNDER_REVIEW.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PR cannot be approved. Current status: '{pr.status}'. Must be SUBMITTED or UNDER_REVIEW."
        )

    transition_pr_status(
        db=db,
        pr=pr,
        target_status=PRStatus.UNDER_REVIEW,
        actor=current_user,
        decision_type="APPROVED_TO_PROCEED",
        reason="Approved for vendor selection and RFQ issuance."
    )

    record_audit(db, "PR_APPROVED_TO_REVIEW", "PURCHASE_REQUEST", pr.id, current_user.id)

    return get_purchase_request_detail(pr.id, db, current_user)


@router.post("/{pr_id}/issue-rfqs", response_model=PurchaseRequestDetailOut)
def issue_rfqs(
    pr_id: uuid.UUID,
    rfq_request: RFQIssueRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    """
    Stage 2 supervisor action: Issue RFQs to 1–3 supervisor-selected vendors.

    The supervisor curates the vendor shortlist (informed by the AI RAG snapshot)
    and explicitly selects which vendors receive an RFQ. This is the only way
    to create RFQs — they are never auto-generated.
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    # Allow from SUBMITTED, UNDER_REVIEW, or APPROVED_FOR_RFQ (legacy compat)
    if pr.status not in [
        PRStatus.SUBMITTED.value,
        PRStatus.UNDER_REVIEW.value,
        PRStatus.APPROVED_FOR_RFQ.value,
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot issue RFQs for PR in status '{pr.status}'. PR must be in SUBMITTED or UNDER_REVIEW status."
        )

    # Validate vendor count
    if not rfq_request.vendor_ids or len(rfq_request.vendor_ids) == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least 1 vendor must be selected.")
    if len(rfq_request.vendor_ids) > 3:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 3 vendors can be invited per RFQ round.")

    # Parse deadline
    if rfq_request.due_date:
        try:
            due_at = datetime.fromisoformat(rfq_request.due_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            due_at = datetime.utcnow() + timedelta(days=7)
    else:
        due_at = datetime.utcnow() + timedelta(days=7)

    # Get PR item context
    pr_item = pr.items[0] if pr.items else None
    item = pr_item.item if pr_item else None

    issued_rfqs = []
    for vendor_id in rfq_request.vendor_ids:
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id, Vendor.is_active == True).first()
        if not vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendor ID {vendor_id} not found or inactive."
            )

        # Check if RFQ already exists for this vendor/PR pair
        existing_rfq = db.query(RFQ).filter(
            RFQ.purchase_request_id == pr.id,
            RFQ.vendor_id == vendor.id
        ).first()
        if existing_rfq:
            # Update deadline if RFQ exists but hasn't been quoted yet
            if existing_rfq.status in ["AWAITING_QUOTATION", "ISSUED"]:
                existing_rfq.due_at = due_at
            issued_rfqs.append(existing_rfq)
            continue

        rfq_ref = f"RFQ-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"
        rfq = RFQ(
            reference_number=rfq_ref,
            purchase_request_id=pr.id,
            vendor_id=vendor.id,
            status="AWAITING_QUOTATION",
            issued_at=datetime.utcnow(),
            due_at=due_at
        )
        db.add(rfq)
        db.flush()
        issued_rfqs.append(rfq)

        record_audit(db, "RFQ_ISSUED", "RFQ", rfq.id, current_user.id,
                     metadata={"rfq_ref": rfq_ref, "vendor": vendor.name, "due_at": due_at.isoformat()})

        # Notify vendor user(s)
        vendor_users = db.query(User).filter(User.vendor_id == vendor.id).all()
        for vendor_user in vendor_users:
            create_notification(
                db=db,
                user_id=vendor_user.id,
                notif_type="RFQ_ISSUED",
                title=f"New RFQ Assigned: {rfq_ref}",
                message=(
                    f"You have been invited to submit a quotation for "
                    f"{pr_item.quantity if pr_item else 1} "
                    f"{item.unit if item else 'units'} of {item.name if item else 'goods'}. "
                    f"Deadline: {due_at.strftime('%Y-%m-%d')}."
                ),
                related_entity_type="RFQ",
                related_entity_id=rfq.id
            )

    # Transition PR to RFQS_ISSUED / AWAITING_QUOTATIONS
    pr.status = PRStatus.AWAITING_QUOTATIONS.value
    db.commit()

    record_audit(db, "RFQS_ISSUED", "PURCHASE_REQUEST", pr.id, current_user.id,
                 metadata={"vendor_count": len(issued_rfqs)})

    # Notify requester
    create_notification(
        db=db,
        user_id=pr.requester_id,
        notif_type="RFQS_ISSUED",
        title=f"RFQs Issued for Your Request: {pr.reference_number}",
        message=(
            f"Supervisor {current_user.name} issued RFQs to {len(issued_rfqs)} vendor(s) "
            f"for your purchase request. Deadline: {due_at.strftime('%Y-%m-%d')}."
        ),
        related_entity_type="PURCHASE_REQUEST",
        related_entity_id=pr.id
    )

    return get_purchase_request_detail(pr.id, db, current_user)


@router.post("/{pr_id}/vendor-selection", response_model=PurchaseRequestDetailOut)
def select_vendor(
    pr_id: uuid.UUID,
    decision_in: VendorSelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    # Quotation evaluation to know who is recommended
    # If no quotations exist yet, rec_id falls back to the currently selected vendor (no false override)
    analysis = evaluate_quotations_v2(db, pr.id)
    rec_id = analysis.recommended_vendor_id if analysis.recommended_vendor_id else pr.selected_vendor_id

    # Safe string comparison to avoid uuid.UUID != str false-override bug
    is_override = bool(rec_id and str(decision_in.selected_vendor_id).lower() != str(rec_id).lower())
    if is_override and (not decision_in.override_reason or len(decision_in.override_reason.strip()) < 3):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Overriding the system-recommended vendor requires a mandatory, substantive reason."
        )

    # Persist or update selection decision
    existing_dec = db.query(VendorSelectionDecision).filter(VendorSelectionDecision.purchase_request_id == pr.id).first()
    if existing_dec:
        existing_dec.recommended_vendor_id = rec_id
        existing_dec.selected_vendor_id = decision_in.selected_vendor_id
        existing_dec.supervisor_id = current_user.id
        existing_dec.override_reason = decision_in.override_reason if is_override else None
    else:
        new_dec = VendorSelectionDecision(
            purchase_request_id=pr.id,
            recommended_vendor_id=rec_id,
            selected_vendor_id=decision_in.selected_vendor_id,
            supervisor_id=current_user.id,
            override_reason=decision_in.override_reason if is_override else None
        )
        db.add(new_dec)

    pr.selected_vendor_id = decision_in.selected_vendor_id
    pr.status = PRStatus.FINAL_APPROVAL_PENDING.value
    db.commit()

    action_name = "VENDOR_OVERRIDE" if is_override else "VENDOR_SELECTED"
    record_audit(
        db, action_name, "PURCHASE_REQUEST", pr.id, current_user.id,
        metadata={
            "recommended": str(rec_id),
            "selected": str(decision_in.selected_vendor_id),
            "reason": decision_in.override_reason
        }
    )

    # In-app notifications for vendor user(s)
    vendor_users = db.query(User).filter(User.vendor_id == decision_in.selected_vendor_id).all()
    for v_user in vendor_users:
        create_notification(
            db=db,
            user_id=v_user.id,
            notif_type="BID_SELECTED",
            title=f"Quotation Awarded: {pr.reference_number}",
            message=f"Congratulations! Your quotation for PR {pr.reference_number} has been selected as the winning bid.",
            related_entity_type="PURCHASE_REQUEST",
            related_entity_id=pr.id
        )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/final-approval", response_model=PurchaseRequestDetailOut)
def final_approval(
    pr_id: uuid.UUID,
    approval_in: FinalApprovalRequest = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    validate_supervisor_authority(db, current_user, pr)

    # Accept any late-stage status so the single-button flow works
    # even if vendor-selection wasn't explicitly confirmed by the supervisor
    APPROVABLE_STATUSES = [
        PRStatus.FINAL_APPROVAL_PENDING.value,
        PRStatus.VENDOR_SELECTION_PENDING.value,
        PRStatus.QUOTATIONS_READY.value,           # New: V2 workflow
        PRStatus.RFQ_ISSUED.value,                 # Legacy
        PRStatus.QUOTATION_RECEIVED.value,         # Legacy
    ]
    if pr.status not in APPROVABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"PR cannot be approved. Current status: '{pr.status}'. Required: one of {APPROVABLE_STATUSES}."
        )

    # At least one valid quotation must exist
    quote_exists = (
        db.query(Quotation)
        .join(RFQ, Quotation.rfq_id == RFQ.id)
        .filter(RFQ.purchase_request_id == pr.id)
        .first()
    )
    if not quote_exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot grant final approval without at least one submitted quotation."
        )

    # Auto-create vendor selection decision if none exists (convenience for single-button flow)
    existing_dec = db.query(VendorSelectionDecision).filter(VendorSelectionDecision.purchase_request_id == pr.id).first()
    if not existing_dec:
        analysis = evaluate_quotations_v2(db, pr.id)
        rec_id = analysis.recommended_vendor_id or pr.selected_vendor_id
        if rec_id:
            pr.selected_vendor_id = rec_id
            new_dec = VendorSelectionDecision(
                purchase_request_id=pr.id,
                recommended_vendor_id=rec_id,
                selected_vendor_id=rec_id,
                supervisor_id=current_user.id,
                override_reason=None
            )
            db.add(new_dec)

    # Final vendor must be selected
    if not pr.selected_vendor_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A final vendor must be selected prior to approval."
        )

    pr.status = PRStatus.APPROVED.value
    db.commit()

    record_audit(db, "FINAL_APPROVED", "PURCHASE_REQUEST", pr.id, current_user.id)

    create_notification(
        db=db,
        user_id=pr.requester_id,
        notif_type="FINAL_APPROVAL_COMPLETED",
        title=f"PR Fully Approved: {pr.reference_number}",
        message=f"Your Purchase Request {pr.reference_number} has received final supervisor approval.",
        related_entity_type="PURCHASE_REQUEST",
        related_entity_id=pr.id
    )

    return get_purchase_request_detail(pr.id, db, current_user)

@router.post("/{pr_id}/simulate-bids", response_model=QuotationAnalysisOutV2)
def simulate_bids_for_pr(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    """
    Simulates receiving competitive quotations from all eligible suppliers for this PR's item.
    Enables immediate, realistic multi-vendor bid evaluation in the supervisor dashboard.

    If RFQs already exist (from issue-rfqs), simulates quotes for those vendors.
    If no RFQs exist, creates them for the top eligible vendors.
    Simulated quotes include expected_delivery_date as a first-class field.
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    pr_item = pr.items[0] if pr.items else None
    if not pr_item:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Purchase Request has no requested items.")

    item = pr_item.item
    qty = float(pr_item.quantity)

    # Use existing RFQs if available; otherwise get eligible vendors
    existing_rfqs = db.query(RFQ).filter(RFQ.purchase_request_id == pr.id).all()
    if existing_rfqs:
        # Simulate only for vendors with existing RFQs (supervisor pre-selected)
        vendors_to_simulate = [(rfq.vendor, rfq) for rfq in existing_rfqs if rfq.vendor]
    else:
        # Fall back: get eligible vendors and create RFQs
        eligible_vendors = list(item.vendors) if item.vendors else db.query(Vendor).limit(3).all()
        if not eligible_vendors:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No vendors available for this item.")
        vendors_to_simulate = []
        for v in eligible_vendors:
            rfq = db.query(RFQ).filter(RFQ.purchase_request_id == pr.id, RFQ.vendor_id == v.id).first()
            if not rfq:
                rfq_ref = f"RFQ-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"
                rfq = RFQ(
                    reference_number=rfq_ref,
                    purchase_request_id=pr.id,
                    vendor_id=v.id,
                    status="AWAITING_QUOTATION",
                    issued_at=datetime.utcnow(),
                    due_at=datetime.utcnow() + timedelta(days=7)
                )
                db.add(rfq)
                db.commit()
                db.refresh(rfq)
            vendors_to_simulate.append((v, rfq))

    # Get median baseline price
    hist_prices = [hp.unit_price for hp in db.query(HistoricalPrice).filter(HistoricalPrice.item_id == item.id).all()]
    base_price = float(np.median(hist_prices)) if hist_prices else 500.0

    # Realistic competitive bid profiles
    price_factors = [1.0, 0.94, 1.06, 0.98, 1.03]
    lead_times = [5, 10, 2, 7, 4]
    # Delivery dates: 7, 12, 4, 9, 6 days from today
    delivery_offsets = [7, 12, 4, 9, 6]
    notes_templates = [
        "Official commercial proposal adhering to corporate SLA and manufacturer warranty.",
        "Competitive bulk rate with standard ground logistics fulfillment.",
        "Expedited express delivery with dedicated enterprise account management.",
        "Value commercial bid with certified quality standards.",
        "Standard commercial fulfillment terms with 30-day price validity."
    ]

    today = datetime.utcnow().date()

    for idx, (v, rfq) in enumerate(vendors_to_simulate):
        # Ensure Quote exists (don't overwrite existing real quotes)
        quote = db.query(Quotation).filter(Quotation.rfq_id == rfq.id).first()
        if not quote:
            factor = price_factors[idx % len(price_factors)]
            u_price = round(base_price * factor, 2)
            l_time = lead_times[idx % len(lead_times)]
            delivery_days = delivery_offsets[idx % len(delivery_offsets)]
            delivery_date_str = (today + timedelta(days=delivery_days)).strftime("%Y-%m-%d")
            n_text = notes_templates[idx % len(notes_templates)]
            quote = Quotation(
                rfq_id=rfq.id,
                vendor_id=v.id,
                quoted_unit_price=u_price,
                total_price=round(u_price * qty, 2),
                lead_time_days=l_time,
                expected_delivery_date=delivery_date_str,
                validity_period="30 Days",
                notes=n_text
            )
            db.add(quote)
            rfq.status = "QUOTATION_RECEIVED"

    pr.status = PRStatus.VENDOR_SELECTION_PENDING.value
    db.commit()

    record_audit(db, "BIDS_SIMULATED", "PURCHASE_REQUEST", pr.id, current_user.id,
                 metadata={"vendor_count": len(vendors_to_simulate)})

    return evaluate_quotations_v2(db, pr.id)

