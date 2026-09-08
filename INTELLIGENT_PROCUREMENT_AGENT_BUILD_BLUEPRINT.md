# INTELLIGENT PROCUREMENT SYSTEM
## Autonomous Coding Agent Build Blueprint
### Version 2 — Detailed Implementation Specification

> **Purpose:** This document is the implementation blueprint for an autonomous coding agent such as Antigravity. The agent should treat this document as the primary source of truth when designing and building the system.
>
> **Important:** The goal is not to reproduce any previously suggested architecture mechanically. The goal is to build the most efficient, reliable, understandable solution that satisfies the requirements below.
>
> **Core architectural principle:**
>
> **Deterministic + Analytical + Generative/Agentic Intelligence**
>
> Procurement-critical decisions must remain deterministic and/or analytically reproducible. Generative AI enhances understanding and interaction but must never become a dependency for core workflow correctness.

---

# 1. PROJECT GOAL

Build a complete intelligent procurement management system that manages the lifecycle:

**Purchase Request → Supervisor Review → RFQ → Vendor Quotation → Quotation Evaluation → Final Vendor Selection → Final Approval → Purchase Order Generation**

The system must demonstrate:

1. Structured procurement workflows.
2. Role-based access control.
3. Inventory intelligence.
4. Duplicate/similar PR detection.
5. Explainable vendor recommendation.
6. Vendor performance scores and badges.
7. Indicative cost estimation before quotations.
8. Supervisor decision support.
9. Vendor quotation handling.
10. Weighted quotation evaluation.
11. Human override and approval.
12. Purchase Order PDF generation.
13. Notifications and automatic emails.
14. RAG-powered knowledge assistance.
15. Contextual AI assistance.
16. Efficient use of LLMs only where they provide real value.

The system will use mock data and does not need deployment infrastructure.

---

# 2. NON-NEGOTIABLE SYSTEM PRINCIPLES

## 2.1 Core procurement logic must work without an LLM

The following MUST NOT require an LLM:

- Authentication.
- Authorization.
- PR creation.
- Inventory checking.
- Duplicate detection.
- Workflow state transitions.
- Supervisor routing.
- Vendor scoring.
- Vendor ranking.
- Indicative cost calculation.
- RFQ creation.
- Quotation storage.
- Quotation scoring.
- Final approval validation.
- PO generation.

If the LLM is unavailable, the procurement workflow must continue normally.

## 2.2 Humans retain final authority

AI and analytical services may recommend.

They may not:

- Automatically approve a PR.
- Automatically reject a PR.
- Automatically choose the final vendor.
- Automatically generate a PO without required approval.
- Change procurement workflow state autonomously.

## 2.3 Structured data first

Purchase Requests are created through structured UI fields.

The primary PR workflow is NOT based on:

- Natural-language request parsing.
- Free-text semantic item extraction.
- Embedding-based PR matching.

The requester selects structured data from the system.

## 2.4 Use the simplest architecture that preserves quality

Avoid:

- Microservices.
- Kubernetes.
- Event infrastructure that provides no practical benefit.
- Separate vector databases.
- Unnecessary ML models.
- LangChain unless a later requirement genuinely demands it.

Use a modular monolith with clear internal separation.

---

# 3. TECH STACK

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS
- shadcn/ui
- Lucide icons
- Recharts where analytics visualization is useful

## Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic

## Database

- PostgreSQL
- pgvector extension

## Authentication

- JWT access tokens
- Secure password hashing
- Backend-enforced RBAC

## Storage

Local filesystem.

Suggested structure:

```text
storage/
├── purchase_orders/
├── quotations/
├── knowledge_documents/
└── generated_exports/
```

## AI

Implement a pluggable abstraction.

Possible providers:

```text
LLMProvider
├── LocalLLMProvider
├── HostedLLMProvider
└── FutureProvider
```

Do not tightly couple application business logic to one provider.

## RAG

- Document text extraction.
- Chunking.
- Embedding provider abstraction.
- pgvector similarity search.
- Context construction.
- Grounded answer generation.

---

# 4. HIGH-LEVEL ARCHITECTURE

```text
Next.js Frontend
        │
        │ REST API
        ▼
FastAPI Backend
        │
        ├── Authentication / RBAC
        ├── Procurement Module
        ├── Inventory Module
        ├── Vendor Module
        ├── RFQ Module
        ├── Quotation Module
        ├── Purchase Order Module
        ├── Notification Module
        ├── Analytical Intelligence
        └── Generative AI / RAG
                 │
                 ├── PostgreSQL structured data
                 ├── pgvector knowledge retrieval
                 └── Pluggable LLM provider
        │
        ▼
PostgreSQL + pgvector
```

## Internal intelligence separation

```text
INTELLIGENCE
│
├── DETERMINISTIC
│   ├── validation
│   ├── workflow rules
│   ├── inventory analysis
│   └── duplicate detection
│
├── ANALYTICAL
│   ├── vendor scoring
│   ├── vendor recommendation
│   ├── indicative cost
│   └── quotation evaluation
│
└── GENERATIVE / AGENTIC
    ├── summaries
    ├── explanations
    ├── contextual copilot
    └── RAG knowledge answers
```

---

# 5. USER ROLES

## 5.1 Employee / Requester

Can:

- Log in.
- View own dashboard.
- Create PR.
- Select item.
- Enter quantity.
- View inventory intelligence.
- View duplicate alerts.
- View vendor recommendations.
- Select exactly one vendor.
- Submit PR.
- View own PR history.
- View workflow status.
- Revise returned PR.
- Resubmit returned PR.
- Use contextual AI assistance.

Cannot:

- Approve PRs.
- Issue RFQs.
- Perform final vendor approval.
- Generate PO directly.

## 5.2 Supervisor

Department-specific.

Can:

