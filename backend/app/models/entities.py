import uuid
from datetime import datetime
import enum
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Numeric, DateTime, ForeignKey, Table
)
from sqlalchemy.orm import relationship
from app.core.database import Base, GUID

class UserRole(str, enum.Enum):
    EMPLOYEE = "EMPLOYEE"
    SUPERVISOR = "SUPERVISOR"
    VENDOR = "VENDOR"
    ADMIN = "ADMIN"

class PRStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    # Legacy — kept for backward compatibility with old records
    APPROVED_FOR_RFQ = "APPROVED_FOR_RFQ"
    # New multi-vendor workflow statuses
    RFQS_ISSUED = "RFQS_ISSUED"                     # Supervisor selected vendors and issued RFQs
    AWAITING_QUOTATIONS = "AWAITING_QUOTATIONS"      # RFQs issued, no quotations received yet
    QUOTATIONS_READY = "QUOTATIONS_READY"            # At least 1 quotation received
    # Legacy alias statuses — kept for backward compat
    RFQ_ISSUED = "RFQ_ISSUED"
    QUOTATION_RECEIVED = "QUOTATION_RECEIVED"
    VENDOR_SELECTION_PENDING = "VENDOR_SELECTION_PENDING"
    FINAL_APPROVAL_PENDING = "FINAL_APPROVAL_PENDING"
    APPROVED = "APPROVED"
    PO_GENERATED = "PO_GENERATED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class BadgeType(str, enum.Enum):
    PREFERRED_VENDOR = "PREFERRED_VENDOR"
    HIGH_RELIABILITY = "HIGH_RELIABILITY"
    QUALITY_LEADER = "QUALITY_LEADER"
    COST_EFFICIENT = "COST_EFFICIENT"
    NEEDS_ATTENTION = "NEEDS_ATTENTION"

# Department - Supervisor Many-to-Many or association
department_supervisors = Table(
    "department_supervisors",
    Base.metadata,
    Column("department_id", GUID, ForeignKey("departments.id", ondelete="CASCADE"), primary_key=True),
    Column("supervisor_id", GUID, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

# Vendor - Item Category or Item Mapping
vendor_item_mapping = Table(
    "vendor_item_mapping",
    Base.metadata,
    Column("vendor_id", GUID, ForeignKey("vendors.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", GUID, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True)
)

class Department(Base):
    __tablename__ = "departments"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="department")
    supervisors = relationship("User", secondary=department_supervisors, back_populates="supervised_departments")
    purchase_requests = relationship("PurchaseRequest", back_populates="department")

class User(Base):
    __tablename__ = "users"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(150), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default=UserRole.EMPLOYEE.value)
    department_id = Column(GUID, ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    department = relationship("Department", back_populates="users", foreign_keys=[department_id])
    supervised_departments = relationship("Department", secondary=department_supervisors, back_populates="supervisors")
    purchase_requests = relationship("PurchaseRequest", back_populates="requester", foreign_keys="PurchaseRequest.requester_id")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    vendor = relationship("Vendor", back_populates="users")

class Item(Base):
    __tablename__ = "items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False, index=True)
    unit = Column(String(50), nullable=False, default="units")  # e.g., units, pcs, kg, licenses
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    inventory = relationship("Inventory", back_populates="item", uselist=False, cascade="all, delete-orphan")
    vendors = relationship("Vendor", secondary=vendor_item_mapping, back_populates="eligible_items")
    pr_items = relationship("PurchaseRequestItem", back_populates="item")
    historical_prices = relationship("HistoricalPrice", back_populates="item", cascade="all, delete-orphan")

class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="CASCADE"), unique=True, nullable=False)
    available_quantity = Column(Numeric(12, 2), default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    item = relationship("Item", back_populates="inventory")

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    users = relationship("User", back_populates="vendor")
    eligible_items = relationship("Item", secondary=vendor_item_mapping, back_populates="vendors")
    performance_records = relationship("VendorPerformance", back_populates="vendor", cascade="all, delete-orphan")
    item_performance_records = relationship("VendorItemPerformance", back_populates="vendor", cascade="all, delete-orphan")
    badges = relationship("VendorBadge", back_populates="vendor", cascade="all, delete-orphan")
    rfqs = relationship("RFQ", back_populates="vendor")
    quotations = relationship("Quotation", back_populates="vendor")
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    reviews = relationship("VendorReview", back_populates="vendor", cascade="all, delete-orphan")
    review_embeddings = relationship("VendorReviewEmbedding", back_populates="vendor", cascade="all, delete-orphan")

class VendorPerformance(Base):
    __tablename__ = "vendor_performance"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    measurement_period = Column(DateTime, nullable=False)
    quality_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    delivery_reliability_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    responsiveness_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    price_competitiveness_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    historical_fulfillment_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="performance_records")

class VendorItemPerformance(Base):
    __tablename__ = "vendor_item_performance"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    item_specific_score = Column(Numeric(5, 2), nullable=False)  # 0-100
    measurement_period = Column(DateTime, nullable=False)

    vendor = relationship("Vendor", back_populates="item_performance_records")

