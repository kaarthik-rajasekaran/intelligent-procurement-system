from typing import List
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import RFQ, Quotation, PurchaseRequest, User, UserRole, PRStatus
from app.schemas.domain import RFQOut, QuotationCreate, QuotationOut, QuotationAnalysisOutV2
from app.intelligence.analytical import evaluate_quotations_v2
from app.services.notification_service import create_notification, record_audit
from app.api.deps import get_current_user

router = APIRouter(prefix="/rfqs", tags=["RFQs & Quotations"])

def build_rfq_out(rfq: RFQ) -> RFQOut:
    pr = rfq.purchase_request
    pr_item = pr.items[0] if (pr and pr.items) else None
    return RFQOut(
        id=rfq.id,
        reference_number=rfq.reference_number,
        purchase_request_id=rfq.purchase_request_id,
        pr_reference=pr.reference_number if pr else "N/A",
        item_name=pr_item.item.name if (pr_item and pr_item.item) else "Item",
        item_unit=pr_item.item.unit if (pr_item and pr_item.item) else "units",
        quantity=float(pr_item.quantity) if pr_item else 1.0,
        vendor_id=rfq.vendor_id,
        vendor_name=rfq.vendor.name if rfq.vendor else "Vendor",
        status=rfq.status,
        issued_at=rfq.issued_at,
        due_at=rfq.due_at,
        has_quotation=bool(rfq.quotation)
    )

@router.get("", response_model=List[RFQOut])
def list_rfqs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(RFQ)
    if current_user.role == UserRole.VENDOR.value:
        if current_user.vendor_id:
            query = query.filter(RFQ.vendor_id == current_user.vendor_id)
        else:
            return []
    elif current_user.role == UserRole.SUPERVISOR.value:
        if current_user.department_id:
            query = query.join(PurchaseRequest).filter(PurchaseRequest.department_id == current_user.department_id)
    elif current_user.role == UserRole.EMPLOYEE.value:
        query = query.join(PurchaseRequest).filter(PurchaseRequest.requester_id == current_user.id)

    rfqs = query.order_by(RFQ.issued_at.desc()).all()
    return [build_rfq_out(r) for r in rfqs]

@router.get("/{rfq_id}", response_model=RFQOut)
def get_rfq(rfq_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found.")

    if current_user.role == UserRole.VENDOR.value and rfq.vendor_id != current_user.vendor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access RFQ assigned to another vendor.")

    return build_rfq_out(rfq)

@router.post("/{rfq_id}/quotations", response_model=QuotationOut)
def submit_quotation(
    rfq_id: uuid.UUID,
    quote_in: QuotationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RFQ not found.")

    # Validation: Vendor must own the RFQ
    if current_user.role == UserRole.VENDOR.value and rfq.vendor_id != current_user.vendor_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot submit quote for another vendor's RFQ.")

    # Reject submissions for expired or cancelled RFQs
    if rfq.status in ["RFQ_EXPIRED", "RFQ_CANCELLED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot submit a quotation for an RFQ with status '{rfq.status}'."
        )

    # Check deadline — auto-expire if past due_at
    if rfq.due_at and datetime.utcnow() > rfq.due_at:
        rfq.status = "RFQ_EXPIRED"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The RFQ deadline has passed ({rfq.due_at.strftime('%Y-%m-%d %H:%M UTC')}). This RFQ is now expired and can no longer accept quotations."
        )

    # Enforce: Quotations cannot be modified or revised once submitted
    existing_quote = db.query(Quotation).filter(Quotation.rfq_id == rfq.id).first()
    if existing_quote or rfq.status in ["QUOTED", "QUOTATION_RECEIVED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A quotation has already been submitted for this RFQ. Quotations are final and cannot be modified or revised."
        )

    # Calculate total price
    pr = rfq.purchase_request
    pr_item = pr.items[0] if (pr and pr.items) else None
    qty = float(pr_item.quantity) if pr_item else 1.0
    total_price = quote_in.quoted_unit_price * qty

    quote = Quotation(
        rfq_id=rfq.id,
        vendor_id=rfq.vendor_id,
        quoted_unit_price=quote_in.quoted_unit_price,
        total_price=total_price,
        lead_time_days=quote_in.lead_time_days,
        expected_delivery_date=quote_in.expected_delivery_date,
        validity_period=quote_in.validity_period,
        notes=quote_in.notes
    )
    db.add(quote)

    # Update RFQ status to QUOTATION_RECEIVED
    rfq.status = "QUOTATION_RECEIVED"

    # Update PR status to reflect quotations received
    if pr:
        # Count how many RFQs for this PR now have quotations
        all_rfqs = db.query(RFQ).filter(RFQ.purchase_request_id == pr.id).all()
        # At least 1 received → QUOTATIONS_READY
        if pr.status in [
            PRStatus.RFQS_ISSUED.value,
            PRStatus.AWAITING_QUOTATIONS.value,
            PRStatus.RFQ_ISSUED.value,  # legacy
        ]:
            pr.status = PRStatus.QUOTATIONS_READY.value

    db.commit()
    db.refresh(quote)

    record_audit(
        db, "QUOTATION_SUBMITTED", "QUOTATION", quote.id, current_user.id,
        metadata={"rfq_ref": rfq.reference_number, "total_price": total_price}
    )

    # Notify the department supervisors that a quotation was received
    if pr and pr.department:
        for sup in pr.department.supervisors:
            create_notification(
                db=db,
                user_id=sup.id,
                notif_type="QUOTATION_RECEIVED",
                title=f"Quotation Received: {rfq.reference_number}",
                message=f"{rfq.vendor.name if rfq.vendor else 'Vendor'} submitted a quotation for {pr.reference_number}. Total: ${total_price:,.2f}.",
                related_entity_type="RFQ",
                related_entity_id=rfq.id
            )

    return QuotationOut(
        id=quote.id,
        rfq_id=quote.rfq_id,
        vendor_id=quote.vendor_id,
        vendor_name=rfq.vendor.name if rfq.vendor else "Vendor",
        quoted_unit_price=float(quote.quoted_unit_price),
        total_price=float(quote.total_price),
        lead_time_days=quote.lead_time_days,
        expected_delivery_date=quote.expected_delivery_date,
        validity_period=quote.validity_period,
        notes=quote.notes,
        submitted_at=quote.submitted_at
    )
