import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import uuid
from datetime import datetime
from app.core.database import engine, Base, SessionLocal
from app.models.entities import (
    User, Item, Department, Vendor, PurchaseRequest, PurchaseRequestItem,
    PRStatus, Inventory, HistoricalPrice, PurchaseOrder, RFQ, Quotation
)
from app.services.seed_data import seed_database
from app.intelligence.deterministic import analyze_inventory, detect_duplicate_requests
from app.intelligence.analytical import (
    compute_vendor_badges, get_vendor_recommendations, evaluate_quotations
)
from app.services.workflow import transition_pr_status, validate_supervisor_authority
from app.services.po_service import create_purchase_order_idempotent
from fastapi import HTTPException

@pytest.fixture(scope="module")
def db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    seed_database(session)
    yield session
    session.close()

def test_inventory_analysis(db):
    item = db.query(Item).filter(Item.name.like("%Dell%")).first()
    assert item is not None

    # Test sufficient inventory (Dell has 45 in stock)
    res_sufficient = analyze_inventory(db, item.id, requested_quantity=10.0)
    assert res_sufficient.coverage_status == "SUFFICIENT"
    assert res_sufficient.shortage_quantity == 0.0

    # Test insufficient inventory
    res_insufficient = analyze_inventory(db, item.id, requested_quantity=100.0)
    assert res_insufficient.coverage_status == "INSUFFICIENT"
    assert res_insufficient.shortage_quantity == 55.0

def test_duplicate_pr_detection_20_percent_rule(db):
    dept = db.query(Department).filter(Department.name == "Information Technology").first()
    item = db.query(Item).filter(Item.name.like("%Dell%")).first()
    emp = db.query(User).filter(User.email == "alex.employee@company.com").first()
    vendor = db.query(Vendor).first()
    assert dept is not None and item is not None and emp is not None and vendor is not None

    # Ensure reference PR exists for test
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.reference_number == "PR-2026-000101").first()
    if not pr:
        pr = PurchaseRequest(
            reference_number="PR-2026-000101",
            requester_id=emp.id,
            department_id=dept.id,
            selected_vendor_id=vendor.id,
            status=PRStatus.UNDER_REVIEW.value,
            duplicate_acknowledged=False
        )
        db.add(pr)
        db.commit()
        pr_item = PurchaseRequestItem(
            purchase_request_id=pr.id,
            item_id=item.id,
            quantity=10.0
        )
        db.add(pr_item)
        db.commit()

    # 1. Quantity = 11 units -> abs(10-11)/max(10,11)*100 = 1/11*100 = 9.09% <= 20% -> MATCH!
    matches = detect_duplicate_requests(db, item.id, dept.id, requested_quantity=11.0)
    assert len(matches) >= 1
    assert any(m.reference_number == "PR-2026-000101" for m in matches)

    # 2. Quantity = 25 units -> abs(10-25)/25*100 = 60% > 20% -> NO MATCH!
    matches_far = detect_duplicate_requests(db, item.id, dept.id, requested_quantity=25.0)
    assert not any(m.reference_number == "PR-2026-000101" for m in matches_far)

def test_analytical_vendor_recommendations(db):
    item = db.query(Item).filter(Item.name.like("%Dell%")).first()
    recs = get_vendor_recommendations(db, item.id)
    assert len(recs) >= 3

    # Check ranked order and scores
    assert recs[0].rank == 1
    assert recs[0].overall_score >= recs[1].overall_score

def test_workflow_state_machine(db):
    emp = db.query(User).filter(User.email == "alex.employee@company.com").first()
    sup = db.query(User).filter(User.email == "david.supervisor@company.com").first()
    dept = db.query(Department).filter(Department.name == "Information Technology").first()
    vendor = db.query(Vendor).first()
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.reference_number == "PR-2026-000101").first()
    if not pr:
        pr = PurchaseRequest(
            reference_number="PR-2026-000101",
            requester_id=emp.id,
            department_id=dept.id,
            selected_vendor_id=vendor.id,
            status=PRStatus.UNDER_REVIEW.value,
            duplicate_acknowledged=False
        )
        db.add(pr)
        db.commit()

    # Invalid jump: Cannot go from UNDER_REVIEW straight to PO_GENERATED
    with pytest.raises(HTTPException) as excinfo:
        transition_pr_status(db, pr, PRStatus.PO_GENERATED, actor=sup)
    assert excinfo.value.status_code == 400

    # Returning requires mandatory reason
    with pytest.raises(HTTPException) as excinfo:
        transition_pr_status(db, pr, PRStatus.REVISION_REQUIRED, actor=sup, reason="")
    assert excinfo.value.status_code == 400

def test_quotation_evaluation_and_idempotent_po(db):
    dept = db.query(Department).filter(Department.name == "Information Technology").first()
    item = db.query(Item).filter(Item.name.like("%Dell%")).first()
    emp = db.query(User).filter(User.email == "alex.employee@company.com").first()
    sup = db.query(User).filter(User.email == "david.supervisor@company.com").first()
    vendors = db.query(Vendor).all()

    pr = db.query(PurchaseRequest).filter(PurchaseRequest.reference_number == "PR-2026-000103").first()
    if not pr:
        pr = PurchaseRequest(
            reference_number="PR-2026-000103",
            requester_id=emp.id,
            department_id=dept.id,
            status=PRStatus.QUOTATION_RECEIVED.value,
            selected_vendor_id=vendors[0].id,
            duplicate_acknowledged=False
        )
        db.add(pr)
        db.commit()
        db.add(PurchaseRequestItem(purchase_request_id=pr.id, item_id=item.id, quantity=5.0))
        db.commit()

    quotes = db.query(Quotation).join(RFQ).filter(RFQ.purchase_request_id == pr.id).all()
    if not quotes:
        for v in vendors[:3]:
            rfq = RFQ(
                reference_number=f"RFQ-TEST-{v.name[:4].upper()}-{str(uuid.uuid4())[:4]}",
                purchase_request_id=pr.id,
                vendor_id=v.id,
                status="QUOTED"
            )
            db.add(rfq)
            db.commit()
            q = Quotation(
                rfq_id=rfq.id,
                vendor_id=v.id,
                quoted_unit_price=2000.0,
                lead_time_days=5,
                total_price=10000.0
            )
            db.add(q)
            db.commit()

    analysis = evaluate_quotations(db, pr.id)
    assert len(analysis.evaluations) >= 1
    assert analysis.recommended_vendor_id is not None
    assert analysis.evaluations[0].is_recommended == True

    # Test final approval & PO generation
    pr.status = PRStatus.APPROVED.value
    db.commit()

    # Clean up existing PO for this PR if left over from earlier runs
    existing = db.query(PurchaseOrder).filter(PurchaseOrder.purchase_request_id == pr.id).first()
    if existing:
        db.delete(existing)
        db.commit()

    # 1. Generate PO first time
    po1, created1 = create_purchase_order_idempotent(db, pr.id, sup)
    assert created1 is True
    assert po1.po_number.startswith("PO-")
    assert os.path.exists(po1.pdf_path)

    # 2. Generate PO second time (idempotency check)
    po2, created2 = create_purchase_order_idempotent(db, pr.id, sup)
    assert created2 is False
    assert po2.id == po1.id
    assert po2.po_number == po1.po_number