class VendorBadge(Base):
    __tablename__ = "vendor_badges"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    badge_type = Column(String(50), nullable=False)
    awarded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="badges")

class HistoricalPrice(Base):
    __tablename__ = "historical_prices"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    item = relationship("Item", back_populates="historical_prices")

class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    requester_id = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    department_id = Column(GUID, ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    selected_vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String(50), default=PRStatus.DRAFT.value, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    duplicate_acknowledged = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    requester = relationship("User", back_populates="purchase_requests", foreign_keys=[requester_id])
    department = relationship("Department", back_populates="purchase_requests")
    selected_vendor = relationship("Vendor", foreign_keys=[selected_vendor_id])
    items = relationship("PurchaseRequestItem", back_populates="purchase_request", cascade="all, delete-orphan")
    reviews = relationship("PurchaseRequestReview", back_populates="purchase_request", cascade="all, delete-orphan", order_by="desc(PurchaseRequestReview.created_at)")
    rfqs = relationship("RFQ", back_populates="purchase_request", cascade="all, delete-orphan")
    vendor_selection_decision = relationship("VendorSelectionDecision", back_populates="purchase_request", uselist=False, cascade="all, delete-orphan")
    purchase_order = relationship("PurchaseOrder", back_populates="purchase_request", uselist=False)
    recommendation_snapshots = relationship("PRRecommendationSnapshot", back_populates="purchase_request", cascade="all, delete-orphan", order_by="desc(PRRecommendationSnapshot.version)")

class PurchaseRequestItem(Base):
    __tablename__ = "purchase_request_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Numeric(12, 2), nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="items")
    item = relationship("Item", back_populates="pr_items")

class PurchaseRequestReview(Base):
    __tablename__ = "purchase_request_reviews"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    supervisor_id = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    decision = Column(String(50), nullable=False)  # APPROVED_TO_PROCEED, RETURNED_FOR_REVISION, REJECTED
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="reviews")
    supervisor = relationship("User")

