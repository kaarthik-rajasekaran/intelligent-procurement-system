from abc import ABC, abstractmethod
from typing import Optional, List
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        pass

    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def health_check(self) -> bool:
        pass


# ---------------------------------------------------------------------------
# MOCK LOCAL PROVIDER  (zero dependencies — always available)
# ---------------------------------------------------------------------------
class MockLocalLLMProvider(BaseLLMProvider):
    """
    Intelligent deterministic local LLM provider.
    Generates rich, dynamic, grounded responses based on prompt structure and domain evidence.
    """

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        prompt_lower = prompt.lower()

        # 1. RAG Vendor Recommendation Prompt (requires structured JSON output)
        if "candidate vendors" in prompt_lower or "recommendation_status" in prompt_lower or "task: analyze the evidence" in prompt_lower:
            try:
                import re
                import json

                # Extract item name and category
                item_match = re.search(r'PROCUREMENT ITEM:\s*(.+)', prompt, re.IGNORECASE)
                cat_match = re.search(r'CATEGORY:\s*(.+)', prompt, re.IGNORECASE)
                qty_match = re.search(r'REQUESTED QUANTITY:\s*([\d\.]+)', prompt, re.IGNORECASE)

                item_name = item_match.group(1).strip() if item_match else "Procurement Item"
                category = cat_match.group(1).strip() if cat_match else "General"
                quantity = float(qty_match.group(1)) if qty_match else 1.0

                # Extract vendor blocks: --- VENDOR: <name> (ID: <id>) ---
                vendor_blocks = re.findall(
                    r'---\s*VENDOR:\s*(.+?)\s*\(ID:\s*([a-f0-9-]+)\)\s*---\n(.*?)(?=\n---\s*VENDOR:|\nTASK:|\Z)',
                    prompt,
                    re.DOTALL | re.IGNORECASE
                )

                recommendations = []
                for idx, (v_name, v_id, v_content) in enumerate(vendor_blocks, start=1):
                    v_name = v_name.strip()
                    v_id = v_id.strip()

                    # Extract metrics
                    score_match = re.search(r'Analytical Score:\s*([\d\.]+)', v_content)
                    analytical_score = float(score_match.group(1)) if score_match else 80.0

                    q_match = re.search(r'Avg Quality Rating:\s*([\d\.]+)', v_content)
                    d_match = re.search(r'Avg Delivery Rating:\s*([\d\.]+)', v_content)
                    p_match = re.search(r'Avg Price Rating:\s*([\d\.]+)', v_content)
                    ot_match = re.search(r'On-Time Delivery Rate:\s*([\d\.]+)', v_content)
                    trend_match = re.search(r'Trend:\s*(\w+)', v_content)
                    has_bulk_issue = "BULK ORDER ISSUES DETECTED" in v_content

                    quality_score = float(q_match.group(1)) * 10 if q_match else 85.0
                    delivery_score = float(d_match.group(1)) * 10 if d_match else 88.0
                    on_time_rate = float(ot_match.group(1)) if ot_match else 90.0
                    trend = trend_match.group(1).upper() if trend_match else "STABLE"

                    # Determine status and status rationale
                    if idx == 1 and not has_bulk_issue and analytical_score >= 80:
                        status_val = "RECOMMENDED"
                    elif has_bulk_issue and quantity >= 15:
                        status_val = "CAUTION"
                    else:
                        status_val = "ACCEPTABLE"

                    # Generate dynamic contextual reasoning
                    strengths = []
                    risks = []

                    if quality_score >= 85:
                        strengths.append(f"High product quality and low return rate ({quality_score:.1f}% rating for {item_name})")
                    if on_time_rate >= 90:
                        strengths.append(f"Strong on-time delivery reliability ({on_time_rate:.1f}% fulfillment rate)")
                    if trend == "IMPROVING":
                        strengths.append("Quarterly review trajectory indicates consistent operational improvement")
                    if not strengths:
                        strengths.append(f"Established commercial vendor for {category} catalog items")

                    if has_bulk_issue and quantity >= 15:
                        risks.append(f"Past reviews indicate fulfillment bottlenecks on bulk orders ({quantity:g}+ units)")
                    elif quality_score < 80:
                        risks.append("Occasional QA variance noted in historical quarterly evaluations")
                    elif delivery_score < 80:
                        risks.append("Lead time buffer recommended due to occasional logistics delays")
                    else:
                        risks.append("Standard procurement lead time monitoring advised")

                    if status_val == "RECOMMENDED":
                        summary = (
                            f"{v_name} is the optimal recommendation for {item_name} with an analytical composite score of {analytical_score:.1f}/100. "
                            f"Demonstrates consistent {quality_score:.1f}% quality compliance and {on_time_rate:.1f}% on-time fulfillment."
                        )
                    elif status_val == "CAUTION":
                        summary = (
                            f"{v_name} holds acceptable baseline scores ({analytical_score:.1f}/100), but cautions are advised for a requested volume of {quantity:g} units "
                            f"due to past recorded bulk fulfillment delays."
                        )
                    else:
                        summary = (
                            f"{v_name} provides a solid alternative option with a {analytical_score:.1f}/100 performance profile and balanced {category} capabilities."
                        )

                    recommendations.append({
                        "vendor_id": v_id,
                        "vendor_name": v_name,
                        "rank": idx,
                        "recommendation_status": status_val,
                        "reasoning_summary": summary,
                        "key_strengths": strengths[:3],
                        "potential_risks": risks[:2]
                    })

                # Return valid JSON
                return json.dumps({"recommendations": recommendations[:3]}, indent=2)

            except Exception as e:
                logger.warning(f"[MockLocalLLM] Error generating structured RAG JSON: {e}")

        # 2. Purchase Request Executive Summary Prompt
        elif "purchase request reference:" in prompt_lower or "generate a 2-3 sentence professional executive summary" in prompt_lower:
            import re
            pr_ref = re.search(r'Purchase Request Reference:\s*(PR-[\w-]+)', prompt)
            req_name = re.search(r'Requester:\s*(.+?)\s*\(', prompt)
            item_info = re.search(r'Item Requested:\s*([\d\.]+x\s*.+)', prompt)
            supplier = re.search(r'Assigned Supplier:\s*(.+)', prompt)
            shortage_match = re.search(r'Shortage\s*=\s*([\d\.]+)', prompt)

            ref_str = pr_ref.group(1) if pr_ref else "PR-2026-XXXX"
            req_str = req_name.group(1) if req_name else "Employee"
            item_str = item_info.group(1) if item_info else "Item"
            supp_str = supplier.group(1) if supplier else "Assigned Vendor"
            shortage_val = float(shortage_match.group(1)) if shortage_match else 0.0

            stock_clause = (
                f"A warehouse shortage of {shortage_val:g} units requires external fulfillment from {supp_str}."
                if shortage_val > 0
                else f"Warehouse stock is currently being evaluated for allocation."
            )

            return (
                f"Purchase Request **{ref_str}** has been initiated by {req_str} for **{item_str}**. "
                f"{stock_clause} "
                f"Assigned supplier **{supp_str}** was selected to ensure corporate SLA compliance."
            )

        # 3. Vendor Recommendation Rationale Prompt
        elif "top recommended supplier:" in prompt_lower or "explain why this supplier is recommended" in prompt_lower:
            import re
            item_m = re.search(r'Item:\s*(.+)', prompt)
            supp_m = re.search(r'Top Recommended Supplier:\s*(.+)', prompt)
            score_m = re.search(r'Composite Score:\s*([\d\.]+)', prompt)

            item_val = item_m.group(1).strip() if item_m else "the requested item"
            supp_val = supp_m.group(1).strip() if supp_m else "The supplier"
            score_val = score_m.group(1).strip() if score_m else "85.0"

            return (
                f"**{supp_val}** is strongly recommended for **{item_val}** with a composite performance score of **{score_val}/100**. "
                f"Historical vendor evaluations verify superior on-time fulfillment reliability and strong quality compliance across preceding quarters. "
                f"Selecting this vendor minimizes operational delivery risks."
            )

        # 4. Quotation Evaluation Comparison Prompt
        elif "quotations evaluated for pr:" in prompt_lower or "explain the multi-criteria trade-offs" in prompt_lower:
            return (
                "The competitive bidding evaluation balances Price Competitiveness (40%), Delivery Speed (20%), "
                "Vendor Reliability (20%), and Product Quality (20%). The top-ranked quotation delivers the optimal "
                "balance of unit cost economy and committed fulfillment lead time."
            )

        # 5. Knowledge RAG / Procurement Policy Query Prompt
        elif "context from internal procurement policies:" in prompt_lower or "grounded answer based strictly on the policies" in prompt_lower:
            import re
            # Extract grounded text
            context_match = re.search(r'Context from internal procurement policies:\s*(.*?)\s*User Query:', prompt, re.DOTALL)
            ctx_text = context_match.group(1).strip() if context_match else ""
            
            # Find relevant sentence matching query keywords
            if ctx_text:
                sentences = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', ctx_text) if len(s.strip()) > 15]
                matched_sentences = [s for s in sentences if any(w in s.lower() for w in ["threshold", "5,000", "$5,000", "rfq", "approval", "policy", "vendor"])]
                if matched_sentences:
                    return f"According to corporate procurement policy: {' '.join(matched_sentences[:3])}"
                return f"According to corporate procurement policy:\n\n{sentences[0]}"
            return "According to corporate procurement policy, purchases exceeding $5,000 require multi-vendor RFQ competitive bidding and supervisor approval."

        # 6. Enterprise Copilot Chat Prompt (Context-Grounded Database QA)
        elif "enterprise procurement database records:" in prompt_lower and "user question:" in prompt_lower:
            import re
            ctx_match = re.search(r'ENTERPRISE PROCUREMENT DATABASE RECORDS:\s*(.*?)\s*USER QUESTION:\s*(.*)', prompt, re.DOTALL)
            ctx_str = ctx_match.group(1).strip() if ctx_match else ""
            question_str = ctx_match.group(2).strip() if ctx_match else ""
            q_lower = question_str.lower()

            # 1. Parse matched PR fields
            pr_data = {}
            if "[PURCHASE REQUEST RECORD MATCHED]" in ctx_str:
                pr_section = re.search(r'\[PURCHASE REQUEST RECORD MATCHED\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if pr_section:
                    for line in pr_section.group(1).split('\n'):
                        if '• Reference Number:' in line:
                            pr_data['ref'] = line.split(':', 1)[1].strip()
                        elif '• Requester:' in line:
                            pr_data['requester'] = line.split(':', 1)[1].strip()
                        elif '• Status:' in line:
                            pr_data['status'] = line.split(':', 1)[1].strip()
                        elif '• Selected / Awarded Supplier:' in line:
                            pr_data['supplier'] = line.split(':', 1)[1].strip()
                        elif '• Item:' in line:
                            pr_data['item'] = line.split(':', 1)[1].strip()
                        elif '• Quantity:' in line:
                            pr_data['qty'] = line.split(':', 1)[1].strip()
                        elif '• Related PO:' in line:
                            pr_data['po'] = line.split(':', 1)[1].strip()
                        elif '• Notes:' in line:
                            pr_data['notes'] = line.split(':', 1)[1].strip()

            # 2. Parse matched PO fields
            po_data = {}
            if "[SPECIFIC PURCHASE ORDER RECORD MATCHED]" in ctx_str:
                po_section = re.search(r'\[SPECIFIC PURCHASE ORDER RECORD MATCHED\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if po_section:
                    for line in po_section.group(1).split('\n'):
                        if '• PO Number:' in line:
                            po_data['po_num'] = line.split(':', 1)[1].strip()
                        elif '• PR Reference:' in line:
                            po_data['pr_ref'] = line.split(':', 1)[1].strip()
                        elif '• Awarded Supplier / Vendor:' in line:
                            po_data['supplier'] = line.split(':', 1)[1].strip()
                        elif '• Item Description:' in line:
                            po_data['item'] = line.split(':', 1)[1].strip()
                        elif '• Quantity:' in line:
                            po_data['qty'] = line.split(':', 1)[1].strip()
                        elif '• Total Approved Amount:' in line:
                            po_data['amount'] = line.split(':', 1)[1].strip()
                        elif '• Order Status:' in line:
                            po_data['status'] = line.split(':', 1)[1].strip()
                        elif '• Issue Date:' in line:
                            po_data['issue_date'] = line.split(':', 1)[1].strip()

            # 3. Handle Specific Question Intents for Matched PR / PO
            # A. Quantity Intent
            if any(w in q_lower for w in ['quantity', 'quantities', 'how many', 'count', 'units', 'volume']):
                if pr_data.get('qty'):
                    return f"The requested quantity for **{pr_data.get('ref', 'this request')}** is **{pr_data.get('qty')}** of **{pr_data.get('item', 'the requested item')}**."
                if po_data.get('qty'):
                    return f"The quantity on Purchase Order **{po_data.get('po_num', 'this order')}** is **{po_data.get('qty')}** of **{po_data.get('item', 'the item')}**."

            # B. Supplier / Vendor Intent
            if any(w in q_lower for w in ['supplier', 'vendor', 'who is', 'who supplied', 'awarded', 'seller', 'provider']) and not any(w in q_lower for w in ['all suppliers', 'list suppliers', 'which suppliers']):
                if pr_data.get('supplier') and pr_data['supplier'] != 'None':
                    return f"The selected supplier for **{pr_data.get('ref', 'this request')}** is **{pr_data.get('supplier')}**."
                if po_data.get('supplier'):
                    return f"The awarded supplier for Purchase Order **{po_data.get('po_num', 'this order')}** is **{po_data.get('supplier')}**."

            # C. Status / Approval / Stage Intent
            if any(w in q_lower for w in ['status', 'stage', 'approved', 'approval', 'where is', 'current state']):
                if pr_data.get('status'):
                    po_clause = f" (Associated Purchase Order: **{pr_data.get('po')}**)" if pr_data.get('po') and 'None' not in pr_data.get('po') else ""
                    return f"Purchase Request **{pr_data.get('ref', 'this request')}** is currently at status: **{pr_data.get('status')}**.{po_clause}"
                if po_data.get('status'):
                    return f"Purchase Order **{po_data.get('po_num', 'this order')}** is currently in **{po_data.get('status')}** status (Approved Amount: **{po_data.get('amount', 'N/A')}**)."

            # D. Item / Product Intent
            if any(w in q_lower for w in ['what item', 'which item', 'product', 'equipment', 'what did']):
                if pr_data.get('item'):
                    return f"The item for **{pr_data.get('ref', 'this request')}** is **{pr_data.get('item')}** (Quantity: **{pr_data.get('qty', 'N/A')}**)."
                if po_data.get('item'):
                    return f"The item ordered on **{po_data.get('po_num', 'this order')}** is **{po_data.get('item')}** (Quantity: **{po_data.get('qty', 'N/A')}**)."

            # E. Price / Amount / Cost Intent
            if any(w in q_lower for w in ['price', 'cost', 'amount', 'total', 'budget', 'how much', 'dollars']):
                if po_data.get('amount'):
                    return f"The total approved amount for Purchase Order **{po_data.get('po_num', 'this order')}** is **{po_data.get('amount')}**."
                if pr_data.get('po') and 'PO-' in pr_data.get('po'):
                    return f"Purchase Request **{pr_data.get('ref')}** has been issued Purchase Order **{pr_data.get('po')}** with supplier **{pr_data.get('supplier')}**."

            # F. Requester / Department Intent
            if any(w in q_lower for w in ['requester', 'who requested', 'who submitted', 'department', 'employee']):
                if pr_data.get('requester'):
                    return f"**{pr_data.get('ref', 'This request')}** was submitted by **{pr_data.get('requester')}**."

            # G. Purchase Order / PO Number Intent
            if any(w in q_lower for w in ['po number', 'purchase order', 'po reference', 'po ref']):
                if pr_data.get('po') and 'None' not in pr_data.get('po'):
                    return f"The related Purchase Order for **{pr_data.get('ref')}** is **{pr_data.get('po')}** (Status: **{pr_data.get('status')}**)."
                elif pr_data.get('ref'):
                    return f"Purchase Request **{pr_data.get('ref')}** does not have a Purchase Order generated yet (Current stage: **{pr_data.get('status')}**)."

            # H. Notes / Reason Intent
            if any(w in q_lower for w in ['note', 'notes', 'reason', 'justification', 'comment']):
                if pr_data.get('notes'):
                    return f"Requester notes for **{pr_data.get('ref', 'this request')}**: **{pr_data.get('notes')}**."

            # I. General PR Overview (e.g. "Tell me about PR-...", "PR details")
            if pr_data and any(w in q_lower for w in ['tell me', 'about', 'summary', 'overview', 'details', 'pr-']):
                return (
                    f"**Purchase Request {pr_data.get('ref', '')} Overview:**\n\n"
                    f"• **Item:** {pr_data.get('qty', '')} of {pr_data.get('item', '')}\n"
                    f"• **Requester:** {pr_data.get('requester', '')}\n"
                    f"• **Current Status:** {pr_data.get('status', '')}\n"
                    f"• **Awarded Supplier:** {pr_data.get('supplier', 'None assigned yet')}\n"
                    f"• **Related PO:** {pr_data.get('po', 'None generated yet')}\n"
                    f"• **Notes:** {pr_data.get('notes', 'None')}"
                )

            # J. General PO Overview
            if po_data and any(w in q_lower for w in ['tell me', 'about', 'summary', 'overview', 'po-']):
                return (
                    f"**Purchase Order {po_data.get('po_num', '')} Overview:**\n\n"
                    f"• **Item:** {po_data.get('qty', '')} of {po_data.get('item', '')}\n"
                    f"• **Supplier:** {po_data.get('supplier', '')}\n"
                    f"• **Approved Amount:** {po_data.get('amount', '')}\n"
                    f"• **Order Status:** {po_data.get('status', '')}\n"
                    f"• **PR Reference:** {po_data.get('pr_ref', 'N/A')}\n"
                    f"• **Issue Date:** {po_data.get('issue_date', 'N/A')}"
                )

            # 4. Multi-Factor Quotation Scoring Query
            if "[MULTI-FACTOR QUOTATION EVALUATION FORMULA]" in ctx_str and any(w in q_lower for w in ['quotation', 'evaluation', 'score', 'scoring', 'multi-factor', 'weight', 'criteria']):
                mf_section = re.search(r'\[MULTI-FACTOR QUOTATION EVALUATION FORMULA\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if mf_section:
                    return f"**Multi-Factor Quotation Scoring Criteria:**\n\n{mf_section.group(1).strip()}"

            # 5. Policy & Threshold Guidelines Query
            if "[CORPORATE PROCUREMENT POLICY EXCERPTS]" in ctx_str and any(w in q_lower for w in ['policy', 'threshold', 'rule', 'guideline', 'limit', 'compliance', 'approval']):
                pol_section = re.search(r'\[CORPORATE PROCUREMENT POLICY EXCERPTS\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if pol_section:
                    return f"**Procurement Policy Guidelines:**\n\n{pol_section.group(1).strip()[:500]}"

            # 6. Registered Enterprise Suppliers Query
            if "[REGISTERED ENTERPRISE SUPPLIERS]" in ctx_str and any(w in q_lower for w in ['vendor', 'supplier', 'who', 'hardware', 'laptop', 'network', 'telecom', 'furniture', 'office', 'toner', 'safeguard']):
                v_section = re.search(r'\[REGISTERED ENTERPRISE SUPPLIERS\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if v_section:
                    return f"**Registered Enterprise Suppliers:**\n\n{v_section.group(1).strip()}"

            # 7. Active Purchase Requests on Record Query
            if "[ACTIVE PURCHASE REQUESTS ON RECORD]" in ctx_str and any(w in q_lower for w in ['request', 'requests', 'active', 'queue']):
                pr_section = re.search(r'\[ACTIVE PURCHASE REQUESTS ON RECORD\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if pr_section:
                    return f"**Active Purchase Requests on Record:**\n\n{pr_section.group(1).strip()}"

            # 8. Recent Purchase Orders Query
            if "[ACTIVE ENTERPRISE PURCHASE ORDERS ON RECORD]" in ctx_str and any(w in q_lower for w in ['order', 'orders', 'recent', 'history']):
                po_section = re.search(r'\[ACTIVE ENTERPRISE PURCHASE ORDERS ON RECORD\]\s*(.*?)(?=\n\n\[|\Z)', ctx_str, re.DOTALL)
                if po_section:
                    return f"**Recent Purchase Orders on Record:**\n\n{po_section.group(1).strip()}"

            # Default conversational fallback when context is available
            if pr_data:
                return (
                    f"I have loaded details for Purchase Request **{pr_data.get('ref', '')}** "
                    f"({pr_data.get('qty', '')} of {pr_data.get('item', '')}, Status: {pr_data.get('status', '')}). "
                    f"You can ask me specific questions like: *'how many quantities?'*, *'who is the supplier?'*, or *'what is the status?'*."
                )

            return (
                "**Procurement Copilot:**\n"
                "I am your Enterprise Procurement Copilot. I have real-time access to purchase requests, purchase orders, registered suppliers, inventory reserves, and company procurement guidelines. How can I assist you?"
            )

        # 7. Default General Response
        else:
            return (
                "**Procurement Copilot:**\n"
                f"I have reviewed the procurement inquiry. "
                "All transaction workflows comply with automated inventory allocation, supplier tier ranking, "
                "and supervisor approval controls."
            )

    def generate_embedding(self, text: str) -> List[float]:
        import hashlib
        import numpy as np
        seed = int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(64)
        norm = float(sum(x ** 2 for x in vec) ** 0.5)
        if norm > 0:
            vec = [x / norm for x in vec]
        return list(vec)

    def health_check(self) -> bool:
        return True



# ---------------------------------------------------------------------------
# GOOGLE GEMINI PROVIDER (new google-genai SDK)
# ---------------------------------------------------------------------------
class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini via the new google-genai SDK.
    """

    def __init__(self, api_key: str, model: str = "gemini-flash-lite-latest"):
        try:
            from google import genai
            from google.genai import types as genai_types
            self._client = genai.Client(api_key=api_key)
            self._genai_types = genai_types
            self._model_name = model or "gemini-flash-lite-latest"
            self._fallback_models = [
                "gemini-flash-lite-latest",
                "gemini-3.5-flash",
                "gemini-flash-latest",
                "gemini-3.5-flash-lite"
            ]
            logger.info(f"[LLM] Gemini provider initialized with primary model: {self._model_name}")
        except ImportError:
            raise RuntimeError(
                "google-genai package not installed. "
                "Run: pip install google-genai"
            )

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        candidate_models = [self._model_name] + [m for m in self._fallback_models if m != self._model_name]
        last_error = None

        for model_candidate in candidate_models:
            try:
                config = None
                if system_prompt:
                    config = self._genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3
                    )
                else:
                    config = self._genai_types.GenerateContentConfig(
                        temperature=0.3
                    )

                response = self._client.models.generate_content(
                    model=model_candidate,
                    contents=prompt,
                    config=config
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as e:
                last_error = e
                logger.warning(f"[Gemini] model '{model_candidate}' failed: {e}. Trying fallback...")
                continue

        logger.error(f"[Gemini] All Gemini candidate models failed ({last_error}). Falling back to analytical mock response.")
        return MockLocalLLMProvider().generate_text(prompt, system_prompt)

    def generate_embedding(self, text: str) -> List[float]:
        for em in ["gemini-embedding-001", "gemini-embedding-2"]:
            try:
                result = self._client.models.embed_content(
                    model=em,
                    contents=text
                )
                if result and result.embeddings:
                    return list(result.embeddings[0].values)
            except Exception as e:
                logger.warning(f"[Gemini] Embedding model '{em}' failed: {e}")
                continue

        logger.warning("[Gemini] All embedding models failed, using deterministic local embedding fallback.")
        return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents="OK",
                config=self._genai_types.GenerateContentConfig(temperature=0.1)
            )
            return bool(response.text)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# OPENAI PROVIDER
# ---------------------------------------------------------------------------
class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI ChatCompletion via openai SDK.
    Requires: pip install openai
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=api_key)
            self._model = model
            logger.info(f"[LLM] OpenAI provider initialized with model: {model}")
        except ImportError:
            raise RuntimeError("openai package not installed. Run: pip install openai")

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=1024,
                temperature=0.3
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"[OpenAI] generate_text error: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        try:
            resp = self._client.embeddings.create(
                model="text-embedding-3-small",
                input=text[:8000]
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"[OpenAI] Embedding failed, using fallback: {e}")
            return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5
            )
            return bool(resp.choices)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# ANTHROPIC PROVIDER
# ---------------------------------------------------------------------------
class AnthropicLLMProvider(BaseLLMProvider):
    """
    Anthropic Claude via anthropic SDK.
    Requires: pip install anthropic
    """

    def __init__(self, api_key: str, model: str = "claude-3-haiku-20240307"):
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
            self._model = model
            logger.info(f"[LLM] Anthropic provider initialized with model: {model}")
        except ImportError:
            raise RuntimeError("anthropic package not installed. Run: pip install anthropic")

    def generate_text(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=1024,
                system=system_prompt or "You are an intelligent procurement assistant.",
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text
        except Exception as e:
            logger.error(f"[Anthropic] generate_text error: {e}")
            raise

    def generate_embedding(self, text: str) -> List[float]:
        # Anthropic does not expose an embedding API; fall back to mock
        return MockLocalLLMProvider().generate_embedding(text)

    def health_check(self) -> bool:
        try:
            resp = self._client.messages.create(
                model=self._model,
                max_tokens=5,
                messages=[{"role": "user", "content": "ping"}]
            )
            return bool(resp.content)
        except Exception:
            return False


# ---------------------------------------------------------------------------
# FACTORY
# ---------------------------------------------------------------------------
def get_llm_provider() -> BaseLLMProvider:
    """
    Returns the configured LLM provider based on LLM_PROVIDER setting.
    Falls back to MockLocalLLMProvider if no valid provider is configured
    or if the required package is not installed.
    """
    provider_name = settings.LLM_PROVIDER.lower().strip()

    if provider_name == "gemini" and settings.GEMINI_API_KEY:
        try:
            return GeminiLLMProvider(
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] Gemini init failed: {e}. Falling back to mock.")

    elif provider_name == "openai" and settings.OPENAI_API_KEY:
        try:
            return OpenAILLMProvider(
                api_key=settings.OPENAI_API_KEY,
                model=settings.OPENAI_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] OpenAI init failed: {e}. Falling back to mock.")

    elif provider_name == "anthropic" and settings.ANTHROPIC_API_KEY:
        try:
            return AnthropicLLMProvider(
                api_key=settings.ANTHROPIC_API_KEY,
                model=settings.ANTHROPIC_MODEL
            )
        except Exception as e:
            logger.warning(f"[LLM] Anthropic init failed: {e}. Falling back to mock.")

    elif provider_name != "mock_local":
        logger.warning(
            f"[LLM] Unknown provider '{provider_name}' or missing API key. "
            "Falling back to MockLocalLLMProvider."
        )

    logger.info("[LLM] Using MockLocalLLMProvider (no real API key configured).")
    return MockLocalLLMProvider()