- View PRs assigned to their department.
- Review checking sheets.
- View inventory information.
- View duplicate matches.
- View vendor recommendations.
- View indicative cost.
- Return PR with mandatory reason.
- Approve PR to proceed.
- Review quotations.
- Review weighted quotation analysis.
- Confirm a vendor.
- Override system recommendation with mandatory reason.
- Perform final approval.
- Access generated PO.
- Use AI explanations and summaries.

Cannot:

- Automatically bypass mandatory workflow prerequisites.

## 5.3 Vendor

Can:

- Log in.
- View RFQs assigned to the vendor.
- View RFQ details.
- Submit quotation.
- View submitted quotation status.

Cannot:

- View unrelated RFQs.
- Approve procurement decisions.
- Modify PR workflow.

---

# 6. ROLE PERMISSION MATRIX

| Action | Employee | Supervisor | Vendor |
|---|---:|---:|---:|
| Login | Yes | Yes | Yes |
| Create PR | Yes | No requirement | No |
| View own PR | Yes | Assigned PRs | No |
| Edit Draft/Returned PR | Yes | No | No |
| Submit PR | Yes | No | No |
| Review PR | No | Assigned department | No |
| Return PR | No | Yes | No |
| Approve PR to RFQ stage | No | Yes | No |
| View assigned RFQ | No | Yes | Assigned only |
| Submit quotation | No | No | Yes |
| View quotation analysis | No | Yes | Own submitted quote |
| Select final vendor | No | Yes | No |
| Final approval | No | Yes | No |
| Generate PO | System after approval | Trigger/view | No |
| Upload knowledge docs | Optional admin capability if implemented | Optional | No |

---

# 7. PROCUREMENT WORKFLOW STATE MACHINE

Use an explicit state machine.

Suggested PR statuses:

```text
DRAFT
SUBMITTED
UNDER_REVIEW
REVISION_REQUIRED
APPROVED_FOR_RFQ
RFQ_ISSUED
QUOTATION_RECEIVED
VENDOR_SELECTION_PENDING
FINAL_APPROVAL_PENDING
APPROVED
PO_GENERATED
COMPLETED
REJECTED
```

## 7.1 State transitions

```text
DRAFT
  └── submit ───────────────► SUBMITTED

SUBMITTED
  └── supervisor opens ─────► UNDER_REVIEW

UNDER_REVIEW
  ├── return ───────────────► REVISION_REQUIRED
  └── approve to proceed ───► APPROVED_FOR_RFQ

REVISION_REQUIRED
  └── employee resubmits ───► SUBMITTED

APPROVED_FOR_RFQ
  └── RFQ issued ───────────► RFQ_ISSUED

RFQ_ISSUED
  └── quotation received ───► QUOTATION_RECEIVED

QUOTATION_RECEIVED
  └── evaluation ready ─────► VENDOR_SELECTION_PENDING

VENDOR_SELECTION_PENDING
  └── supervisor confirms ──► FINAL_APPROVAL_PENDING

FINAL_APPROVAL_PENDING
  └── final approval ───────► APPROVED

APPROVED
  └── PO generated ─────────► PO_GENERATED

PO_GENERATED
  └── procurement finalized ► COMPLETED
```

`REJECTED` is terminal.

## 7.2 Invalid transitions

Reject requests attempting:

- Final approval before quotation.
- PO generation before final approval.
- Quotation submission without an assigned RFQ.
- Employee approval actions.
- Supervisor review outside assigned department.
- Editing terminal PRs.
- Returning a PR without reason.
- Overriding recommendation without reason.

---

# 8. PURCHASE REQUEST CREATION

## 8.1 Required inputs

```text
item_id              Required
quantity             Required
selected_vendor_id   Required
notes                Optional
```

Department is derived from authenticated employee.

Requester identity is derived from authentication, not trusted from client payload.

## 8.2 Create PR user flow

```text
Employee opens Create PR
        ↓
Select Item
        ↓
Fetch inventory
        ↓
Enter Quantity
        ↓
Calculate availability and shortage
        ↓
Fetch vendor recommendations
        ↓
Select one vendor
        ↓
Run duplicate detection
        ↓
If matches exist → show duplicate dialog
        ↓
Employee cancels OR acknowledges and continues
        ↓
Review
        ↓
Submit
        ↓
Route to department supervisor
```

## 8.3 Validation

Quantity:

- Must be numeric.
- Must be greater than zero.
- Must respect reasonable configured upper bounds.

Item:

- Must exist.
- Must be active.

Vendor:

- Must exist.
- Must be active.
- Must be eligible/relevant to selected item/category if such relation exists.

---

# 9. INVENTORY ANALYSIS

Inventory analysis is deterministic.

## Input

```text
item_id
requested_quantity
```

## Output

```text
available_quantity
requested_quantity
shortage_quantity
coverage_status
```

## Rules

```text
IF available_quantity >= requested_quantity
    coverage_status = SUFFICIENT
    shortage_quantity = 0

ELSE
    coverage_status = INSUFFICIENT
    shortage_quantity =
        requested_quantity - available_quantity
```

## Important

Insufficient inventory is information for decision-making.

It does NOT automatically reject the PR unless a future business rule explicitly changes that.

## UI

Show:

```text
Requested Quantity: 50
Available Inventory: 10
Shortage: 40
Status: Insufficient Inventory
```

---

# 10. DUPLICATE / SIMILAR PR DETECTION

Duplicate detection uses structured database data.

Do NOT use embeddings or semantic search.

## 10.1 Active statuses

For duplicate matching, only PRs in active/non-terminal workflow states count.

Recommended active statuses:

```text
SUBMITTED
UNDER_REVIEW
REVISION_REQUIRED
APPROVED_FOR_RFQ
RFQ_ISSUED
QUOTATION_RECEIVED
VENDOR_SELECTION_PENDING
FINAL_APPROVAL_PENDING
APPROVED
```

