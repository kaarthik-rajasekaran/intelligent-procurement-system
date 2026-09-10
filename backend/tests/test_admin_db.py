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

    # 2. Get DB Stats
    stats_res = client.get("/admin/db/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_tables" in stats
    assert stats["total_tables"] >= 15
    assert "SQLite 3" in stats["database_type"]

    # 3. List all tables
    tables_res = client.get("/admin/db/tables", headers=headers)
    assert tables_res.status_code == 200
    tables = tables_res.json()
    assert len(tables) >= 15
    table_names = [t["name"] for t in tables]
    assert "inventory" in table_names
    assert "items" in table_names
    assert "vendors" in table_names
    assert "purchase_requests" in table_names

    # 4. Get table records for inventory
    inv_res = client.get("/admin/db/table/inventory", headers=headers)
    assert inv_res.status_code == 200
    inv_data = inv_res.json()
    assert inv_data["table"] == "inventory"
    assert len(inv_data["rows"]) > 0
    assert "columns" in inv_data
    assert "foreign_keys" in inv_data

    # 5. Get Relationships graph
    rel_res = client.get("/admin/db/relationships", headers=headers)
    assert rel_res.status_code == 200
    rel_data = rel_res.json()
    assert "nodes" in rel_data
    assert "edges" in rel_data
    assert len(rel_data["nodes"]) >= 15

