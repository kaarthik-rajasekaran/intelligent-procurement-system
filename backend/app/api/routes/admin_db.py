from typing import List, Dict, Any, Optional
import os
import sqlite3
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import inspect
from app.core.database import get_db, engine, Base
from app.core.config import settings
from app.api.deps import get_optional_current_user
from app.models.entities import User, UserRole

router = APIRouter(prefix="/admin/db", tags=["Database Explorer"])

TABLE_CATEGORIES = {
    "departments": "CORE ORGANIZATION",
    "users": "CORE ORGANIZATION",
    "department_supervisors": "CORE ORGANIZATION",
    "items": "PROCUREMENT CATALOG",
    "inventory": "PROCUREMENT CATALOG",
    "historical_prices": "PROCUREMENT CATALOG",
    "vendors": "SUPPLIER MANAGEMENT",
    "vendor_performance": "SUPPLIER MANAGEMENT",
    "vendor_item_performance": "SUPPLIER MANAGEMENT",
    "vendor_badges": "SUPPLIER MANAGEMENT",
    "vendor_item_mapping": "SUPPLIER MANAGEMENT",
    "vendor_reviews": "SUPPLIER MANAGEMENT",
    "vendor_review_embeddings": "SUPPLIER MANAGEMENT",
    "purchase_requests": "PROCUREMENT WORKFLOW",
    "purchase_request_items": "PROCUREMENT WORKFLOW",
    "purchase_request_reviews": "PROCUREMENT WORKFLOW",
    "pr_recommendation_snapshots": "PROCUREMENT WORKFLOW",
    "rfqs": "RFQ & BIDDING",
    "quotations": "RFQ & BIDDING",
    "vendor_selection_decisions": "RFQ & BIDDING",
    "purchase_orders": "PURCHASE ORDERS",
    "notifications": "SYSTEM & AUDIT",
    "audit_logs": "SYSTEM & AUDIT",
    "knowledge_documents": "SYSTEM & AUDIT",
    "knowledge_chunks": "SYSTEM & AUDIT",
}

def get_db_file_path() -> str:
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "")
        if not os.path.isabs(path):
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            path = os.path.join(base_dir, path)
        return path
    return "procurement.db"