Terminal states excluded:

```text
COMPLETED
REJECTED
```

`PO_GENERATED` may be treated as terminal for duplicate purposes because procurement has effectively concluded. Prefer excluding it from duplicate detection.

## 10.2 Matching rule

A potential duplicate exists when:

```text
same item
AND
same department
AND
existing PR is active
AND
quantity similarity threshold is satisfied
```

## 10.3 Default quantity similarity

Use a configurable threshold.

Recommended initial threshold:

**20% quantity difference**

Formula:

```text
difference_percentage =
ABS(existing_quantity - requested_quantity)
/
MAX(requested_quantity, existing_quantity)
× 100
```

Potential duplicate when:

```text
difference_percentage <= 20
```

Exact threshold must be stored as a configurable constant.

## 10.4 Duplicate result

Return:

```text
PR reference
department
item
existing quantity
requested quantity
status
request date
selected vendor if useful
quantity difference percentage
```

## 10.5 UI behavior

If one or more matches exist:

Show a modal/dialog.

The employee must explicitly choose:

```text
Cancel / Go Back
OR
Continue Anyway
```

If continuing, persist:

```text
duplicate_acknowledged = true
```

The system should not silently block the PR merely because a duplicate candidate exists.

---

# 11. VENDOR PERFORMANCE DATA

Survey collection is out of scope.

Assume monthly/internal survey data already exists.

Mock performance data should include:

```text
quality_score
delivery_reliability_score
responsiveness_score
price_competitiveness_score
historical_fulfillment_score
item_specific_score where possible
measurement_period
```

Scores should preferably be on a consistent 0–100 scale.

---

# 12. VENDOR BADGES

Badges are deterministic.

Recommended badge categories:

```text
PREFERRED_VENDOR
HIGH_RELIABILITY
QUALITY_LEADER
COST_EFFICIENT
NEEDS_ATTENTION
```

Suggested rules:

```text
overall_score >= 90
    PREFERRED_VENDOR

delivery_reliability_score >= 90
    HIGH_RELIABILITY

quality_score >= 90
    QUALITY_LEADER

price_competitiveness_score >= 90
    COST_EFFICIENT

overall_score < 60
    NEEDS_ATTENTION
```

A vendor may have multiple badges.

Badge thresholds should be constants/configuration, not hardcoded across unrelated modules.

---

# 13. VENDOR RECOMMENDATION ENGINE

Vendor recommendation begins when the requester selects an item.

It should not wait until quotation stage.

## 13.1 Eligible vendors

Only consider:

- Active vendors.
- Vendors relevant to the selected item/category.
- Vendors with sufficient available performance data.

If item-vendor eligibility is not explicitly modeled, seed an item/category mapping.

## 13.2 Default weighted vendor score

Use an explainable weighted score.

Recommended initial weights:

| Factor | Weight |
|---|---:|
| Quality | 25% |
| Delivery Reliability | 25% |
| Item-Specific Performance | 20% |
| Price Competitiveness | 15% |
| Historical Fulfillment | 10% |
| Responsiveness | 5% |

Formula:

```text
VendorScore =
0.25 × Quality
+
0.25 × DeliveryReliability
+
0.20 × ItemSpecificPerformance
+
0.15 × PriceCompetitiveness
+
0.10 × HistoricalFulfillment
+
0.05 × Responsiveness
```

All factor values should be normalized to 0–100.

## 13.3 Missing factor handling

Do not silently treat missing data as zero if that unfairly destroys the score.

Preferred approach:

1. Calculate score using available eligible factors.
2. Renormalize the weights across available factors.
3. Mark score confidence as reduced if significant data is missing.

Example:

If Responsiveness is missing, redistribute only the available weights proportionally.

## 13.4 Tie-breaking

If scores tie:

1. Higher delivery reliability.
2. Higher quality.
3. Higher item-specific score.
4. More recent performance data.
5. Stable deterministic ordering by vendor ID/name.

## 13.5 Recommendation output

Return:

```text
rank
vendor
overall_score
badge(s)
factor breakdown
short explanation data
score confidence
```

Do not use an LLM to calculate the score.

An LLM may explain the already-calculated result.

---

# 14. INDICATIVE COST ESTIMATION

Purpose:

Give the supervisor an estimated cost before an actual vendor quotation arrives.

It must be clearly labelled:

**Indicative Cost / Estimated Cost**

Never present it as an actual quotation.

## Inputs

Use available structured mock/historical data:

- Historical quotations.
- Historical unit prices.
- Item price history.
- Quantity.
- Vendor history where available.

## Recommended algorithm

For each relevant historical price:

1. Prefer same item.
2. Prefer recent records.
3. Prefer comparable quantity ranges.

Initial simple robust implementation:

```text
estimated_unit_price = median(relevant historical unit prices)
estimated_total_cost =
estimated_unit_price × requested_quantity
```

Optionally improve with recency weighting.

## Output

```text
estimated_unit_price
estimated_total_cost
number_of_reference_records
confidence / data availability indicator
```

---

# 15. SUPERVISOR CHECKING SHEET

This is a dedicated database-backed UI.

It is not Google Sheets.

## Must show

### PR context

- PR reference.
- Requester.
- Department.
- Item.
- Quantity.
- Notes.
- Selected vendor.

### Intelligence

- Inventory status.
- Available quantity.
- Shortage.
- Duplicate matches.
- Vendor recommendations.
- Vendor scores.
- Badges.
- Indicative cost.

### Workflow

- Current status.
- Submission date.
- Revision history.
- Previous review decisions.

### Actions

```text
Approve to Proceed
Return to Requester
View Supporting Details
```

## Return rule

Return requires a mandatory reason.

---

# 16. RFQ WORKFLOW

RFQ is created only after supervisor approval to proceed.

