from typing import List, Dict, Any, Optional
import sqlite3
import uuid
import json
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db, engine
from app.core.config import settings
from app.api.deps import get_current_user

router = APIRouter(prefix="/admin/db", tags=["Admin Database Management"])

# Whitelist of manageable tables
ALLOWED_TABLES = [
    "inventory",
    "items",
    "vendors",
    "vendor_performance",
    "vendor_item_performance",
    "vendor_reviews",
    "vendor_badges",
    "purchase_requests",
    "purchase_request_items",
    "rfqs",
    "quotations",
    "purchase_orders",
    "users",
    "departments",
    "historical_prices",
    "pr_recommendation_snapshots",
    "notifications",
    "audit_logs",
    "knowledge_documents",
    "knowledge_chunks"
]

class SqlQueryRequest(BaseModel):
    query: str

class UpdateRowRequest(BaseModel):
    data: Dict[str, Any]

class CreateRowRequest(BaseModel):
    data: Dict[str, Any]

def get_sqlite_conn():
    conn = sqlite3.connect(settings.DATABASE_URL.replace("sqlite:///", ""))
    conn.row_factory = sqlite3.Row
    return conn

@router.get("/tables")
def list_tables(current_user=Depends(get_current_user)):
    """
    Returns list of all manageable tables with row counts and column definitions.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        tables_info = []
        for table in ALLOWED_TABLES:
            try:
                # Get row count
                cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                row_count = cursor.fetchone()["count"]

                # Get table info (columns, types, pk)
                cursor.execute(f"PRAGMA table_info({table})")
                cols = cursor.fetchall()
                columns = [
                    {
                        "cid": col["cid"],
                        "name": col["name"],
                        "type": col["type"],
                        "notnull": bool(col["notnull"]),
                        "dflt_value": col["dflt_value"],
                        "pk": bool(col["pk"])
                    }
                    for col in cols
                ]

                tables_info.append({
                    "name": table,
                    "row_count": row_count,
                    "columns": columns,
                    "primary_key": next((c["name"] for c in columns if c["pk"]), "id")
                })
            except Exception:
                continue
        return tables_info
    finally:
        conn.close()

@router.get("/tables/{table_name}")
def get_table_data(
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    search: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """
    Returns records from a specific table with column metadata.
    """
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' is not in allowed management list.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # Get schema columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        columns = [
            {
                "name": col["name"],
                "type": col["type"],
                "pk": bool(col["pk"])
            }
            for col in cols
        ]

        # Build query
        query = f"SELECT * FROM {table_name}"
        params = []
        if search and search.strip():
            # Search across all text columns
            text_cols = [c["name"] for c in columns if "CHAR" in c["type"].upper() or "TEXT" in c["type"].upper()]
            if text_cols:
                clause = " OR ".join([f"{c} LIKE ?" for c in text_cols])
                query += f" WHERE {clause}"
                params = [f"%{search.strip()}%"] * len(text_cols)

        query += f" LIMIT {limit} OFFSET {offset}"
        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Total count
        count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        cursor.execute(count_query)
        total_count = cursor.fetchone()["cnt"]

        records = []
        for r in rows:
            record = {}
            for col in columns:
                val = r[col["name"]]
                record[col["name"]] = val
            records.append(record)

        return {
            "table_name": table_name,
            "columns": columns,
            "primary_key": next((c["name"] for c in columns if c["pk"]), "id"),
            "total_count": total_count,
            "records": records
        }
    finally:
        conn.close()

@router.put("/tables/{table_name}/{row_id}")
def update_table_row(
    table_name: str,
    row_id: str,
    req: UpdateRowRequest,
    current_user=Depends(get_current_user)
):
    """
    Updates one or more columns for a specific row in the database.
    """
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' is not manageable.")

    if not req.data:
        raise HTTPException(status_code=400, detail="No data provided to update.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # Determine PK
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        pk_col = next((col["name"] for col in cols if col["pk"]), "id")

        set_clauses = []
        values = []
        for k, v in req.data.items():
            if k != pk_col:
                set_clauses.append(f"{k} = ?")
                values.append(v)

        if not set_clauses:
            raise HTTPException(status_code=400, detail="No valid updatable columns provided.")

        values.append(row_id)
        update_sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {pk_col} = ?"
        cursor.execute(update_sql, values)
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Record with {pk_col}={row_id} not found in {table_name}.")

        # Return the updated row
        cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_col} = ?", (row_id,))
        updated_row = cursor.fetchone()
        return dict(updated_row) if updated_row else {"success": True}
    finally:
        conn.close()

@router.post("/tables/{table_name}")
def create_table_row(
    table_name: str,
    req: CreateRowRequest,
    current_user=Depends(get_current_user)
):
    """
    Inserts a new record into any table.
    """
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' is not manageable.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # Check if ID needs auto-generating (UUID)
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        pk_col = next((col["name"] for col in cols if col["pk"]), "id")

        data = dict(req.data)
        if pk_col in [c["name"] for c in cols] and (pk_col not in data or not data[pk_col]):
            # Auto-generate UUID string
            data[pk_col] = str(uuid.uuid4())

        columns = list(data.keys())
        placeholders = ["?"] * len(columns)
        values = list(data.values())

        insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        cursor.execute(insert_sql, values)
        conn.commit()

        pk_val = data[pk_col]
        cursor.execute(f"SELECT * FROM {table_name} WHERE {pk_col} = ?", (pk_val,))
        created_row = cursor.fetchone()
        return dict(created_row) if created_row else {"id": pk_val, "success": True}
    finally:
        conn.close()

@router.delete("/tables/{table_name}/{row_id}")
def delete_table_row(
    table_name: str,
    row_id: str,
    current_user=Depends(get_current_user)
):
    """
    Deletes a specific row from the database.
    """
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail=f"Table '{table_name}' is not manageable.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        cols = cursor.fetchall()
        pk_col = next((col["name"] for col in cols if col["pk"]), "id")

        cursor.execute(f"DELETE FROM {table_name} WHERE {pk_col} = ?", (row_id,))
        conn.commit()

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Record not found.")

        return {"message": f"Successfully deleted record from {table_name} where {pk_col}={row_id}"}
    finally:
        conn.close()

@router.post("/execute-sql")
def execute_raw_sql(
    req: SqlQueryRequest,
    current_user=Depends(get_current_user)
):
    """
    Executes a custom SQL query and returns results or rowcount.
    """
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        is_select = query.upper().startswith("SELECT") or query.upper().startswith("PRAGMA")

        if is_select:
            rows = cursor.fetchall()
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
            else:
                columns = []

            results = [dict(r) for r in rows]
            return {
                "type": "SELECT",
                "columns": columns,
                "row_count": len(results),
                "results": results
            }
        else:
            conn.commit()
            return {
                "type": "MUTATION",
                "affected_rows": cursor.rowcount,
                "message": f"Query executed successfully. {cursor.rowcount} row(s) affected."
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL Execution Error: {str(e)}")
    finally:
        conn.close()
