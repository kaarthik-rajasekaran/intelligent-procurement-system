import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.entities import PurchaseRequest, PurchaseOrder, RFQ, Quotation, Vendor, Item, Inventory, KnowledgeChunk
from app.schemas.domain import AIChatRequest, AIChatResponse, AISummaryResponse
from app.ai.provider import get_llm_provider
from app.intelligence.analytical import get_vendor_recommendations, evaluate_quotations
from app.intelligence.deterministic import analyze_inventory
from app.ai.rag import query_knowledge_rag
from app.api.deps import get_current_user

router = APIRouter(prefix="/ai", tags=["AI Copilot & Explanations"])

def build_copilot_context(db: Session, message: str, context_type: str = None, context_id: str = None) -> str:
    """
    Intelligently inspects the user message and environment to pull all relevant
    Purchase Orders, Purchase Requests, RFQs, Vendor, and Policy records into the LLM context.
    """
    context_sections = []
    msg_upper = message.upper()

    # 1. PO Extraction & Lookup
    po_matches = re.findall(r'PO-[\w-]+', msg_upper)
    if po_matches:
        for po_num in po_matches:
            po = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.ilike(f"%{po_num}%")).first()
            if po:
                pr = po.purchase_request
                pr_item = pr.items[0] if (pr and pr.items) else None
                vendor = po.vendor
                context_sections.append(
                    f"[SPECIFIC PURCHASE ORDER RECORD MATCHED]\n"
                    f"• PO Number: {po.po_number}\n"
                    f"• PR Reference: {pr.reference_number if pr else 'N/A'}\n"
                    f"• Awarded Supplier / Vendor: {vendor.name if vendor else 'Unknown'} ({vendor.email if vendor else 'N/A'})\n"
                    f"• Item Description: {pr_item.item.name if (pr_item and pr_item.item) else 'N/A'}\n"
                    f"• Quantity: {pr_item.quantity if pr_item else 'N/A'} {pr_item.item.unit if (pr_item and pr_item.item) else 'units'}\n"
                    f"• Total Approved Amount: ${float(po.approved_amount):,.2f}\n"
                    f"• Order Status: {po.status}\n"
                    f"• Issue Date: {po.generated_at.strftime('%Y-%m-%d %H:%M') if po.generated_at else 'N/A'}\n"
                )

    # 2. PR Extraction & Lookup
    pr_matches = re.findall(r'PR-[\w-]+', msg_upper)
    if pr_matches or (context_type == "pr" and context_id):
        target_refs = pr_matches[:]
        if context_id and not target_refs:
            try:
                pr_obj = db.query(PurchaseRequest).filter(PurchaseRequest.id == uuid.UUID(context_id)).first()
                if pr_obj:
                    target_refs.append(pr_obj.reference_number)
            except Exception:
                pass

        for ref in target_refs:
            pr = db.query(PurchaseRequest).filter(PurchaseRequest.reference_number.ilike(f"%{ref}%")).first()
            if pr:
                pr_item = pr.items[0] if pr.items else None
                vendor = pr.selected_vendor
                po = db.query(PurchaseOrder).filter(PurchaseOrder.purchase_request_id == pr.id).first()
                context_sections.append(
                    f"[PURCHASE REQUEST RECORD MATCHED]\n"
                    f"• Reference Number: {pr.reference_number}\n"
                    f"• Requester: {pr.requester.name if pr.requester else 'Unknown'} ({pr.department.name if pr.department else 'N/A'})\n"
                    f"• Status: {pr.status}\n"
                    f"• Selected / Awarded Supplier: {vendor.name if vendor else 'None'}\n"
                    f"• Item: {pr_item.item.name if (pr_item and pr_item.item) else 'N/A'}\n"
                    f"• Quantity: {pr_item.quantity if pr_item else 'N/A'} {pr_item.item.unit if (pr_item and pr_item.item) else 'units'}\n"
                    f"• Related PO: {po.po_number if po else 'None generated yet'}\n"
                    f"• Notes: {pr.notes or 'None'}\n"
                )

    # 3. Always include a concise snapshot of all Recent Purchase Orders in the system
    #    so general questions ("what orders exist?", "who is the supplier for order X?") are always answered accurately!
    recent_pos = db.query(PurchaseOrder).order_by(PurchaseOrder.generated_at.desc()).limit(15).all()
    if recent_pos:
        po_lines = []
        for p in recent_pos:
            pr_it = p.purchase_request.items[0] if (p.purchase_request and p.purchase_request.items) else None
            it_name = pr_it.item.name if (pr_it and pr_it.item) else "Item"
            qty = pr_it.quantity if pr_it else "N/A"
            v_name = p.vendor.name if p.vendor else "Vendor"
            po_lines.append(
                f"• {p.po_number} | Supplier: {v_name} | Amount: ${float(p.approved_amount):,.2f} | Item: {qty}x {it_name} | PR Ref: {p.purchase_request.reference_number if p.purchase_request else 'N/A'} | Status: {p.status}"
            )
        context_sections.append("[ACTIVE ENTERPRISE PURCHASE ORDERS ON RECORD]\n" + "\n".join(po_lines))

    # 4. Check for Policy / Guideline / Threshold queries
    policy_keywords = ['policy', 'threshold', 'approval', 'guideline', 'limit', 'rules', 'compliance', 'supervisor']
    if any(k in message.lower() for k in policy_keywords):
        try:
            chunks = db.query(KnowledgeChunk).limit(4).all()
            if chunks:
                policy_text = "\n---\n".join([c.content[:400] for c in chunks])
                context_sections.append(f"[CORPORATE PROCUREMENT POLICY EXCERPTS]\n{policy_text}")
        except Exception:
            pass

    return "\n\n".join(context_sections)