## RFQ creation

RFQ includes:

```text
rfq_id
rfq_reference
purchase_request_id
vendor_id
item
quantity
issued_at
status
```

## Flow

```text
PR approved to proceed
        ↓
Create RFQ
        ↓
Assign vendor
        ↓
Persist RFQ
        ↓
Create notification
        ↓
Attempt automatic email
```

Email failure must not roll back the RFQ transaction.

---

# 17. VENDOR PORTAL

Vendor dashboard should show:

- Assigned RFQs.
- Pending RFQs.
- Submitted quotations.
- Relevant statuses.

RFQ detail page should show:

- RFQ reference.
- Item.
- Quantity.
- Issue date.
- Optional due date.

---

# 18. QUOTATION SUBMISSION

## Required fields

```text
quoted_unit_price
lead_time
```

## Derived/validated

```text
total_price = quoted_unit_price × requested_quantity
```

Optional:

```text
validity_period
notes
quotation_document
```

Validation:

- Unit price > 0.
- Lead time > 0 if measured numerically.
- Vendor must own the RFQ.
- RFQ must accept submission.

Persist submission timestamp.

---

# 19. QUOTATION EVALUATION

Quotation evaluation is analytical and separate from pre-request vendor recommendation.

Do not select the lowest quotation automatically.

## Default weighted quotation score

Recommended weights:

| Factor | Weight |
|---|---:|
| Price Competitiveness | 40% |
| Delivery Lead Time | 20% |
| Vendor Reliability | 20% |
| Quality Performance | 20% |

Formula:

```text
QuotationScore =
0.40 × PriceScore
+
0.20 × DeliveryScore
+
0.20 × ReliabilityScore
+
0.20 × QualityScore
```

## Price score

For valid quotes:

```text
PriceScore =
LowestValidQuote
/
VendorQuote
× 100
```

## Delivery score

```text
DeliveryScore =
ShortestValidLeadTime
/
VendorLeadTime
× 100
```

## Reliability score

Use normalized vendor delivery/historical reliability.

## Quality score

Use normalized vendor quality performance.

## Output

Return:

```text
vendor
quoted unit price
total quoted price
lead time
price score
delivery score
reliability score
quality score
final weighted score
rank
recommended vendor
```

## Ties

Tie-break:

1. Higher overall vendor reliability.
2. Better delivery score.
3. Lower price.
4. Stable deterministic vendor ordering.

---

# 20. FINAL VENDOR SELECTION AND OVERRIDE

The analytical engine recommends a vendor.

The supervisor makes the final decision.

## If recommended vendor is selected

No override reason required.

## If another vendor is selected

Require:

```text
override_reason
```

The system must:

- Reject submission without reason.
- Persist recommended vendor.
- Persist selected vendor.
- Persist supervisor.
- Persist reason.
- Audit the decision.

---

# 21. FINAL APPROVAL

Final approval requires:

1. PR is at the correct workflow stage.
2. At least one valid quotation exists.
3. Final vendor is selected.
4. Override reason exists if recommendation was overridden.
5. Supervisor is authorized.

Only then may final approval succeed.

---

# 22. PURCHASE ORDER GENERATION

PO generation happens only after final approval.

## Idempotency requirement

PO generation must not create duplicate POs if retried.

Recommended approach:

- Unique constraint on PR-to-final-PO relationship.
- Transactional creation.
- Return existing PO when appropriate.

## PO flow

```text
Final approval
      ↓
Validate prerequisites
      ↓
Generate unique PO number
      ↓
Create PO database record
      ↓
Generate PDF
      ↓
Save locally
      ↓
Update PO path/status
      ↓
Create notification
      ↓
Attempt email
```

## PO PDF fields

Include:

- PO number.
- Generation date.
- PR reference.
- Vendor.
- Item.
- Quantity.
- Unit price.
- Total amount.
- Lead/delivery information if available.
- Approval reference.

---

# 23. NOTIFICATIONS AND EMAILS

Use event-oriented internal services without requiring a separate message broker.

## Notification events

```text
PR_SUBMITTED
PR_RETURNED
PR_APPROVED_TO_PROCEED
RFQ_ISSUED
QUOTATION_SUBMITTED
VENDOR_SELECTED
FINAL_APPROVAL_COMPLETED
PO_GENERATED
```

## In-app notifications

Persist in database.

Fields:

```text
id
user_id
type
title
message
is_read
related_entity_type
related_entity_id
created_at
```

## Email

Implement an abstraction:

```text
EmailService
├── DevelopmentLoggerProvider
├── SMTPProvider
└── FutureProvider
```

For local hackathon development, logging/mock delivery is acceptable if real SMTP credentials are unavailable.

Core transaction must succeed even if email delivery fails.

---

# 24. DATABASE BLUEPRINT

Use UUID primary keys unless there is a strong reason otherwise.

## users

```text
id UUID PK
name VARCHAR
email VARCHAR UNIQUE
password_hash VARCHAR
role ENUM
department_id UUID FK NULLABLE
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
```

## departments

```text
id UUID PK
name VARCHAR UNIQUE
created_at TIMESTAMP
```

## department_supervisors

Allows explicit department-to-supervisor mapping.

```text
department_id UUID FK
supervisor_id UUID FK
```

For simplicity, one primary supervisor per department is sufficient.

## items

```text
id UUID PK
name VARCHAR
description TEXT NULLABLE
category VARCHAR
unit VARCHAR
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
```

## inventory

```text
id UUID PK
item_id UUID FK UNIQUE
available_quantity NUMERIC
updated_at TIMESTAMP
```

## vendors

```text
id UUID PK
name VARCHAR
email VARCHAR
phone VARCHAR NULLABLE
is_active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
```

## vendor_item_categories / vendor_item_mapping

Use a mapping to establish eligibility.

