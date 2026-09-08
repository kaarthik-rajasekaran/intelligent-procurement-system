import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.domain import QuotationAnalysisOutV2
from app.intelligence.analytical import evaluate_quotations_v2
from app.api.deps import get_current_user

router = APIRouter(prefix="/purchase-requests", tags=["Quotations & Bidding Analysis"])

@router.get("/{pr_id}/quotation-analysis", response_model=QuotationAnalysisOutV2)
def get_quotation_analysis(pr_id: uuid.UUID, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    """
    Returns V2 quotation analysis with delivery date scoring.
    Only valid quotations from non-expired RFQs are included.
    """
    return evaluate_quotations_v2(db, pr_id)