class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    reference_number = Column(String(50), unique=True, index=True, nullable=False)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    # Statuses: AWAITING_QUOTATION | QUOTATION_RECEIVED | RFQ_EXPIRED | RFQ_CANCELLED
    # Legacy: ISSUED (= AWAITING_QUOTATION), QUOTED (= QUOTATION_RECEIVED), CLOSED
    status = Column(String(50), default="AWAITING_QUOTATION", nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    due_at = Column(DateTime, nullable=True)   # RFQ submission deadline

    purchase_request = relationship("PurchaseRequest", back_populates="rfqs")
    vendor = relationship("Vendor", back_populates="rfqs")
    quotation = relationship("Quotation", back_populates="rfq", uselist=False, cascade="all, delete-orphan")

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    rfq_id = Column(GUID, ForeignKey("rfqs.id", ondelete="CASCADE"), unique=True, nullable=False)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    quoted_unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)
    lead_time_days = Column(Integer, nullable=False)
    expected_delivery_date = Column(String(20), nullable=True)  # ISO date string "YYYY-MM-DD"
    validity_period = Column(String(100), nullable=True)
    notes = Column(Text, nullable=True)
    document_path = Column(String(500), nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    rfq = relationship("RFQ", back_populates="quotation")
    vendor = relationship("Vendor", back_populates="quotations")
    purchase_orders = relationship("PurchaseOrder", back_populates="quotation")

class VendorSelectionDecision(Base):
    __tablename__ = "vendor_selection_decisions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="CASCADE"), unique=True, nullable=False)
    recommended_vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    selected_vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    supervisor_id = Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    override_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="vendor_selection_decision")
    recommended_vendor = relationship("Vendor", foreign_keys=[recommended_vendor_id])
    selected_vendor = relationship("Vendor", foreign_keys=[selected_vendor_id])
    supervisor = relationship("User", foreign_keys=[supervisor_id])

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    po_number = Column(String(50), unique=True, index=True, nullable=False)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="RESTRICT"), unique=True, nullable=False)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    quotation_id = Column(GUID, ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False)
    approved_amount = Column(Numeric(12, 2), nullable=False)
    status = Column(String(50), default="GENERATED", nullable=False)
    pdf_path = Column(String(500), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="purchase_order")
    vendor = relationship("Vendor", back_populates="purchase_orders")
    quotation = relationship("Quotation", back_populates="purchase_orders")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    related_entity_type = Column(String(50), nullable=True)
    related_entity_id = Column(GUID, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(GUID, nullable=True)
    previous_state = Column(Text, nullable=True)  # JSON string
    new_state = Column(Text, nullable=True)  # JSON string
    metadata_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User")

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    document_type = Column(String(50), nullable=False)
    processing_status = Column(String(50), default="PROCESSED", nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding_json = Column(Text, nullable=True)  # JSON array of floats for dialect portability
    metadata_json = Column(Text, nullable=True)

    document = relationship("KnowledgeDocument", back_populates="chunks")


# =============================================================================
# VENDOR REVIEW SYSTEM (RAG + LLM Recommendation Engine)
# =============================================================================

class VendorReview(Base):
    """
    Structured quarterly vendor review record.
    Simulates exported Google Form response data (CSV ingestion).
    Used as the primary data source for RAG-based vendor recommendations.
    """
    __tablename__ = "vendor_reviews"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)
    item_id = Column(GUID, ForeignKey("items.id", ondelete="CASCADE"), nullable=True, index=True)
    review_period = Column(String(20), nullable=False)           # e.g., "Q2-2026"
    reviewer_role = Column(String(50), nullable=False)           # "PROCUREMENT_OFFICER", "DEPARTMENT_HEAD", "INVENTORY_MANAGER"

    # Structured 0–10 ratings
    quality_rating = Column(Numeric(3, 1), nullable=False)
    delivery_rating = Column(Numeric(3, 1), nullable=False)
    responsiveness_rating = Column(Numeric(3, 1), nullable=False)
    price_rating = Column(Numeric(3, 1), nullable=False)

    # Qualitative free-text (the content that gets embedded for RAG)
    qualitative_feedback = Column(Text, nullable=False)
    specific_issues = Column(Text, nullable=True)

    # Contextual metadata
    order_quantity = Column(Numeric(12, 2), nullable=True)
    fulfilled_on_time = Column(Boolean, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    vendor = relationship("Vendor", back_populates="reviews")
    embedding = relationship("VendorReviewEmbedding", back_populates="review", uselist=False, cascade="all, delete-orphan")


class VendorReviewEmbedding(Base):
    """
    Vector embedding of qualitative review text for RAG similarity retrieval.
    Stores embedding as JSON array for SQLite compatibility
    (same pattern as KnowledgeChunk.embedding_json — no PostgreSQL/pgvector required).
    """
    __tablename__ = "vendor_review_embeddings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    review_id = Column(GUID, ForeignKey("vendor_reviews.id", ondelete="CASCADE"), unique=True, nullable=False)
    vendor_id = Column(GUID, ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True)  # denormalized for fast filter
    item_id = Column(GUID, ForeignKey("items.id", ondelete="CASCADE"), nullable=True, index=True)       # denormalized
    category = Column(String(100), nullable=True, index=True)                                            # denormalized for category-level fallback

    embedding_json = Column(Text, nullable=True)   # JSON array of floats
    chunk_text = Column(Text, nullable=False)       # the text that was embedded
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    review = relationship("VendorReview", back_populates="embedding")
    vendor = relationship("Vendor", back_populates="review_embeddings")


# =============================================================================
# PR RECOMMENDATION SNAPSHOT (Persist RAG+LLM result for Supervisor reuse)
# =============================================================================

class PRRecommendationSnapshot(Base):
    """
    Persisted snapshot of a RAG+LLM vendor recommendation for a specific Purchase Request.
    
    Generated ONCE when employee runs "Run Vendor Recommendation" and saved immediately
    after PR creation. The Supervisor reads this snapshot without triggering any LLM calls.
    
    Only the explicit "Refresh AI Recommendation" button on the Checking Sheet creates a
    new version. Historical versions are never overwritten (append-only, version-numbered).
    
    is_stale is set to True by the system when the PR item_id or quantity is changed after
    the snapshot was created, prompting the Supervisor to consider refreshing.
    """
    __tablename__ = "pr_recommendation_snapshots"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    purchase_request_id = Column(GUID, ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)

    # Denormalized item context (captured at time of recommendation)
    item_id = Column(String(36), nullable=True)          # UUID as string for flexibility
    item_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    quantity = Column(Numeric(12, 2), nullable=True)

    # Top recommendation (the #1 ranked candidate at time of generation)
    recommended_vendor_id = Column(String(36), nullable=True)
    recommended_vendor_name = Column(String(200), nullable=True)

    # Full ranked candidate list — serialized JSON of List[RAGVendorRecommendation]
    all_candidates_json = Column(Text, nullable=True)

    # Top recommendation metrics
    evidence_confidence = Column(String(20), nullable=True)   # HIGH | MEDIUM | LOW
    reasoning_summary = Column(Text, nullable=True)
    key_strengths_json = Column(Text, nullable=True)          # JSON list of strings
    potential_risks_json = Column(Text, nullable=True)        # JSON list of strings
    avg_quality_rating = Column(Numeric(4, 2), nullable=True)
    avg_delivery_rating = Column(Numeric(4, 2), nullable=True)
    avg_price_rating = Column(Numeric(4, 2), nullable=True)
    trend_direction = Column(String(20), nullable=True)       # IMPROVING | STABLE | DECLINING
    review_count = Column(Integer, nullable=True, default=0)
    final_recommendation_score = Column(Numeric(6, 2), nullable=True)  # Canonical ranking score
    analytical_score = Column(Numeric(6, 2), nullable=True)             # Historical performance component
    source = Column(String(30), nullable=True)                # LLM_RAG | ANALYTICAL_FALLBACK

    # Lifecycle flags
    is_stale = Column(Boolean, default=False, nullable=False)
    triggered_by = Column(String(30), nullable=False, default="EMPLOYEE")  # EMPLOYEE | SUPERVISOR_REFRESH

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    purchase_request = relationship("PurchaseRequest", back_populates="recommendation_snapshots")