```text
vendor_id UUID FK
item_id UUID FK OR category
```

Choose the simplest model supporting seeded recommendations.

## vendor_performance

```text
id UUID PK
vendor_id UUID FK
measurement_period DATE
quality_score NUMERIC
delivery_reliability_score NUMERIC
responsiveness_score NUMERIC
price_competitiveness_score NUMERIC
historical_fulfillment_score NUMERIC
created_at TIMESTAMP
```

## vendor_item_performance

```text
id UUID PK
vendor_id UUID FK
item_id UUID FK
item_specific_score NUMERIC
measurement_period DATE
```

## vendor_score_snapshots

Optional persistence for explainability/history.

```text
id UUID PK
vendor_id UUID FK
overall_score NUMERIC
quality_component NUMERIC
delivery_component NUMERIC
item_component NUMERIC
price_component NUMERIC
fulfillment_component NUMERIC
responsiveness_component NUMERIC
calculated_at TIMESTAMP
```

## vendor_badges

```text
id UUID PK
vendor_id UUID FK
badge_type ENUM/VARCHAR
awarded_at TIMESTAMP
```

## purchase_requests

```text
id UUID PK
reference_number VARCHAR UNIQUE
requester_id UUID FK
department_id UUID FK
selected_vendor_id UUID FK
status ENUM
notes TEXT NULLABLE
duplicate_acknowledged BOOLEAN DEFAULT FALSE
created_at TIMESTAMP
updated_at TIMESTAMP
```

## purchase_request_items

Design for future extensibility even if MVP has one item.

```text
id UUID PK
purchase_request_id UUID FK
item_id UUID FK
quantity NUMERIC
```

For MVP, enforce one item per PR if desired.

## purchase_request_reviews

```text
id UUID PK
purchase_request_id UUID FK
supervisor_id UUID FK
decision VARCHAR
reason TEXT NULLABLE
created_at TIMESTAMP
```

## historical_prices

Supports indicative estimation.

```text
id UUID PK
item_id UUID FK
vendor_id UUID FK NULLABLE
unit_price NUMERIC
quantity NUMERIC
recorded_at TIMESTAMP
```

## rfqs

```text
id UUID PK
reference_number VARCHAR UNIQUE
purchase_request_id UUID FK
vendor_id UUID FK
status VARCHAR
issued_at TIMESTAMP
due_at TIMESTAMP NULLABLE
```

## quotations

```text
id UUID PK
rfq_id UUID FK
vendor_id UUID FK
quoted_unit_price NUMERIC
total_price NUMERIC
lead_time_days INTEGER
validity_period VARCHAR NULLABLE
notes TEXT NULLABLE
document_path VARCHAR NULLABLE
submitted_at TIMESTAMP
```

## vendor_selection_decisions

```text
id UUID PK
purchase_request_id UUID FK
recommended_vendor_id UUID FK
selected_vendor_id UUID FK
supervisor_id UUID FK
override_reason TEXT NULLABLE
created_at TIMESTAMP
```

## purchase_orders

```text
id UUID PK
po_number VARCHAR UNIQUE
purchase_request_id UUID FK UNIQUE
vendor_id UUID FK
quotation_id UUID FK
approved_amount NUMERIC
status VARCHAR
pdf_path VARCHAR NULLABLE
generated_at TIMESTAMP
```

## notifications

As specified above.

## audit_logs

```text
id UUID PK
actor_id UUID FK NULLABLE
action VARCHAR
entity_type VARCHAR
entity_id UUID
previous_state JSONB NULLABLE
new_state JSONB NULLABLE
metadata JSONB NULLABLE
created_at TIMESTAMP
```

## knowledge_documents

```text
id UUID PK
title VARCHAR
original_filename VARCHAR
file_path VARCHAR
document_type VARCHAR
processing_status VARCHAR
uploaded_at TIMESTAMP
```

## knowledge_chunks

```text
id UUID PK
document_id UUID FK
chunk_index INTEGER
content TEXT
embedding VECTOR(...)
metadata JSONB
```

---

# 25. BACKEND MODULE RESPONSIBILITIES

Suggested structure:

```text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── models/
│   ├── schemas/
│   ├── modules/
│   │   ├── auth/
│   │   ├── users/
│   │   ├── departments/
│   │   ├── catalog/
│   │   ├── inventory/
│   │   ├── vendors/
│   │   ├── procurement/
│   │   ├── rfq/
│   │   ├── quotations/
│   │   └── purchase_orders/
│   ├── intelligence/
│   │   ├── deterministic/
│   │   └── analytical/
│   ├── ai/
│   │   ├── providers/
│   │   ├── embeddings/
│   │   ├── rag/
│   │   └── copilot/
│   ├── notifications/
│   ├── email/
│   └── audit/
├── alembic/
├── storage/
└── tests/
```

## Important services

### InventoryService

Input:

```text
item_id
quantity
```

Output:

```text
availability analysis
```

### DuplicateDetectionService

Input:

```text
item_id
department_id
quantity
```

Output:

```text
similar active PRs
```

### VendorRecommendationService

Input:

```text
item_id
```

Output:

```text
ranked eligible vendors
factor breakdown
badges
```

### IndicativeCostService

Input:

```text
item_id
quantity
```

Output:

```text
estimated unit price
estimated total
confidence/basis
```

### QuotationEvaluationService

Input:

```text
purchase_request_id or quotation collection
```

Output:

```text
factor scores
weighted ranking
recommended vendor
```

### ProcurementWorkflowService

Responsible for:

- Validating transitions.
- Routing.
- Creating review records.
- Preventing invalid actions.

Do not scatter workflow transition logic randomly across routes.

---

# 26. API BLUEPRINT

Exact URL naming may vary slightly, but maintain consistent REST semantics.

## Authentication

```text
POST /auth/login
GET  /auth/me
```

## Items

