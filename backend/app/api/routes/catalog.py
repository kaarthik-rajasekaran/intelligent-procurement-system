from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import Item, Department, Inventory
from app.schemas.domain import ItemOut, DepartmentOut, InventoryAnalysisResult
from app.intelligence.deterministic import analyze_inventory
from app.api.deps import get_current_user

catalog_router = APIRouter(tags=["Catalog & Departments"])
inventory_router = APIRouter(prefix="/inventory", tags=["Inventory"])

@catalog_router.get("/items", response_model=List[ItemOut])
def list_items(db: Session = Depends(get_db)):
    items = db.query(Item).filter(Item.is_active == True).all()
    results = []
    for item in items:
        inv = db.query(Inventory).filter(Inventory.item_id == item.id).first()
        available = float(inv.available_quantity) if inv else 0.0
        results.append(
            ItemOut(
                id=item.id,
                name=item.name,
                description=item.description,
                category=item.category,
                unit=item.unit,
                is_active=item.is_active,
                available_quantity=available
            )
        )
    return results

@catalog_router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: uuid.UUID, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    inv = db.query(Inventory).filter(Inventory.item_id == item.id).first()
    available = float(inv.available_quantity) if inv else 0.0
    return ItemOut(
        id=item.id,
        name=item.name,
        description=item.description,
        category=item.category,
        unit=item.unit,
        is_active=item.is_active,
        available_quantity=available
    )

@catalog_router.get("/departments", response_model=List[DepartmentOut])
def list_departments(db: Session = Depends(get_db)):
    return db.query(Department).all()

@inventory_router.get("/items/{item_id}", response_model=InventoryAnalysisResult)
def check_item_inventory(item_id: uuid.UUID, quantity: float = 1.0, db: Session = Depends(get_db)):
    return analyze_inventory(db, item_id, quantity)