@router.post("/chat", response_model=AIChatResponse)
def ai_copilot_chat(
    chat_in: AIChatRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not settings.AI_ENABLED:
        return AIChatResponse(
            reply="AI Copilot is currently offline (Deterministic intelligence mode active).",
            context_used="None"
        )

    llm = get_llm_provider()
    retrieved_context = build_copilot_context(
        db=db,
        message=chat_in.message,
        context_type=chat_in.context_type,
        context_id=chat_in.context_id
    )

    system_prompt = (
        f"You are the Enterprise Intelligent Procurement Copilot for {settings.PROJECT_NAME}.\n"
        f"Active User: {current_user.name} (Role: {current_user.role}).\n\n"
        "You have direct real-time access to official database records and company procurement guidelines provided in the context below.\n"
        "RULES:\n"
        "1. Answer questions directly, factually, and professionally using the provided records.\n"
        "2. If asked about a Purchase Order (e.g. PO-...), Purchase Request (PR-...), or RFQ, state the exact details (awarded supplier name, item description, quantity, amount, and status) clearly.\n"
        "3. Never state that you lack information if the PO or record is listed in the provided context records.\n"
        "4. Format key numbers and names in bold for executive readability."
    )

    full_prompt = (
        f"ENTERPRISE PROCUREMENT DATABASE RECORDS:\n"
        f"{retrieved_context}\n\n"
        f"USER QUESTION: {chat_in.message}\n\n"
        "Provide a helpful, precise, grounded answer."
    )

    reply = llm.generate_text(prompt=full_prompt, system_prompt=system_prompt)
    return AIChatResponse(reply=reply, context_used=retrieved_context[:500] if retrieved_context else "None")

@router.post("/summarize/pr/{pr_id}", response_model=AISummaryResponse)
def summarize_purchase_request(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase Request not found.")

    pr_item = pr.items[0] if pr.items else None
    item_name = pr_item.item.name if (pr_item and pr_item.item) else "Item"
    item_desc = pr_item.item.description if (pr_item and pr_item.item) else ""
    qty = float(pr_item.quantity) if pr_item else 1.0

    inv = analyze_inventory(db, pr_item.item_id, qty) if pr_item else None
    vendor_name = pr.selected_vendor.name if pr.selected_vendor else "Selected Vendor"

    llm = get_llm_provider()
    prompt = (
        f"Purchase Request Reference: {pr.reference_number}\n"
        f"Requester: {pr.requester.name if pr.requester else 'Unknown'} (Department: {pr.department.name if pr.department else 'General'})\n"
        f"Status: {pr.status}\n"
        f"Item Requested: {qty:g}x {item_name} ({item_desc})\n"
        f"Assigned Supplier: {vendor_name}\n"
        f"Inventory Check: Available Stock = {inv.available_quantity if inv else 0:g}, Shortage = {inv.shortage_quantity if inv else 0:g}, Status = {inv.coverage_status if inv else 'UNKNOWN'}\n"
        f"Requester Notes: {pr.notes or 'None'}\n"
        f"Duplicate Acknowledged: {pr.duplicate_acknowledged}\n\n"
        "Generate a 2-3 sentence professional executive summary of this purchase request, highlighting urgency, inventory coverage, and supplier assignment."
    )

    try:
        summary_text = llm.generate_text(
            prompt=prompt,
            system_prompt="You are an enterprise procurement analyst. Write clear, factual, executive-level summaries."
        )
    except Exception:
        summary_text = (
            f"Purchase Request {pr.reference_number} submitted by {pr.requester.name} for {qty:g} {item_name} "
            f"assigned to {vendor_name}. Current workflow stage is '{pr.status}'. "
            f"Inventory reserve check indicates {inv.coverage_status if inv else 'N/A'} availability "
            f"(Available: {inv.available_quantity if inv else 0:g}, Shortage: {inv.shortage_quantity if inv else 0:g})."
        )

    highlights = [
        f"Workflow Stage: {pr.status}",
        f"Item Requested: {qty:g}x {item_name}",
        f"Inventory Coverage: {inv.coverage_status if inv else 'UNKNOWN'}",
        f"Selected Supplier: {vendor_name}"
    ]

    risks = []
    if inv and inv.coverage_status == "INSUFFICIENT":
        risks.append(f"Warehouse shortage of {inv.shortage_quantity:g} units requires external fulfillment.")
    if pr.duplicate_acknowledged:
        risks.append("Requester flagged and acknowledged a potential duplicate PR match in this department.")
    if not risks:
        risks.append("Standard procurement order adhering to corporate operational thresholds.")

    return AISummaryResponse(
        summary=summary_text,
        key_highlights=highlights,
        risks_or_notes=risks
    )

@router.post("/explain/vendor-recommendation/{pr_id}")
def explain_vendor_recommendation(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    pr = db.query(PurchaseRequest).filter(PurchaseRequest.id == pr_id).first()
    if not pr or not pr.items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PR or line item not found.")

    recs = get_vendor_recommendations(db, pr.items[0].item_id)
    if not recs:
        return {"explanation": "No vendor recommendations available for this item."}

    top_rec = recs[0]
    llm = get_llm_provider()
    prompt = (
        f"Item: {pr.items[0].item.name}\n"
        f"Top Recommended Supplier: {top_rec.vendor_name}\n"
        f"Composite Score: {top_rec.overall_score}/100\n"
        f"Quality Rating: {top_rec.factor_breakdown.quality}%\n"
        f"On-Time Delivery Reliability: {top_rec.factor_breakdown.delivery_reliability}%\n"
        f"Price Competitiveness: {top_rec.factor_breakdown.price_competitiveness}%\n"
        f"Active Badges: {', '.join(top_rec.badges) if top_rec.badges else 'None'}\n\n"
        "Explain why this supplier is recommended and what commercial and operational advantages they offer."
    )

    try:
        rationale_text = llm.generate_text(
            prompt=prompt,
            system_prompt="You are an enterprise supplier evaluation specialist. Provide concise, compelling, structured justification."
        )
    except Exception:
        rationale_text = (
            f"{top_rec.vendor_name} achieved the highest composite rating of {top_rec.overall_score}/100 based on "
            f"Quality ({top_rec.factor_breakdown.quality}%), On-Time Delivery Reliability ({top_rec.factor_breakdown.delivery_reliability}%), "
            f"and Price Competitiveness ({top_rec.factor_breakdown.price_competitiveness}%). "
            f"Active Badges: {', '.join(top_rec.badges) if top_rec.badges else 'Standard Partner'}."
        )

    return {
        "recommended_vendor": top_rec.vendor_name,
        "score": top_rec.overall_score,
        "badges": top_rec.badges,
        "rationale": rationale_text
    }

@router.post("/explain/quotation-analysis/{pr_id}")
def explain_quotation_analysis(
    pr_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    analysis = evaluate_quotations(db, pr_id)
    if not analysis.evaluations:
        return {"explanation": "No quotations have been received for evaluation yet."}

    top_eval = analysis.evaluations[0]
    llm = get_llm_provider()

    eval_summaries = []
    for ev in analysis.evaluations:
        eval_summaries.append(
            f"- {ev.vendor_name}: Total Price=${ev.total_price:,.2f}, Lead Time={ev.lead_time_days} days, "
            f"Price Score={ev.price_score}, Delivery Score={ev.delivery_score}, Reliability Score={ev.reliability_score}, "
            f"Final Weighted Score={ev.final_weighted_score}/100 {'[RECOMMENDED]' if ev.is_recommended else ''}"
        )

    prompt = (
        f"Quotations Evaluated for PR:\n"
        f"{chr(10).join(eval_summaries)}\n\n"
        f"Recommended Supplier: {top_eval.vendor_name}\n"
        f"Explain the multi-criteria trade-offs between pricing, lead time, and reliability that lead to this recommendation."
    )

    try:
        rationale_text = llm.generate_text(
            prompt=prompt,
            system_prompt="You are a senior procurement evaluation officer. Explain competitive bidding trade-offs concisely and objectively."
        )
    except Exception:
        rationale_text = (
            f"{top_eval.vendor_name} ranked #1 with a final weighted quotation score of {top_eval.final_weighted_score}/100. "
            f"It was evaluated on Price Competitiveness (40% weight: {top_eval.price_score} pts), "
            f"Fulfillment Speed (20% weight: {top_eval.delivery_score} pts for {top_eval.lead_time_days} days lead time), "
            f"Reliability (20% weight: {top_eval.reliability_score} pts), and Quality (20% weight: {top_eval.quality_score} pts)."
        )

    return {
        "recommended_vendor": top_eval.vendor_name,
        "final_weighted_score": top_eval.final_weighted_score,
        "lead_time_days": top_eval.lead_time_days,
        "quoted_price": top_eval.total_price,
        "rationale": rationale_text
    }