```text
GET /items
GET /items/{id}
```

## Inventory

```text
GET /inventory/items/{item_id}
```

## Vendors

```text
GET /vendors
GET /vendors/{id}
GET /vendors/recommendations?item_id={id}
```

## Purchase Requests

```text
POST /purchase-requests
GET  /purchase-requests
GET  /purchase-requests/{id}
PUT/PATCH /purchase-requests/{id}
POST /purchase-requests/{id}/submit
POST /purchase-requests/{id}/return
POST /purchase-requests/{id}/approve-to-proceed
GET /purchase-requests/{id}/analysis
```

## RFQs

```text
GET /rfqs
GET /rfqs/{id}
POST /rfqs/{id}/issue
```

## Quotations

```text
POST /rfqs/{id}/quotations
GET  /purchase-requests/{id}/quotation-analysis
```

## Final selection

```text
POST /purchase-requests/{id}/vendor-selection
POST /purchase-requests/{id}/final-approval
```

## PO

```text
POST /purchase-requests/{id}/purchase-order
GET  /purchase-orders
GET  /purchase-orders/{id}
GET  /purchase-orders/{id}/document
```

## Notifications

```text
GET /notifications
POST /notifications/{id}/read
```

## Knowledge

```text
POST /knowledge/documents
GET  /knowledge/documents
POST /knowledge/query
```

## AI

```text
POST /ai/chat
POST /ai/summarize/pr/{id}
POST /ai/explain/vendor-recommendation/{id}
POST /ai/explain/quotation-analysis/{id}
```

---

# 27. KEY API CONTRACT EXAMPLES

## Create PR

Request:

```json
{
  "item_id": "UUID",
  "quantity": 50,
  "selected_vendor_id": "UUID",
  "notes": "Optional justification"
}
```

Response should include enough immediate intelligence for frontend flow:

```json
{
  "id": "UUID",
  "reference_number": "PR-2026-000001",
  "status": "SUBMITTED",
  "inventory_analysis": {
    "requested_quantity": 50,
    "available_quantity": 10,
    "shortage_quantity": 40,
    "coverage_status": "INSUFFICIENT"
  },
  "duplicate_matches": [],
  "selected_vendor": {},
  "vendor_recommendation": {}
}
```

The frontend may also call analysis endpoints before final submission for a smoother experience.

## Vendor selection

```json
{
  "selected_vendor_id": "UUID",
  "override_reason": "Required only when selected vendor differs from recommendation"
}
```

Backend rule:

- If selected == recommended → override reason optional/null.
- If selected != recommended → reject missing/blank reason.

---

# 28. FRONTEND PAGE BLUEPRINT

## Shared application shell

```text
Sidebar / Navigation
├── Dashboard
├── Procurement
├── RFQs
├── Quotations
├── Purchase Orders
├── Notifications
└── AI Assistant

Top Bar
├── Page title
├── Notifications
└── User profile
```

Adapt navigation by role.

## Employee Dashboard

Show:

- Active PR count.
- Pending review count.
- Revision-required count.
- Recent PRs.
- Quick Create PR action.
- Status distribution if useful.
- Notifications.

## Create PR Page

Recommended sequence:

```text
1. Item Selection
2. Quantity
3. Live Intelligence
   ├── Inventory
   ├── Duplicate Warning
   └── Vendor Recommendations
4. Vendor Selection
5. Notes
6. Review and Submit
```

Vendor cards should show:

- Rank.
- Vendor name.
- Overall score.
- Badge(s).
- Major strengths.
- Score breakdown.

## Duplicate Dialog

Show:

- Why it was flagged.
- Matching PRs.
- Relevant details.

Actions:

```text
Go Back
Continue Anyway
```

## Supervisor Dashboard

Show:

- Pending reviews.
- PRs requiring action.
- Awaiting quotations.
- Final approval queue.
- Recent decisions.

## Checking Sheet Page

Use sections:

```text
Request Summary
Inventory Analysis
Potential Duplicate Requests
Vendor Recommendation
Indicative Cost
Workflow History
Decision Actions
```

## Quotation Comparison

Table/cards showing:

- Vendor.
- Quote.
- Lead time.
- Price score.
- Delivery score.
- Reliability.
- Quality.
- Final score.
- Recommendation.

Clearly identify:

```text
System Recommended Vendor
```

## Final Decision Dialog

If selecting non-recommended vendor:

```text
Warning:
You are selecting a vendor different from the system recommendation.

Reason for override: [required text field]
```

## Vendor Dashboard

Show:

- Pending RFQs.
- Submitted quotations.
- RFQ cards/table.

## AI Assistant

Support:

- Chat panel.
- Contextual action buttons.

Example buttons:

```text
Summarize this PR
Explain vendor recommendation
Explain duplicate warning
Explain quotation comparison
Ask procurement policy
```

---

# 29. ANALYTICAL VS LLM RESPONSIBILITY TABLE

| Capability | Deterministic | Analytical | LLM |
|---|---:|---:|---:|
| Input validation | Yes | No | No |
| Inventory | Yes | No | No |
| Duplicate detection | Yes | No | No |
| Vendor score | No | Yes | No |
| Vendor recommendation | No | Yes | Explanation only |
| Indicative cost | No | Yes | Explanation only |
| Workflow transition | Yes | No | No |
| Quotation ranking | No | Yes | Explanation only |
| PR summary | Structured data source | Optional | Yes |
| Policy question | No | RAG retrieval | Yes |
| Final approval | Human workflow | Support only | No |

---

# 30. RAG ARCHITECTURE

Use RAG for unstructured organizational knowledge.

Examples:

- Procurement policies.
- SOPs.
- Approval guidelines.
- Vendor management guidelines.
- Internal procurement documentation.

Do NOT use RAG for normal transactional retrieval.

For example:

```text
"What is the status of PR-123?"
```

