import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_revision_and_resubmit_workflow():
    client = TestClient(app, base_url="http://testserver/api/v1")

    # 1. Login as supervisor
    sup_login = client.post("/auth/login", json={"email": "david.supervisor@company.com", "password": "password123"})
    assert sup_login.status_code == 200
    sup_token = sup_login.json()["access_token"]
    sup_headers = {"Authorization": f"Bearer {sup_token}"}

    # 2. Login as employee
    emp_login = client.post("/auth/login", json={"email": "alex.employee@company.com", "password": "password123"})
    assert emp_login.status_code == 200
    emp_token = emp_login.json()["access_token"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 3. Employee creates a PR
    items_res = client.get("/items", headers=emp_headers)
    assert items_res.status_code == 200
    items = items_res.json()
    item_id = items[0]["id"]

    vendors_res = client.get("/vendors", headers=emp_headers)
    assert vendors_res.status_code == 200
    vendors = vendors_res.json()
    vendor_id = vendors[0]["id"]

    create_payload = {
        "item_id": item_id,
        "quantity": 10.0,
        "selected_vendor_id": vendor_id,
        "notes": "Initial requisition for project",
        "duplicate_acknowledged": True
    }
    pr_res = client.post("/purchase-requests", json=create_payload, headers=emp_headers)
    assert pr_res.status_code == 200
    pr = pr_res.json()
    pr_id = pr["id"]
    assert pr["status"] == "SUBMITTED"

    # 4. Supervisor reviews and returns PR for revision
    return_res = client.post(
        f"/purchase-requests/{pr_id}/return",
        json={"reason": "Please reduce quantity to 4 units due to budget constraints."},
        headers=sup_headers
    )
    assert return_res.status_code == 200
    pr_returned = return_res.json()
    assert pr_returned["status"] == "REVISION_REQUIRED"
    assert len(pr_returned["reviews"]) > 0
    assert pr_returned["reviews"][-1]["decision"] in ["RETURNED", "RETURNED_FOR_REVISION"]
    assert "budget constraints" in pr_returned["reviews"][-1]["reason"]

    # 5. Employee resubmits PR with revised quantity and explanation note
    other_vendor_id = vendors[1]["id"] if len(vendors) > 1 else vendor_id
    resubmit_payload = {
        "quantity": 4.0,
        "selected_vendor_id": other_vendor_id,
        "notes": "Adjusted quantity to 4 units as requested by supervisor."
    }
    resubmit_res = client.post(
        f"/purchase-requests/{pr_id}/resubmit",
        json=resubmit_payload,
        headers=emp_headers
    )
    assert resubmit_res.status_code == 200
    pr_resubmitted = resubmit_res.json()
    assert pr_resubmitted["status"] == "SUBMITTED"
    assert pr_resubmitted["quantity"] == 4.0
    assert pr_resubmitted["notes"] == "Adjusted quantity to 4 units as requested by supervisor."
    assert pr_resubmitted["selected_vendor_id"] == other_vendor_id

    # 6. Verify supervisor received a resubmission notification
    notifs_res = client.get("/notifications", headers=sup_headers)
    assert notifs_res.status_code == 200
    notifs = notifs_res.json()
    resubmit_notifs = [n for n in notifs if n["type"] == "PR_RESUBMITTED"]
    assert len(resubmit_notifs) > 0
    assert pr_resubmitted["reference_number"] in resubmit_notifs[0]["title"]
