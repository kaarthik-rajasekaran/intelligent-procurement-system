import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_full_procurement_journey_e2e():
    client = TestClient(app, base_url="http://testserver/api/v1")
    # 1. Employee Login
    login_res = client.post("/auth/login", json={"email": "alex.employee@company.com", "password": "password123"})
    assert login_res.status_code == 200
    emp_token = login_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 2. Fetch Catalog & Vendors
    items_res = client.get("/items", headers=emp_headers)
    assert items_res.status_code == 200
    dell_item = next(i for i in items_res.json() if "Dell" in i["name"])

    vendors_res = client.get("/vendors", headers=emp_headers)
    assert vendors_res.status_code == 200
    target_vendor = next((v for v in vendors_res.json() if "Apex" in v["name"]), vendors_res.json()[0])

    # 3. Create Structured Purchase Request (Qty 5)
    create_res = client.post(
        "/purchase-requests",
        headers=emp_headers,
        json={
            "item_id": dell_item["id"],
            "quantity": 5.0,
            "selected_vendor_id": target_vendor["id"],
            "notes": "E2E automated journey test request.",
            "duplicate_acknowledged": True
        }
    )
    assert create_res.status_code == 200
    pr_data = create_res.json()
    pr_id = pr_data["id"]
    pr_ref = pr_data["reference_number"]
    assert pr_data["status"] == "SUBMITTED"
    assert pr_data["inventory_analysis"]["coverage_status"] == "SUFFICIENT"

    # 4. Supervisor Login
    sup_res = client.post("/auth/login", json={"email": "david.supervisor@company.com", "password": "password123"})
    assert sup_res.status_code == 200
    sup_token = sup_res.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # 5. Supervisor Reviews Checking Sheet
    detail_res = client.get(f"/purchase-requests/{pr_id}", headers=sup_headers)
    assert detail_res.status_code == 200
    sheet = detail_res.json()
    assert sheet["reference_number"] == pr_ref

    # 6. Supervisor Issues Multi-Vendor RFQs (curates 1-3 vendors)
    rfq_issue_res = client.post(
        f"/purchase-requests/{pr_id}/issue-rfqs",
        headers=sup_headers,
        json={"vendor_ids": [target_vendor["id"]]}
    )
    assert rfq_issue_res.status_code == 200
    assert rfq_issue_res.json()["status"] in ["AWAITING_QUOTATIONS", "RFQS_ISSUED"]

    # 7. Vendor Login & Submit Quotation with Expected Delivery Date
    vendor_user = client.post("/auth/login", json={"email": "vendor.apex@company.com", "password": "password123"})
    assert vendor_user.status_code == 200
    vendor_token = vendor_user.json()["access_token"]
    vendor_headers = {"Authorization": f"Bearer {vendor_token}"}

    rfqs_res = client.get("/rfqs", headers=vendor_headers)
    assert rfqs_res.status_code == 200
    matching_rfq = next((r for r in rfqs_res.json() if r["purchase_request_id"] == pr_id), None)
    assert matching_rfq is not None

    quote_res = client.post(
        f"/rfqs/{matching_rfq['id']}/quotations",
        headers=vendor_headers,
        json={
            "quoted_unit_price": 2400.0,
            "lead_time_days": 5,
            "expected_delivery_date": "2026-09-15",
            "validity_period": "30 Days",
            "notes": "E2E official competitive quotation with delivery date."
        }
    )
    assert quote_res.status_code == 200
    assert quote_res.json()["total_price"] == 12000.0
    assert quote_res.json()["expected_delivery_date"] == "2026-09-15"

    # 8. Supervisor Reviews Quotation Analysis & Selects Vendor
    qa_res = client.get(f"/purchase-requests/{pr_id}/quotation-analysis", headers=sup_headers)
    assert qa_res.status_code == 200
    qa_data = qa_res.json()
    assert len(qa_data["evaluations"]) >= 1

    select_res = client.post(
        f"/purchase-requests/{pr_id}/vendor-selection",
        headers=sup_headers,
        json={"selected_vendor_id": target_vendor["id"]}
    )
    assert select_res.status_code == 200

    # 9. Supervisor Grants Final Approval
    final_app_res = client.post(f"/purchase-requests/{pr_id}/final-approval", headers=sup_headers)
    assert final_app_res.status_code == 200
    assert final_app_res.json()["status"] == "APPROVED"

    # 10. Purchase Order Generation (First Attempt)
    po_res1 = client.post(f"/purchase-requests/{pr_id}/purchase-order", headers=sup_headers)
    assert po_res1.status_code == 200
    po_data1 = po_res1.json()
    assert po_data1["po_number"].startswith("PO-")
    assert po_data1["approved_amount"] > 0

    # Verify PDF is downloadable
    pdf_res = client.get(f"/purchase-orders/{po_data1['id']}/pdf", headers=sup_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 1000

    # 11. Idempotency Check (Second Attempt)
    po_res2 = client.post(f"/purchase-requests/{pr_id}/purchase-order", headers=sup_headers)
    assert po_res2.status_code == 200
    po_data2 = po_res2.json()
    assert po_data2["id"] == po_data1["id"]
    assert po_data2["po_number"] == po_data1["po_number"]

    # 12. Policy RAG Query Test
    rag_res = client.post(
        "/knowledge/query",
        json={"query": "What is the policy threshold for purchases requiring multi-vendor RFQ?"}
    )
    assert rag_res.status_code == 200
    assert len(rag_res.json()["grounded_chunks"]) > 0
    assert "5,000" in rag_res.json()["answer"] or "policy" in rag_res.json()["answer"].lower()

    # 13. AI PR Summary Test
    summary_res = client.post(f"/ai/summarize/pr/{pr_id}", headers=sup_headers)
    assert summary_res.status_code == 200
    assert "summary" in summary_res.json()