Should query PostgreSQL.

```text
"What does the procurement policy say about vendor selection?"
```

Should use RAG.

## Ingestion pipeline

```text
Upload
  ↓
Validate file
  ↓
Extract text
  ↓
Clean text
  ↓
Chunk text
  ↓
Generate embeddings
  ↓
Store chunks + embeddings in pgvector
```

Supported MVP files:

- PDF.
- DOCX.
- TXT.

## Retrieval

```text
Question
  ↓
Classify intent / route
  ↓
If knowledge question:
  generate question embedding
  ↓
pgvector similarity search
  ↓
retrieve top relevant chunks
  ↓
construct grounded context
  ↓
LLM answer
```

## No-answer behavior

If no sufficiently relevant context exists:

Do not invent policy.

Return a response equivalent to:

> The available knowledge base does not contain enough information to answer this confidently.

---

# 31. CONTEXTUAL COPILOT ROUTING

The copilot should receive context from the current page/entity where possible.

Example:

On PR detail page:

```text
Context:
PR data
inventory analysis
duplicate matches
vendor recommendation
workflow history
```

The LLM can explain this context.

It should not independently query arbitrary application state without authorization.

## Routing logic

```text
User question
    │
    ├── Structured operational question
    │       ↓
    │   Authorized PostgreSQL/service retrieval
    │       ↓
    │   Optional LLM explanation
    │
    └── Policy/knowledge question
            ↓
           RAG
            ↓
           LLM
```

---

# 32. LLM PROVIDER ABSTRACTION

Define interfaces such as:

```text
generate_text(...)
generate_structured_response(...)
health_check(...)
```

Embedding provider should be independently abstracted where practical.

The application must support:

```text
AI_ENABLED=true/false
```

If disabled:

- Hide or gracefully disable AI-only actions.
- Preserve all procurement features.

---

# 33. ERROR HANDLING

## Authentication

Handle:

- Invalid credentials.
- Missing token.
- Expired token.
- Invalid token.
- Unauthorized role.

## Validation

Handle:

- Unknown item.
- Unknown vendor.
- Inactive vendor.
- Invalid quantity.
- Invalid quotation.
- Missing return reason.
- Missing override reason.

## Workflow

Handle:

- Invalid transition.
- Unauthorized decision.
- Duplicate final approval.
- PO generation before approval.

## Files

Handle:

- Unsupported knowledge document.
- Extraction failure.
- Storage failure.
- PDF generation failure.

## AI

Handle:

- LLM unavailable.
- Embedding unavailable.
- RAG retrieval failure.
- Empty knowledge base.
- Timeout.

AI failure must not affect core procurement state.

---

# 34. AUDIT REQUIREMENTS

Audit these actions:

```text
PR_CREATED
PR_SUBMITTED
PR_RETURNED
PR_RESUBMITTED
PR_APPROVED_TO_PROCEED
RFQ_ISSUED
QUOTATION_SUBMITTED
VENDOR_RECOMMENDED
VENDOR_SELECTED
VENDOR_OVERRIDE
FINAL_APPROVED
PO_GENERATED
```

Record:

- Actor.
- Action.
- Entity.
- Timestamp.
- Relevant state.
- Reason where applicable.

---

# 35. MOCK DATA REQUIREMENTS

Seed sufficient data to demonstrate every feature.

## Users

- Multiple employees.
- Multiple departments.
- At least one supervisor per department.
- Multiple vendor accounts.

## Items

At least 10–20 realistic procurement items.

## Inventory

Include:

- Sufficient stock.
- Exact stock.
- Low stock.
- Zero stock.

## Vendors

At least 5 vendors with visibly different strengths.

Example profiles:

- High quality/high reliability.
- Cheapest but low reliability.
- Fast delivery.
- Strong all-rounder.
- Low-performing vendor.

## PRs

Seed:

- Active PRs matching same item/department.
- Similar quantities.
- Completed PRs that must not trigger duplicate detection.
- Rejected PRs that must not trigger duplicate detection.
- Returned PR.
- RFQ-stage PR.
- Quotation-stage PR.
- Completed PO.

## Historical pricing

Enough data for indicative cost calculation.

## Knowledge documents

Seed several mock procurement policies/SOP documents.

---

# 36. TEST SCENARIOS

The agent should verify these end-to-end scenarios.

## Scenario A — Normal PR

Employee:

1. Selects item.
2. Enters quantity.
3. Sees sufficient inventory.
4. Sees vendor recommendations.
5. Selects vendor.
6. No duplicate.
7. Submits.

Supervisor:

8. Reviews.
9. Approves to proceed.

Vendor:

10. Receives RFQ.
11. Submits quotation.

Supervisor:

12. Reviews evaluation.
13. Selects recommended vendor.
14. Final approves.

System:

15. Generates PO.

## Scenario B — Duplicate

Create a similar active PR.

Create another PR with:

- Same item.
- Same department.
- Quantity within threshold.

Verify:

- Alert appears.
- Matching details are visible.
- User can continue intentionally.

## Scenario C — Terminal PR exclusion

Create completed/rejected PR.

Create matching new PR.

Verify it is not treated as active duplicate.

## Scenario D — Inventory shortage

Request quantity > stock.

Verify:

- Available quantity.
- Shortage.
- Insufficient status.

Verify PR can still proceed unless another explicit rule blocks it.

## Scenario E — Returned PR

Supervisor returns PR with reason.

Verify:

- Employee sees reason.
- Can edit/revise.
- Can resubmit.
- Workflow returns correctly.

## Scenario F — Vendor override

System recommends Vendor A.

Supervisor selects Vendor B.

Verify:

- Reason required.
- Missing reason rejected.
- Valid reason stored/audited.

## Scenario G — LLM unavailable

Disable AI provider.

Verify:

