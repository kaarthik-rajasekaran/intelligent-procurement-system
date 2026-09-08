import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from app.main import app

def test_multivendor_rfq_and_delivery_date_scoring():
    client = TestClient(app, base_url="http://testserver/api/v1")

    # 1. Login as Employee
    emp_res = client.post("/auth/login", json={"email": "alex.employee@company.com", "password": "password123"})
    assert emp_res.status_code == 200
    emp_token = emp_res.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 2. Get Items & Vendors
    items = client.get("/items", headers=emp_headers).json()
    dell_item = next(i for i in items if "Dell" in i["name"])
    vendors = client.get("/vendors", headers=emp_headers).json()
    assert len(vendors) >= 3

    # 3. Create PR
    pr_res = client.post(
        "/purchase-requests",
        headers=emp_headers,
        json={
            "item_id": dell_item["id"],
            "quantity": 10.0,
            "selected_vendor_id": vendors[0]["id"],
            "notes": "Testing multi-vendor RFQ workflow with delivery date.",
            "duplicate_acknowledged": True
        }
    )
    assert pr_res.status_code == 200
    pr_id = pr_res.json()["id"]

    # 4. Login as Supervisor
    sup_res = client.post("/auth/login", json={"email": "david.supervisor@company.com", "password": "password123"})
    assert sup_res.status_code == 200
    sup_token = sup_res.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # 5. Issue RFQs to 2 vendors
    invited_vendors = [vendors[0]["id"], vendors[1]["id"]]
    deadline = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    issue_res = client.post(
        f"/purchase-requests/{pr_id}/issue-rfqs",
        headers=sup_headers,
        json={"vendor_ids": invited_vendors, "due_date": f"{deadline}T23:59:59"}
    )
    assert issue_res.status_code == 200
    assert issue_res.json()["status"] == "AWAITING_QUOTATIONS"

    # 6. Verify RFQs were created for the 2 vendors
    all_rfqs = client.get("/rfqs", headers=sup_headers).json()
    my_rfqs = [r for r in all_rfqs if r["purchase_request_id"] == pr_id]
    assert len(my_rfqs) == 2

    # 7. Simulate quotes for this PR
    sim_res = client.post(f"/purchase-requests/{pr_id}/simulate-bids", headers=sup_headers)
    assert sim_res.status_code == 200
    qa = sim_res.json()
    assert len(qa["evaluations"]) >= 2

    # Verify each evaluation has expected_delivery_date and delivery_date_score
    for eval_item in qa["evaluations"]:
        assert eval_item["expected_delivery_date"] is not None
        assert eval_item["delivery_date_score"] is not None
        assert eval_item["final_weighted_score"] > 0

    # 8. Supervisor selects winning vendor
    best_vendor_id = qa["recommended_vendor_id"]
    select_res = client.post(
        f"/purchase-requests/{pr_id}/vendor-selection",
        headers=sup_headers,
        json={"selected_vendor_id": best_vendor_id}
    )
    assert select_res.status_code == 200

    # 9. Final Approval & PO Generation
    app_res = client.post(f"/purchase-requests/{pr_id}/final-approval", headers=sup_headers)
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVED"

    po_res = client.post(f"/purchase-requests/{pr_id}/purchase-order", headers=sup_headers)
    assert po_res.status_code == 200
    po = po_res.json()
    assert po["po_number"].startswith("PO-")
    assert po["status"] == "GENERATED"
