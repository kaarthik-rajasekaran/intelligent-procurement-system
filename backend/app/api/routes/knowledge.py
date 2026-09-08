from typing import List
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.entities import KnowledgeDocument
from app.schemas.domain import KnowledgeDocOut, KnowledgeQueryRequest, KnowledgeQueryResponse
from app.ai.rag import query_knowledge_rag, ingest_document
from app.api.deps import get_current_user

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base & Policy RAG"])

@router.get("/documents", response_model=List[KnowledgeDocOut])
def list_knowledge_documents(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc()).all()

@router.post("/query", response_model=KnowledgeQueryResponse)
def query_procurement_knowledge(query_in: KnowledgeQueryRequest, db: Session = Depends(get_db)):
    return query_knowledge_rag(db, query_in.query)