- PR creation works.
- Recommendations work.
- Inventory works.
- RFQ works.
- Quotation evaluation works.
- PO works.

## Scenario H — RAG

Upload procurement policy.

Ask policy question.

Verify answer is based on retrieved context.

Ask unsupported question.

Verify system does not invent an answer.

---

# 37. IMPLEMENTATION ORDER FOR AUTONOMOUS CODING AGENT

## PHASE 1 — Foundation

Build:

1. Repository structure.
2. Frontend.
3. FastAPI backend.
4. PostgreSQL connection.
5. Alembic.
6. Environment configuration.
7. Local storage.

Verify application runs.

## PHASE 2 — Authentication and RBAC

Build:

- Users.
- Roles.
- JWT.
- Login.
- Protected routes.

Verify all roles.

## PHASE 3 — Core Data and Mock Data

Build:

- Departments.
- Items.
- Inventory.
- Vendors.
- Performance data.
- Historical pricing.

Create deterministic seeds.

## PHASE 4 — Purchase Request Workflow

Build:

- PR creation.
- State machine.
- Department supervisor routing.
- Review.
- Return.
- Resubmission.

Test transitions.

## PHASE 5 — Deterministic Intelligence

Build:

- Inventory analysis.
- Duplicate detection.
- Duplicate dialog/API.

Test all edge cases.

## PHASE 6 — Analytical Intelligence

Build:

- Vendor scoring.
- Badge generation.
- Recommendations.
- Indicative cost.
- Checking sheet.

Verify reproducibility.

## PHASE 7 — RFQ and Vendor Portal

Build:

- RFQ generation.
- Assignment.
- Vendor dashboard.
- Quotation submission.

## PHASE 8 — Quotation Evaluation

Build:

- Factor scoring.
- Ranking.
- Recommendation.
- Override handling.

## PHASE 9 — Final Approval and PO

Build:

- Prerequisite validation.
- Final approval.
- Idempotent PO generation.
- PDF.
- Local storage.

## PHASE 10 — Notifications and Audit

Build:

- In-app notifications.
- Email abstraction.
- Audit logging.

## PHASE 11 — AI/RAG

Build last:

- Provider abstraction.
- AI summaries.
- Copilot.
- Knowledge ingestion.
- Embeddings.
- pgvector retrieval.
- RAG.

---

# 38. AGENT EXECUTION RULES

The autonomous coding agent must NOT attempt an uncontrolled one-shot build.

For every phase:

```text
1. Inspect current repository state.
2. Implement only the current phase.
3. Run backend.
4. Run frontend.
5. Run migrations.
6. Fix compilation/runtime errors.
7. Verify relevant API behavior.
8. Verify relevant UI flow.
9. Continue only after phase works.
```

## Preserve working code

Before major refactors:

- Inspect existing implementation.
- Reuse stable components.
- Avoid replacing working modules unnecessarily.

## Avoid scope drift

Do not add features merely because they seem interesting.

Prioritize:

```text
Correct workflow
→ Data integrity
→ Business intelligence
→ UI quality
→ AI enhancement
```

---

# 39. DEFINITION OF DONE

The project is complete when the following can be demonstrated locally from start to finish:

```text
1. Employee logs in.
2. Employee creates structured PR.
3. Inventory analysis appears.
4. Duplicate PR detection works.
5. Vendor recommendation appears.
6. Employee selects vendor.
7. PR routes to department supervisor.
8. Supervisor reviews checking sheet.
9. Supervisor can return with reason.
10. Employee can revise and resubmit.
11. Supervisor approves to proceed.
12. RFQ is created.
13. Vendor sees RFQ.
14. Vendor submits quotation.
15. Supervisor sees weighted quotation comparison.
16. System recommends vendor.
17. Supervisor can confirm or override.
18. Override requires reason.
19. Supervisor final approves.
20. PO is generated once.
21. PO PDF is stored locally and accessible.
22. Notifications are generated.
23. Emails are attempted through configured provider.
24. AI can summarize/explain when enabled.
25. RAG answers knowledge questions using pgvector.
26. Core procurement workflow still works with AI disabled.
```

---

# 40. NON-GOALS

Do not build unless explicitly requested later:

- Survey collection workflow.
- Complex demand prediction.
- Forecasting ML models.
- Autonomous procurement approval.
- Autonomous vendor selection.
- Free-text semantic PR creation.
- Google Sheets workflow.
- Company-specific ERP integration.
- Payment systems.
- Cloud deployment.
- Kubernetes.
- Microservices.
- Separate vector database.
- LangChain.

---

# 41. FINAL PRIORITY ORDER

```text
P0 — Must work
Authentication
RBAC
PR workflow
Inventory
Duplicate detection
Supervisor approval/return
RFQ
Quotation
Final vendor selection
Final approval
PO

P1 — Strong competitive intelligence
Vendor scoring
Badges
Recommendations
Indicative cost
Weighted quotation evaluation
Override auditing

P2 — Operational polish
Notifications
Emails
Audit logs
Professional UI
Analytics

P3 — AI enhancement
Summaries
Explanations
Copilot
RAG
```

---

# 42. FINAL IMPLEMENTATION INSTRUCTION

Build the system as a cohesive intelligent procurement application.

The strongest solution is not the one with the most AI.

The strongest solution is the one where:

- The entire procurement journey works.
- Every workflow transition is correct.
- Every important decision is explainable.
- Duplicate and inventory intelligence appears before decisions.
- Vendor recommendations are analytical and reproducible.
- Lowest quotation is not blindly selected.
- Humans retain final authority.
- PO generation is protected by prerequisites.
- AI improves understanding without becoming a failure point.
- RAG is used only where unstructured knowledge retrieval is appropriate.

**When uncertain, prefer correctness, simplicity, deterministic behavior, and demonstrable end-to-end functionality over unnecessary architectural complexity.**
