import os
from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_token
from app.models.entities import PurchaseOrder, PurchaseRequest, User, UserRole
from app.schemas.domain import PurchaseOrderOut
from app.services.po_service import create_purchase_order_idempotent
from app.api.deps import get_current_user, get_optional_current_user, require_role

router = APIRouter(tags=["Purchase Orders"])

def build_po_out(po: PurchaseOrder) -> PurchaseOrderOut:
    pr = po.purchase_request
    pr_item = pr.items[0] if (pr and pr.items) else None
    vendor = po.vendor
    return PurchaseOrderOut(
        id=po.id,
        po_number=po.po_number,
        purchase_request_id=po.purchase_request_id,
        pr_reference=pr.reference_number if pr else "N/A",
        vendor_id=po.vendor_id,
        vendor_name=vendor.name if vendor else "Vendor",
        vendor_email=vendor.email if vendor else "",
        item_name=pr_item.item.name if (pr_item and pr_item.item) else "Item",
        quantity=float(pr_item.quantity) if pr_item else 1.0,
        item_unit=pr_item.item.unit if (pr_item and pr_item.item) else "units",
        unit_price=round(float(po.approved_amount) / float(pr_item.quantity), 2) if (pr_item and float(pr_item.quantity) > 0) else float(po.approved_amount),
        approved_amount=float(po.approved_amount),
        status=po.status,
        pdf_url=f"/api/v1/purchase-orders/{po.id}/pdf" if po.pdf_path else None,
        generated_at=po.generated_at
    )

@router.post("/purchase-requests/{pr_id}/purchase-order", response_model=PurchaseOrderOut)
def generate_purchase_order(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(require_role([UserRole.SUPERVISOR.value, UserRole.ADMIN.value]))
):
    po, created = create_purchase_order_idempotent(db, pr_id, current_user)
    return build_po_out(po)

@router.get("/purchase-orders", response_model=List[PurchaseOrderOut])
def list_purchase_orders(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    query = db.query(PurchaseOrder)
    if current_user.role == UserRole.VENDOR.value:
        query = query.filter(PurchaseOrder.vendor_id == current_user.vendor_id)
    elif current_user.role == UserRole.EMPLOYEE.value:
        query = query.join(PurchaseRequest).filter(PurchaseRequest.requester_id == current_user.id)

    pos = query.order_by(PurchaseOrder.generated_at.desc()).all()
    return [build_po_out(p) for p in pos]

@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderOut)
def get_purchase_order(po_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order not found.")
    return build_po_out(po)

@router.get("/purchase-orders/{po_id}/pdf")
def download_po_pdf(
    po_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
    token: Optional[str] = Query(default=None, description="JWT token for browser-direct downloads")
):
    # Support token as query param for browser direct URL opens (no Authorization header)
    if not current_user and token:
        from app.models.entities import User as UserModel
        payload = decode_token(token)
        if payload:
            user_id = payload.get("sub")
            current_user = db.query(UserModel).filter(UserModel.id == user_id).first()

    if not current_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated.")

    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po or not po.pdf_path or not os.path.exists(po.pdf_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Order PDF not found on disk.")

    return FileResponse(
        path=po.pdf_path,
        filename=f"{po.po_number}.pdf",
        media_type="application/pdf"
    )
