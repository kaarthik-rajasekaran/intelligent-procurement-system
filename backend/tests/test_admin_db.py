import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_admin_db_endpoints():
    client = TestClient(app, base_url="http://testserver/api/v1")

    # 1. Login as Admin
    admin_res = client.post("/auth/login", json={"email": "admin@company.com", "password": "password123"})
    assert admin_res.status_code == 200
    token = admin_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. List all tables
    tables_res = client.get("/admin/db/tables", headers=headers)
    assert tables_res.status_code == 200
    tables = tables_res.json()
    assert len(tables) >= 10
    table_names = [t["name"] for t in tables]
    assert "inventory" in table_names
    assert "items" in table_names
    assert "vendors" in table_names

    # 3. Get table records for inventory
    inv_res = client.get("/admin/db/tables/inventory", headers=headers)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["table_name"] == "inventory"
    assert len(inv_data["records"]) > 0
    first_record = inv_data["records"][0]
    pk_val = first_record["id"]

    # 4. Update in-place (e.g. available_quantity)
    new_qty = 88.0
    update_res = client.put(
        f"/admin/db/tables/inventory/{pk_val}",
        headers=headers,
        json={"data": {"available_quantity": new_qty}}
    )
    assert update_res.status_code == 200
    assert float(update_res.json()["available_quantity"]) == new_qty

    # 5. Verify live inventory endpoint immediately reflects the updated value
    item_id = first_record["item_id"]
    check_res = client.get(f"/inventory/items/{item_id}?quantity=50", headers=headers)
    assert check_res.status_code == 200
    assert check_res.json()["available_quantity"] == new_qty
    assert check_res.json()["coverage_status"] == "SUFFICIENT"

    # 6. Execute Raw SQL (SELECT & UPDATE)
    sql_select = client.post(
        "/admin/db/execute-sql",
        headers=headers,
        json={"query": "SELECT count(*) as count FROM items;"}
    )
    assert sql_select.status_code == 200
    assert sql_select.json()["type"] == "SELECT"
    assert sql_select.json()["row_count"] == 1

    orig_qty = float(first_record.get("available_quantity", 10.0))
    sql_update = client.post(
        "/admin/db/execute-sql",
        headers=headers,
        json={"query": f"UPDATE inventory SET available_quantity = {orig_qty} WHERE id = '{pk_val}';"}
    )
    assert sql_update.status_code == 200
    assert sql_update.json()["type"] == "MUTATION"
    assert sql_update.json()["affected_rows"] == 1

