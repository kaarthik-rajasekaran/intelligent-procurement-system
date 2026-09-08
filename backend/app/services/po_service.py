import os
import uuid
from datetime import datetime
from typing import Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings
from app.models.entities import (
    PurchaseOrder, PurchaseRequest, Quotation, RFQ, Vendor, PRStatus, User
)
from app.services.notification_service import create_notification, record_audit
from app.services.email_service import email_service

def generate_po_pdf(
    po_number: str,
    pr_ref: str,
    vendor_name: str,
    vendor_email: str,
    item_name: str,
    quantity: float,
    unit: str,
    unit_price: float,
    total_amount: float,
    lead_time_days: int,
    supervisor_name: str,
    generated_at: datetime
) -> str:
    """
    Generates a professional corporate Purchase Order PDF document.
    Saves to storage/purchase_orders/{po_number}.pdf and returns the file path.
    """
    filename = f"{po_number}.pdf"
    filepath = settings.PO_STORAGE_DIR / filename

    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "PoTitle",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "PoSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )
    section_style = ParagraphStyle(
        "PoSection",
        parent=styles["Heading3"],
        fontSize=12,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "PoBody",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#334155"),
        leading=13
    )
    bold_style = ParagraphStyle(
        "PoBold",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        leading=13
    )

    story = []

    # Header
    story.append(Paragraph("OFFICIAL PURCHASE ORDER", title_style))
    story.append(Paragraph(f"Autonomous Procurement Engine • PO #{po_number}", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=15))

    # Meta Table: Order details & Vendor details side-by-side
    order_info = [
        [Paragraph("<b>PO Number:</b>", body_style), Paragraph(po_number, bold_style)],
        [Paragraph("<b>Issue Date:</b>", body_style), Paragraph(generated_at.strftime("%B %d, %Y"), body_style)],
        [Paragraph("<b>PR Reference:</b>", body_style), Paragraph(pr_ref, body_style)],
        [Paragraph("<b>Authorized By:</b>", body_style), Paragraph(f"Supervisor {supervisor_name}", body_style)],
    ]
    vendor_info = [
        [Paragraph("<b>Vendor Name:</b>", body_style), Paragraph(vendor_name, bold_style)],
        [Paragraph("<b>Vendor Email:</b>", body_style), Paragraph(vendor_email, body_style)],
        [Paragraph("<b>Lead Time:</b>", body_style), Paragraph(f"{lead_time_days} business days", body_style)],
        [Paragraph("<b>Fulfillment Status:</b>", body_style), Paragraph("Approved for Immediate Fulfillment", body_style)],
    ]

    meta_table_data = [
        [
            Table(order_info, colWidths=[90, 160]),
            Table(vendor_info, colWidths=[90, 160])
        ]
    ]
    meta_table = Table(meta_table_data, colWidths=[260, 260])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 15))

    # Line Items Section
    story.append(Paragraph("LINE ITEM SPECIFICATION", section_style))
    items_data = [
        ["Item Description", "Qty", "Unit", "Unit Price ($)", "Total Amount ($)"],
        [item_name, f"{quantity:g}", unit, f"${unit_price:,.2f}", f"${total_amount:,.2f}"],
        ["", "", "", "SUBTOTAL:", f"${total_amount:,.2f}"],
        ["", "", "", "TAX (0% B2B):", "$0.00"],
        ["", "", "", "TOTAL AMOUNT:", f"${total_amount:,.2f}"]
    ]
    items_table = Table(items_data, colWidths=[220, 50, 60, 90, 100])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, 1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (2, 2), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (2, 4), (-1, 4), colors.HexColor("#e2e8f0")),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 25))

    # Terms & Signature Block
    story.append(Paragraph("TERMS & CONDITIONS", section_style))
    terms = (
        "1. This Purchase Order constitutes a legally binding agreement in accordance with corporate procurement policies.<br/>"
        "2. Goods must strictly match specified technical and quality parameters.<br/>"
        "3. Invoices must reference the exact PO number above to avoid processing delays."
    )
    story.append(Paragraph(terms, body_style))
    story.append(Spacer(1, 20))

    doc.build(story)
    return str(filepath)