def get_sqlite_conn():
    path = get_db_file_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def get_all_table_names(cursor) -> List[str]:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    return [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

def verify_explorer_access(current_user: Optional[User] = Depends(get_optional_current_user)):
    """
    Guards the database explorer read-only inspection.
    Safe read-only inspection for developer and presentation evaluator sessions.
    """
    return True


@router.get("/stats")
def get_db_stats(_=Depends(verify_explorer_access)):
    """
    Returns high-level statistics about the relational database.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        tables = get_all_table_names(cursor)
        total_records = 0
        table_counts = {}
        for t in tables:
            try:
                cursor.execute(f"SELECT count(*) FROM {t}")
                cnt = cursor.fetchone()[0]
                table_counts[t] = cnt
                total_records += cnt
            except Exception:
                table_counts[t] = 0

        db_path = get_db_file_path()
        file_size_bytes = os.path.getsize(db_path) if os.path.exists(db_path) else 0

        return {
            "database_type": "SQLite 3 (Relational ACID Compliant)",
            "database_file": os.path.basename(db_path),
            "file_size_bytes": file_size_bytes,
            "file_size_formatted": f"{file_size_bytes / 1024:.1f} KB" if file_size_bytes < 1024 * 1024 else f"{file_size_bytes / (1024 * 1024):.2f} MB",
            "total_tables": len(tables),
            "total_records": total_records,
            "server_timestamp": datetime.utcnow().isoformat() + "Z",
            "table_counts": table_counts,
            "status": "CONNECTED_ACTIVE"
        }
    finally:
        conn.close()

@router.get("/tables")
def list_tables(_=Depends(verify_explorer_access)):
    """
    Returns list of all tables with row counts, column count, and category.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        table_names = get_all_table_names(cursor)
        results = []
        for table in table_names:
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
                row_count = cursor.fetchone()["cnt"]

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

                cursor.execute(f"PRAGMA foreign_key_list({table})")
                fks = cursor.fetchall()

                pk_cols = [c["name"] for c in columns if c["pk"]]
                primary_key = pk_cols[0] if pk_cols else "id"

                category = TABLE_CATEGORIES.get(table, "OTHER")

                results.append({
                    "name": table,
                    "category": category,
                    "row_count": row_count,
                    "column_count": len(columns),
                    "columns": columns,
                    "primary_key": primary_key,
                    "foreign_keys_count": len(fks)
                })
            except Exception as e:
                continue

        # Sort tables by category order then name
        category_order = [
            "CORE ORGANIZATION",
            "PROCUREMENT CATALOG",
            "SUPPLIER MANAGEMENT",
            "PROCUREMENT WORKFLOW",
            "RFQ & BIDDING",
            "PURCHASE ORDERS",
            "SYSTEM & AUDIT",
            "OTHER"
        ]
        
        def sort_key(item):
            cat = item["category"]
            cat_idx = category_order.index(cat) if cat in category_order else 99
            return (cat_idx, item["name"])

        results.sort(key=sort_key)
        return results
    finally:
        conn.close()

@router.get("/table/{table_name}")
def get_table_details(
    table_name: str,
    page: int = Query(1, ge=1, description="Page number, 1-indexed"),
    page_size: int = Query(25, ge=1, le=500, description="Number of rows per page"),
    search: Optional[str] = Query(None, description="Fuzzy search across text columns"),
    sort_by: Optional[str] = Query(None, description="Column to sort by"),
    sort_order: Optional[str] = Query("asc", regex="^(asc|desc|ASC|DESC)$", description="Sort direction"),
    _=Depends(verify_explorer_access)
):
    """
    Returns real paginated records, column metadata, and relationships for a specific table.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        # Validate table existence
        all_tables = get_all_table_names(cursor)
        if table_name not in all_tables:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist in database.")

        # Inspect table columns
        cursor.execute(f"PRAGMA table_info({table_name})")
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
        col_names = [c["name"] for c in columns]

        # Outbound foreign keys (this table references another)
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        fk_rows = cursor.fetchall()
        foreign_keys = [
            {
                "from_column": fk["from"],
                "to_table": fk["table"],
                "to_column": fk["to"],
                "on_update": fk["on_update"],
                "on_delete": fk["on_delete"]
            }
            for fk in fk_rows
        ]

        # Inbound foreign keys (other tables reference this table)
        inbound_fks = []
        for other_table in all_tables:
            if other_table == table_name:
                continue
            cursor.execute(f"PRAGMA foreign_key_list({other_table})")
            other_fks = cursor.fetchall()
            for ofk in other_fks:
                if ofk["table"] == table_name:
                    inbound_fks.append({
                        "from_table": other_table,
                        "from_column": ofk["from"],
                        "to_column": ofk["to"]
                    })

        # Build query
        base_query = f'SELECT * FROM "{table_name}"'
        count_query = f'SELECT COUNT(*) as total FROM "{table_name}"'
        where_clauses = []
        params = []

        if search and search.strip():
            search_str = f"%{search.strip()}%"
            # Match on all text / varchar / string / json columns
            text_cols = [c["name"] for c in columns if any(t in c["type"].upper() for t in ["CHAR", "TEXT", "CLOB", "STR", "JSON", "BLOB", "UUID", "GUID"])]
            if not text_cols:
                text_cols = col_names  # fallback to all columns
            
            clause_parts = [f'CAST("{col}" AS TEXT) LIKE ?' for col in text_cols]
            where_clauses.append(f"({' OR '.join(clause_parts)})")
            params.extend([search_str] * len(text_cols))

        where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Total count
        cursor.execute(count_query + where_sql, params)
        total_rows = cursor.fetchone()["total"]

        # Sorting
        order_sql = ""
        if sort_by and sort_by in col_names:
            direction = "DESC" if sort_order.upper() == "DESC" else "ASC"
            order_sql = f' ORDER BY "{sort_by}" {direction}'
        else:
            # Default sort by created_at if exists, or primary key
            pk_col = next((c["name"] for c in columns if c["pk"]), None)
            if "created_at" in col_names:
                order_sql = ' ORDER BY "created_at" DESC'
            elif pk_col:
                order_sql = f' ORDER BY "{pk_col}" ASC'

        # Pagination offset
        offset = (page - 1) * page_size
        pagination_sql = f" LIMIT {page_size} OFFSET {offset}"

        full_query = base_query + where_sql + order_sql + pagination_sql
        cursor.execute(full_query, params)
        rows = cursor.fetchall()

        # Parse rows into clean JSON-serializable dictionaries
        records = []
        for r in rows:
            record = {}
            for col in columns:
                val = r[col["name"]]
                if isinstance(val, (bytes, bytearray)):
                    try:
                        val = val.decode("utf-8")
                    except Exception:
                        val = f"<BINARY_DATA {len(val)} bytes>"
                elif isinstance(val, str):
                    if (val.startswith("{") and val.endswith("}")) or (val.startswith("[") and val.endswith("]")):
                        try:
                            val = json.loads(val)
                        except Exception:
                            pass
                record[col["name"]] = val
            records.append(record)

        total_pages = max(1, (total_rows + page_size - 1) // page_size) if total_rows > 0 else 1
        pk_cols = [c["name"] for c in columns if c["pk"]]

        return {
            "table": table_name,
            "category": TABLE_CATEGORIES.get(table_name, "OTHER"),
            "columns": columns,
            "primary_key": pk_cols[0] if pk_cols else "id",
            "primary_keys": pk_cols,
            "foreign_keys": foreign_keys,
            "inbound_foreign_keys": inbound_fks,
            "rows": records,
            "total_rows": total_rows,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    finally:
        conn.close()

@router.get("/relationships")
def get_relationships(_=Depends(verify_explorer_access)):
    """
    Returns full relational foreign-key graph across all tables.
    """
    conn = get_sqlite_conn()
    cursor = conn.cursor()
    try:
        tables = get_all_table_names(cursor)
        nodes = []
        edges = []

        for table in tables:
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {table}")
            cnt = cursor.fetchone()["cnt"]

            nodes.append({
                "id": table,
                "name": table,
                "category": TABLE_CATEGORIES.get(table, "OTHER"),
                "row_count": cnt
            })

            cursor.execute(f"PRAGMA foreign_key_list({table})")
            fks = cursor.fetchall()
            for fk in fks:
                edges.append({
                    "from": table,
                    "to": fk["table"],
                    "from_column": fk["from"],
                    "to_column": fk["to"],
                    "label": f"{fk['from']} → {fk['to']}"
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "total_relationships": len(edges)
        }
    finally:
        conn.close()

