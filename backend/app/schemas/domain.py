from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field
import uuid

# --- AUTH & USER ---
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class LoginRequest(BaseModel):
    email: str
    password: str

class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    vendor_id: Optional[uuid.UUID] = None
    vendor_name: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True

# --- DEPARTMENTS ---
class DepartmentOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    class Config:
        from_attributes = True

# --- ITEMS ---
class ItemOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str] = None
    category: str
    unit: str
    is_active: bool
    available_quantity: float = 0.0

    class Config:
        from_attributes = True

# --- INVENTORY ---
class InventoryAnalysisResult(BaseModel):
    requested_quantity: float
    available_quantity: float
    shortage_quantity: float
    coverage_status: str  # SUFFICIENT or INSUFFICIENT

# --- DUPLICATE DETECTION ---
class DuplicateMatch(BaseModel):
    id: uuid.UUID
    reference_number: str
    department_name: str
    item_name: str
    existing_quantity: float
    requested_quantity: float
    status: str
    request_date: datetime
    selected_vendor_name: Optional[str] = None
    difference_percentage: float

# --- VENDOR SCORING & RECOMMENDATION ---
class VendorBadgeOut(BaseModel):
    badge_type: str
    awarded_at: datetime

    class Config:
        from_attributes = True

class VendorFactorBreakdown(BaseModel):
    quality: float
    delivery_reliability: float
    item_specific: float
    price_competitiveness: float
    historical_fulfillment: float
    responsiveness: float

class VendorRecommendationOut(BaseModel):
    rank: int
    vendor_id: uuid.UUID
    vendor_name: str
    overall_score: float
    badges: List[str]
    factor_breakdown: VendorFactorBreakdown
    explanation: str
    score_confidence: str  # HIGH, MEDIUM, LOW


class RAGVendorRecommendation(BaseModel):
    """
    Rich vendor recommendation produced by the RAG + LLM reasoning engine.
    Contains structured quantitative evidence + LLM contextual reasoning output.

    Score terminology (canonical):
      final_recommendation_score — THE ranking field. Always computed deterministically
        from: 40% Historical Performance + 40% Review Evidence + 20% Confidence
        modified by LLM recommendation_status (CAUTION=-15%, RECOMMENDED=+5%)
      analytical_score — The old weighted VendorPerformance formula score (0-100).
        Displayed as "Historical Performance Score" in the UI. NOT the ranking field.
      recommendation_status — LLM qualitative assessment (RECOMMENDED/ACCEPTABLE/CAUTION).
        Informs final_recommendation_score via modifier but does NOT directly set rank.
    """
    rank: int
    vendor_id: uuid.UUID
    vendor_name: str
    recommendation_status: str          # RECOMMENDED | ACCEPTABLE | CAUTION
    reasoning_summary: str              # LLM-generated contextual reasoning
    key_strengths: List[str]            # LLM-identified strengths from evidence
    potential_risks: List[str]          # LLM-identified risks from evidence
    evidence_confidence: str            # HIGH | MEDIUM | LOW (deterministic rules)
    # Quantitative summary (from structured review aggregation)
    avg_quality_rating: Optional[float] = None
    avg_delivery_rating: Optional[float] = None
    avg_responsiveness_rating: Optional[float] = None
    avg_price_rating: Optional[float] = None
    trend_direction: Optional[str] = None   # IMPROVING | STABLE | DECLINING
    review_count: int = 0
    # Supporting qualitative evidence snippets
    review_insights: List[str] = []
    # Scores
    final_recommendation_score: float = 0.0  # CANONICAL ranking field (0-100)
    analytical_score: float = 0.0            # Historical Performance Score (component only)
    badges: List[str] = []
    # Source of recommendation
    source: str = "ANALYTICAL_FALLBACK"  # "LLM_RAG" | "ANALYTICAL_FALLBACK"