def create_purchase_order_idempotent(
    db: Session,
    purchase_request_id: uuid.UUID,
    actor: User
) -> Tuple[PurchaseOrder, bool]:
    """
    Generates a Purchase Order with strict idempotency.
    If a PO already exists for the given PR, returns the existing PO (created=False).
    Otherwise, generates the PO, builds the PDF, records audit, and notifies stakeholders (created=True).
    """
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == purchase_request_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    # Idempotency check: check if PO already exists
    existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.purchase_request_id == purchase_request_id).first()
    if existing_po:
        return existing_po, False

    # Prerequisite verification: PR must be APPROVED
    if pr.status != PRStatus.APPROVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot generate PO. Purchase Request is in status '{pr.status}', required: '{PRStatus.APPROVED.value}'."
        )

    # Must have a selected vendor decision
    selection = pr.vendor_selection_decision
    selected_vendor_id = selection.selected_vendor_id if selection else pr.selected_vendor_id

    # Must have quotation from the selected vendor
    quote = (
        db.query(Quotation)
        .join(RFQ, Quotation.rfq_id == RFQ.id)
        .filter(RFQ.purchase_request_id == pr.id, Quotation.vendor_id == selected_vendor_id)
        .first()
    )
    if not quote:
        quote = (
            db.query(Quotation)
            .filter(Quotation.vendor_id == selected_vendor_id)
            .first()
        )

    vendor = db.query(Vendor).filter(Vendor.id == selected_vendor_id).first()
    pr_item = pr.items[0] if pr.items else None
    
    qty = float(pr_item.quantity) if pr_item else 1.0
    item_name = pr_item.item.name if (pr_item and pr_item.item) else "Procurement Item"
    item_unit = pr_item.item.unit if (pr_item and pr_item.item) else "units"
    unit_price = float(quote.quoted_unit_price) if quote else 100.0
    total_amount = float(quote.total_price) if quote else (qty * unit_price)
    lead_time = int(quote.lead_time_days) if quote else 7

    po_number = f"PO-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"
    now = datetime.utcnow()

    # Generate PDF
    pdf_path = generate_po_pdf(
        po_number=po_number,
        pr_ref=pr.reference_number,
        vendor_name=vendor.name if vendor else "Selected Vendor",
        vendor_email=vendor.email if vendor else "vendor@example.com",
        item_name=item_name,
        quantity=qty,
        unit=item_unit,
        unit_price=unit_price,
        total_amount=total_amount,
        lead_time_days=lead_time,
        supervisor_name=actor.name,
        generated_at=now
    )

    new_po = PurchaseOrder(
        po_number=po_number,
        purchase_request_id=pr.id,
        vendor_id=selected_vendor_id,
        quotation_id=quote.id if quote else None,
        approved_amount=total_amount,
        status="GENERATED",
        pdf_path=pdf_path,
        generated_at=now
    )
    db.add(new_po)
    
    # Update PR status to PO_GENERATED
    pr.status = PRStatus.PO_GENERATED.value

    db.commit()
    db.refresh(new_po)

    # Audit log
    record_audit(
        db=db,
        action="PO_GENERATED",
        entity_type="PURCHASE_ORDER",
        entity_id=new_po.id,
        actor_id=actor.id,
        metadata={"po_number": po_number, "amount": total_amount}
    )

    # Notify Requester
    create_notification(
        db=db,
        user_id=pr.requester_id,
        notif_type="PO_GENERATED",
        title=f"Purchase Order Generated: {po_number}",
        message=f"Purchase Order {po_number} has been generated for your request {pr.reference_number}.",
        related_entity_type="PURCHASE_ORDER",
        related_entity_id=new_po.id
    )

    # In-app notifications for vendor user(s)
    vendor_users = db.query(User).filter(User.vendor_id == new_po.vendor_id).all()
    for v_user in vendor_users:
        create_notification(
            db=db,
            user_id=v_user.id,
            notif_type="PO_ISSUED",
            title=f"Purchase Order Issued: {po_number}",
            message=f"Official Purchase Order {po_number} has been issued to your company for {pr.reference_number}. Approved Amount: ${total_amount:,.2f}.",
            related_entity_type="PURCHASE_ORDER",
            related_entity_id=new_po.id
        )

    if vendor and vendor.email:
        email_service.send_email(
            to_email=vendor.email,
            subject=f"Purchase Order Issued: {po_number}",
            body=f"Dear {vendor.name},\n\nPlease find attached the official Purchase Order {po_number} for {pr.reference_number}.\n\nTotal Approved: ${total_amount:,.2f}",
            attachment_path=pdf_path
        )

    return new_po, True