class VendorOut(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    phone: Optional[str] = None
    is_active: bool
    badges: List[str] = []

    class Config:
        from_attributes = True


# --- RECOMMENDATION SNAPSHOT (Persist RAG result for Supervisor reuse) ---

class RecommendationSnapshotCreate(BaseModel):
    """Payload sent by the frontend immediately after PR creation to persist the RAG snapshot."""
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    recommended_vendor_id: Optional[str] = None
    recommended_vendor_name: Optional[str] = None
    all_candidates: List[RAGVendorRecommendation] = []
    evidence_confidence: Optional[str] = None
    reasoning_summary: Optional[str] = None
    key_strengths: List[str] = []
    potential_risks: List[str] = []
    avg_quality_rating: Optional[float] = None
    avg_delivery_rating: Optional[float] = None
    avg_price_rating: Optional[float] = None
    trend_direction: Optional[str] = None
    review_count: int = 0
    final_recommendation_score: float = 0.0  # Canonical ranking score
    analytical_score: float = 0.0            # Historical performance score (component)
    source: str = "ANALYTICAL_FALLBACK"

class RecommendationSnapshotOut(BaseModel):
    """Full snapshot returned to the Supervisor Checking Sheet — zero LLM on read."""
    id: uuid.UUID
    purchase_request_id: uuid.UUID
    version: int
    item_id: Optional[str] = None
    item_name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    recommended_vendor_id: Optional[str] = None
    recommended_vendor_name: Optional[str] = None
    all_candidates: List[RAGVendorRecommendation] = []
    evidence_confidence: Optional[str] = None
    reasoning_summary: Optional[str] = None
    key_strengths: List[str] = []
    potential_risks: List[str] = []
    avg_quality_rating: Optional[float] = None
    avg_delivery_rating: Optional[float] = None
    avg_price_rating: Optional[float] = None
    trend_direction: Optional[str] = None
    review_count: int = 0
    final_recommendation_score: float = 0.0  # Canonical ranking score
    analytical_score: float = 0.0            # Historical performance score (component)
    source: str = "ANALYTICAL_FALLBACK"
    is_stale: bool = False
    triggered_by: str = "EMPLOYEE"
    created_at: datetime

    class Config:
        from_attributes = True


# --- PURCHASE REQUEST ---
class PurchaseRequestCreate(BaseModel):
    item_id: uuid.UUID
    quantity: float = Field(..., gt=0)
    selected_vendor_id: uuid.UUID
    notes: Optional[str] = None
    duplicate_acknowledged: bool = False

class PurchaseRequestUpdate(BaseModel):
    item_id: Optional[uuid.UUID] = None
    quantity: Optional[float] = Field(None, gt=0)
    selected_vendor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

class PurchaseRequestReturn(BaseModel):
    reason: str = Field(..., min_length=3)

class PurchaseRequestResubmit(BaseModel):
    quantity: Optional[float] = Field(None, gt=0)
    selected_vendor_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None

class PurchaseRequestReviewOut(BaseModel):
    id: uuid.UUID
    supervisor_id: uuid.UUID
    supervisor_name: str
    decision: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PurchaseRequestOut(BaseModel):
    id: uuid.UUID
    reference_number: str
    requester_id: uuid.UUID
    requester_name: str
    department_id: uuid.UUID
    department_name: str
    selected_vendor_id: uuid.UUID
    selected_vendor_name: str
    status: str
    notes: Optional[str] = None
    duplicate_acknowledged: bool
    item_id: Optional[uuid.UUID] = None
    item_name: Optional[str] = None
    item_unit: Optional[str] = None
    quantity: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PurchaseRequestDetailOut(PurchaseRequestOut):
    inventory_analysis: Optional[InventoryAnalysisResult] = None
    duplicate_matches: List[DuplicateMatch] = []
    vendor_recommendation: Optional[VendorRecommendationOut] = None
    reviews: List[PurchaseRequestReviewOut] = []

# --- RFQ & QUOTATION ---
class RFQOut(BaseModel):
    id: uuid.UUID
    reference_number: str
    purchase_request_id: uuid.UUID
    pr_reference: str
    item_name: str
    item_unit: str
    quantity: float
    vendor_id: uuid.UUID
    vendor_name: str
    status: str
    issued_at: datetime
    due_at: Optional[datetime] = None
    has_quotation: bool = False

    class Config:
        from_attributes = True

class RFQIssueRequest(BaseModel):
    """Supervisor submits this to issue RFQs to selected vendors."""
    vendor_ids: List[uuid.UUID]     # 1–3 vendor IDs selected by supervisor
    due_date: Optional[str] = None  # ISO datetime string for RFQ deadline (default: 7 days)

class QuotationCreate(BaseModel):
    quoted_unit_price: float = Field(..., gt=0)
    lead_time_days: int = Field(..., gt=0)
    expected_delivery_date: Optional[str] = None   # ISO date "YYYY-MM-DD"
    validity_period: Optional[str] = None
    notes: Optional[str] = None

class QuotationOut(BaseModel):
    id: uuid.UUID
    rfq_id: uuid.UUID
    vendor_id: uuid.UUID
    vendor_name: str
    quoted_unit_price: float
    total_price: float
    lead_time_days: int
    expected_delivery_date: Optional[str] = None
    validity_period: Optional[str] = None
    notes: Optional[str] = None
    submitted_at: datetime

    class Config:
        from_attributes = True

class QuotationEvaluationItem(BaseModel):
    rank: int
    vendor_id: uuid.UUID
    vendor_name: str
    quoted_unit_price: float
    total_price: float
    lead_time_days: int
    price_score: float
    delivery_score: float
    reliability_score: float
    quality_score: float
    final_weighted_score: float
    is_recommended: bool
    vendor_badges: List[str] = []

class QuotationAnalysisOut(BaseModel):
    purchase_request_id: uuid.UUID
    pr_reference: str
    evaluations: List[QuotationEvaluationItem]
    recommended_vendor_id: Optional[uuid.UUID] = None
    recommended_vendor_name: Optional[str] = None

# --- V2 QUOTATION EVALUATION (Multi-Vendor RFQ Workflow) ---
class QuotationEvaluationItemV2(BaseModel):
    """Extended quotation evaluation item with delivery date as a first-class factor."""
    rank: int
    vendor_id: uuid.UUID
    vendor_name: str
    quoted_unit_price: float
    total_price: float
    lead_time_days: int
    expected_delivery_date: Optional[str] = None   # Vendor's committed delivery date
    price_score: float
    lead_time_score: float
    delivery_date_score: float     # Score based on how soon vendor can deliver
    reliability_score: float
    quality_score: float
    final_weighted_score: float
    is_recommended: bool
    is_expired: bool = False       # True if RFQ deadline passed before quotation
    vendor_badges: List[str] = []

class QuotationAnalysisOutV2(BaseModel):
    """V2 quotation analysis result used by the multi-vendor RFQ workflow."""
    purchase_request_id: uuid.UUID
    pr_reference: str
    evaluations: List[QuotationEvaluationItemV2]
    recommended_vendor_id: Optional[uuid.UUID] = None
    recommended_vendor_name: Optional[str] = None
    llm_explanation: Optional[str] = None     # Optional LLM narrative (not calculated)

# --- FINAL SELECTION & APPROVAL ---
class VendorSelectionRequest(BaseModel):
    selected_vendor_id: uuid.UUID
    override_reason: Optional[str] = None

class FinalApprovalRequest(BaseModel):
    notes: Optional[str] = None

# --- PURCHASE ORDER ---
class PurchaseOrderOut(BaseModel):
    id: uuid.UUID
    po_number: str
    purchase_request_id: uuid.UUID
    pr_reference: str
    vendor_id: uuid.UUID
    vendor_name: str
    vendor_email: str
    item_name: str
    quantity: float
    item_unit: str
    unit_price: float
    approved_amount: float
    status: str
    pdf_url: Optional[str] = None
    generated_at: datetime

    class Config:
        from_attributes = True

# --- NOTIFICATIONS & AUDIT ---
class NotificationOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    message: str
    is_read: bool
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogOut(BaseModel):
    id: uuid.UUID
    actor_id: Optional[uuid.UUID] = None
    actor_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- KNOWLEDGE & RAG ---
class KnowledgeDocOut(BaseModel):
    id: uuid.UUID
    title: str
    original_filename: str
    document_type: str
    processing_status: str
    uploaded_at: datetime

    class Config:
        from_attributes = True

class KnowledgeQueryRequest(BaseModel):
    query: str

class KnowledgeQueryResponse(BaseModel):
    query: str
    answer: str
    grounded_chunks: List[str]
    confidence: str

# --- AI COPILOT ---
class AIChatRequest(BaseModel):
    message: str
    context_type: Optional[str] = None  # "pr", "general"
    context_id: Optional[str] = None

class AIChatResponse(BaseModel):
    reply: str
    context_used: Optional[str] = None

class AISummaryResponse(BaseModel):
    summary: str
    key_highlights: List[str]
    risks_or_notes: List[str]
