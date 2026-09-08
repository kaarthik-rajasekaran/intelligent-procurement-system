# Enhanced Keynote & Architectural Presentation Generator for Micron Hackathon
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# -----------------------------------------------------------------------------
# PALETTE & TYPOGRAPHY (Matching uploaded deck + Micron theme)
# -----------------------------------------------------------------------------
NAVY_DEEP = RGBColor(10, 17, 30)       # #0A111E (Deep Dark Slate Navy)
NAVY_CARD = RGBColor(18, 28, 48)       # #121C30 (Dark Card Background)
NAVY_CARD_BORDER = RGBColor(30, 50, 80)# #1E3250 (Subtle Dark Border)
MICRON_BLUE = RGBColor(0, 114, 206)    # #0072CE (Micron Brand Blue)
CYAN_ACCENT = RGBColor(0, 163, 224)    # #00A3E0 (Tech Cyan Accent)
WHITE = RGBColor(255, 255, 255)        # #FFFFFF
SLATE_LIGHT = RGBColor(226, 232, 240)  # #E2E8F0 (Text Secondary)
SLATE_MUTED = RGBColor(148, 163, 184)  # #94A3B8 (Text Muted)
EMERALD = RGBColor(16, 185, 129)       # #10B981 (Success / Green)
AMBER = RGBColor(245, 158, 11)         # #F59E0B (Warning / Amber)
ROSE = RGBColor(239, 68, 68)           # #EF4444 (Risk / Rose)
PURPLE_ACCENT = RGBColor(139, 92, 246) # #8B5CF6 (Agentic Flow Purple)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def build_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_bg(slide, color=NAVY_DEEP):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_category_header(slide, category_text, title_text):
        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.733), Inches(1.3))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_cat = tf.paragraphs[0]
        p_cat.text = category_text.upper()
        p_cat.font.size = Pt(11)
        p_cat.font.bold = True
        p_cat.font.name = FONT_HEADING
        p_cat.font.color.rgb = CYAN_ACCENT
        p_cat.space_after = Pt(4)

        p_title = tf.add_paragraph()
        p_title.text = title_text
        p_title.font.size = Pt(28)
        p_title.font.bold = True
        p_title.font.name = FONT_HEADING
        p_title.font.color.rgb = WHITE

    def make_card(slide, left, top, width, height, bg=NAVY_CARD, border=NAVY_CARD_BORDER):
        s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        s.fill.solid()
        s.fill.fore_color.rgb = bg
        s.line.color.rgb = border
        s.line.width = Pt(1.2)
        return s

    def set_notes(slide, key_msg, narration, duration, transition):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = (
            f"🎯 KEY MESSAGE:\n{key_msg}\n\n"
            f"🎙️ SUGGESTED NARRATION (~{duration}):\n{narration}\n\n"
            f"🔄 TRANSITION TO NEXT SLIDE:\n{transition}"
        )

    # =========================================================================
    # SLIDE 1: Title / Opening
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(2.0), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = CYAN_ACCENT
    bar.line.fill.background()

    tb = s1.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(2.5))
    p = tb.text_frame.paragraphs[0]
    p.text = "From Purchase Request to Intelligent Decision"
    p.font.size = Pt(42)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_HEADING

    p2 = tb.text_frame.add_paragraph()
    p2.text = "Intelligent Procurement Management System (IPMS) — Micron Technology Hackathon"
    p2.font.size = Pt(18)
    p2.font.color.rgb = CYAN_ACCENT
    p2.space_before = Pt(12)

    flow_steps = ["REQUEST", "INTELLIGENCE", "COMPETITION", "DECISION", "EXECUTION"]
    step_w = Inches(2.1)
    step_gap = Inches(0.3)
    start_x = Inches(0.8)
    y_pos = Inches(4.7)

    for i, step in enumerate(flow_steps):
        card = make_card(s1, start_x + i * (step_w + step_gap), y_pos, step_w, Inches(1.4),
                         bg=RGBColor(0, 36, 71) if i == 0 else NAVY_CARD,
                         border=CYAN_ACCENT if i == 0 else NAVY_CARD_BORDER)
        tf = card.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = step
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = WHITE if i == 0 else SLATE_MUTED

    set_notes(s1,
        "Procurement starts with a humble request, but real optimization happens in the decisions that follow.",
        "Good morning, members of the Micron evaluation panel. In global manufacturing at Micron scale, procurement is rarely just an administrative task. Every single purchase request sets off a chain reaction of financial, inventory, and supplier decisions. Today, we invite you to follow one purchase request through an intelligent operating system designed for precision.",
        "1.0 min",
        "Let us look at the fundamental problem facing modern enterprise procurement.")

    # =========================================================================
    # SLIDE 2: THE CHALLENGE — Procurement at Scale Breaks Down Under Volume
    # (Incorporating Uploaded Screenshot #1)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_category_header(s2, "THE CHALLENGE", "Procurement at scale breaks down under its own volume")

    # Left Narrative Card
    c_left = make_card(s2, Inches(0.8), Inches(2.0), Inches(7.2), Inches(4.5), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf_l = c_left.text_frame
    tf_l.margin_left = tf_l.margin_right = Inches(0.5)
    tf_l.margin_top = Inches(0.8)
    p = tf_l.paragraphs[0]
    p.text = "Large organizations generate thousands of purchase requisitions daily."
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub = tf_l.add_paragraph()
    p_sub.text = "\nThis volume drives real operational inefficiency — many requests duplicate existing assets or could be sourced more effectively through alternative suppliers."
    p_sub.font.size = Pt(17)
    p_sub.font.color.rgb = SLATE_LIGHT

    # Right Counter Box (2,847 PRs/Day)
    c_right = make_card(s2, Inches(8.3), Inches(2.0), Inches(4.2), Inches(4.5), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_r = c_right.text_frame
    tf_r.margin_top = Inches(0.5)

    p1 = tf_r.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    p1.text = "PRs SUBMITTED / DAY"
    p1.font.size = Pt(12)
    p1.font.bold = True
    p1.font.color.rgb = SLATE_MUTED

    p2 = tf_r.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = "2,847"
    p2.font.size = Pt(56)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(14)

    p3 = tf_r.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = "▲ growing daily volume"
    p3.font.size = Pt(13)
    p3.font.bold = True
    p3.font.color.rgb = ROSE
    p3.space_before = Pt(8)

    p4 = tf_r.add_paragraph()
    p4.alignment = PP_ALIGN.CENTER
    p4.text = "Live Counter — Verified in Enterprise Benchmark"
    p4.font.size = Pt(11)
    p4.font.italic = True
    p4.font.color.rgb = SLATE_MUTED
    p4.space_before = Pt(30)

    set_notes(s2,
        "High requisition volume creates invisible duplicate spend and supplier blind spots.",
        "When an enterprise processes thousands of PRs daily, human review chains break down. Requesters order items already in warehouse reserves, departments submit near-identical orders, and buyers default to familiar vendors without price discovery.",
        "1.0 min",
        "Let us examine the hidden questions behind every single request.")

    # =========================================================================
    # SLIDE 3: Until You Follow What Happens Next (5 Questions Surrounding PR)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_category_header(s3, "THE DECISION INCEPTION", "Until You Follow What Happens Next")

    center_box = make_card(s3, Inches(5.1), Inches(3.2), Inches(3.1), Inches(1.8), bg=MICRON_BLUE, border=CYAN_ACCENT)
    p = center_box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "PURCHASE\nREQUEST"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = WHITE

    questions = [
        ("DO WE NEED IT?", Inches(0.8), Inches(2.2)),
        ("ARE WE ALREADY BUYING IT?", Inches(0.8), Inches(4.5)),
        ("WHO SHOULD SUPPLY IT?", Inches(8.7), Inches(2.2)),
        ("WHAT DO WE KNOW ABOUT THEM?", Inches(8.7), Inches(4.5)),
        ("WHICH OFFER IS REALLY BEST?", Inches(4.7), Inches(5.5))
    ]
    for q_text, qx, qy in questions:
        q_card = make_card(s3, qx, qy, Inches(3.8), Inches(1.1), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
        p = q_card.text_frame.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = q_text
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = SLATE_LIGHT

    set_notes(s3,
        "A single PR hides 5 critical choices that directly govern cost, lead time, and supply risk.",
        "A purchase request looks simple. But behind it are five critical choices: Do we already own it? Has another team ordered it? Who is qualified? What is their true track record? And which quotation gives the best total value? Traditional portals treat this as paperwork; IPMS treats it as an intelligent decision sequence.",
        "1.0 min",
        "Here are the four strategic moves we built to solve this.")

    # =========================================================================
    # SLIDE 4: OUR APPROACH & SOLUTION — Four Moves That Close the Gap
    # (Incorporating Uploaded Screenshot #4)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_category_header(s4, "OUR APPROACH & SOLUTION", "Four moves that close the gap")

    moves = [
        ("01", "Automated De-duplication & Intelligent Routing", "Runs the instant a new PR is submitted — ±20% active quantity window match"),
        ("02", "Proactive Inventory Verification & Notification", "Instantly checks warehouse reserves to fulfill from stock with zero external spend"),
        ("03", "Alternative Sourcing Analysis & Vendor Comparison", "Evaluates candidate suppliers on price benchmark, lead time speed, history & quality"),
        ("04", "Grounded AI Recommendation Synthesis", "Ingests quarterly qualitative reviews via RAG to surface actionable vendor strengths & risks")
    ]

    for i, (num, m_title, m_desc) in enumerate(moves):
        c = make_card(s4, Inches(0.8), Inches(1.9 + i * 1.25), Inches(11.733), Inches(1.1), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
        tf = c.text_frame
        tf.margin_left = Inches(0.4)
        tf.margin_top = Inches(0.18)

        p = tf.paragraphs[0]
        p.text = f"{num}   {m_title}"
        p.font.size = Pt(16)
        p.font.bold = True
        p.font.color.rgb = CYAN_ACCENT if i % 2 == 0 else WHITE

        p_sub = tf.add_paragraph()
        p_sub.text = f"       {m_desc}"
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = SLATE_MUTED

    set_notes(s4,
        "Four integrated mechanisms: de-duplication, inventory check, multi-factor sourcing, and RAG synthesis.",
        "Our approach closes the procurement gap in four strategic steps: de-duplication at submission, proactive inventory stock check, multi-factor supplier analysis, and RAG-powered qualitative feedback synthesis. Every step adds measurable decision intelligence.",
        "1.0 min",
        "Let us walk through the first decision: Should we buy it at all?")

    # =========================================================================
    # SLIDE 5: Decision #1: Don't Buy What You Already Have.
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_category_header(s5, "DECISION #1: INVENTORY INTELLIGENCE", "First: Don't Buy What You Already Have")

    cards_data = [
        ("REQUESTED", "100 UNITS", WHITE, NAVY_CARD, NAVY_CARD_BORDER),
        ("IN STOCK", "70 UNITS", EMERALD, RGBColor(6, 44, 34), EMERALD),
        ("ACTUAL BUY", "30 UNITS", CYAN_ACCENT, RGBColor(0, 36, 71), CYAN_ACCENT)
    ]
    for i, (label, val, txt_c, bg_c, brd_c) in enumerate(cards_data):
        c = make_card(s5, Inches(0.8 + i * 4.0), Inches(2.2), Inches(3.7), Inches(2.6), bg=bg_c, border=brd_c)
        tf = c.text_frame
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        p1.text = label
        p1.font.size = Pt(14)
        p1.font.bold = True
        p1.font.color.rgb = SLATE_MUTED

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = val
        p2.font.size = Pt(36)
        p2.font.bold = True
        p2.font.color.rgb = txt_c
        p2.space_before = Pt(20)

    tb_b = s5.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.7), Inches(1.0))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = '\"The cheapest purchase is the purchase you never had to make.\"'
    p_b.font.size = Pt(22)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s5,
        "Deterministic inventory reconciliation isolates true shortage before initiating external procurement.",
        "When an engineer requests 100 units, IPMS deterministically checks warehouse reserves via Shortage = max(0, Requested - Available). With 70 in stock, the true external procurement need drops to 30. Zero AI hallucination, pure mathematical stock reconciliation.",
        "1.0 min",
        "Now that we know the requirement is 30, what if someone already ordered it?")

    # =========================================================================
    # SLIDE 6: Decision #2: What If Someone Already Asked For Those 30?
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_bg(s6)
    add_category_header(s6, "DECISION #2: DUPLICATE INTELLIGENCE", "What If Someone Already Asked For Those 30?")

    c1 = make_card(s6, Inches(0.8), Inches(2.2), Inches(3.6), Inches(2.8), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf1 = c1.text_frame
    p = tf1.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "NEW REQUEST\n\nThermal Paste\n30 Units"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c2 = make_card(s6, Inches(4.8), Inches(2.2), Inches(3.7), Inches(2.8), bg=RGBColor(50, 35, 10), border=AMBER)
    tf2 = c2.text_frame
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "⚠ POTENTIAL MATCH\n\nDepartment Match\n±20% Quantity Window\nDecision-Support Alert"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = AMBER

    c3 = make_card(s6, Inches(8.9), Inches(2.2), Inches(3.6), Inches(2.8), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf3 = c3.text_frame
    p = tf3.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "EXISTING ACTIVE PR\n\nPR-2026-0042\n28 Units (Active)"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    tb_b = s6.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "Make potential waste visible before money leaves the organization."
    p_b.font.size = Pt(18)
    p_b.font.bold = True
    p_b.font.color.rgb = CYAN_ACCENT

    set_notes(s6,
        "Duplicate windowing checks active department requests within a ±20% quantity variance.",
        "IPMS scans active non-terminal PRs in the same department for the same SKU. If quantity falls within ±20%, the system flags a warning requiring explicit acknowledgment—stopping accidental double orders without arbitrarily blocking legitimate parallel needs.",
        "1.0 min",
        "Let us see how our autonomous agentic flow handles this decision.")

    # =========================================================================
    # SLIDE 7: OUR AGENTIC FLOW — Checks, Calls Tools, Hands Off to Human
    # (Incorporating Uploaded Screenshot #3)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_category_header(s7, "OUR AGENTIC FLOW", "The agent decides what to check, calls its tools, then hands off to a human")

    # Top Input Node
    c_in = make_card(s7, Inches(3.8), Inches(1.8), Inches(5.7), Inches(0.7), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    p = c_in.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Employee Submits PR (Item + Quantity + Department + Preferred Vendor)"
    p.font.size = Pt(12)
    p.font.color.rgb = SLATE_LIGHT

    # Split Agent Node: Left Duplicate Detection, Right Vendor Sourcing
    c_dup = make_card(s7, Inches(0.8), Inches(2.7), Inches(5.6), Inches(1.3), bg=NAVY_CARD, border=AMBER)
    tf_d = c_dup.text_frame
    p = tf_d.paragraphs[0]
    p.text = "Tool 1: Duplicate & Stock Detection"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = AMBER
    p_sub = tf_d.add_paragraph()
    p_sub.text = "Checks inventory reserve & ±20% active department requests.\nOutcome: Flags potential duplicate or verifies genuine net shortage."
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = SLATE_MUTED

    c_ven = make_card(s7, Inches(6.9), Inches(2.7), Inches(5.6), Inches(1.3), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_v = c_ven.text_frame
    p = tf_v.paragraphs[0]
    p.text = "Tool 2: Alternative Sourcing & RAG"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT
    p_sub = tf_v.add_paragraph()
    p_sub.text = "Evaluates vendor price benchmarks, lead time velocity & reviews.\nOutcome: Ranks top 3 candidate suppliers with qualitative strengths."
    p_sub.font.size = Pt(10)
    p_sub.font.color.rgb = SLATE_MUTED

    # Join Node: Agent Summary
    c_sum = make_card(s7, Inches(2.5), Inches(4.2), Inches(8.3), Inches(0.8), bg=RGBColor(0, 36, 71), border=CYAN_ACCENT)
    p = c_sum.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Agent Writes Grounded Executive Briefing (Synthesizes facts into plain language)"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = WHITE

    # Supervisor Review Actions (Approve / Return for Revision / Reject)
    actions = [
        ("Approve for RFQ", "Advances to 3-Vendor RFQ", EMERALD),
        ("Return for Revision", "Returns to Employee Queue", AMBER),
        ("Reject Request", "Terminal audit state", ROSE)
    ]
    for i, (act_title, act_sub, col) in enumerate(actions):
        c = make_card(s7, Inches(0.8 + i * 4.0), Inches(5.2), Inches(3.7), Inches(1.2), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{act_title}\n{act_sub}"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = col

    # Bottom Callout
    tb_b = s7.shapes.add_textbox(Inches(0.8), Inches(6.6), Inches(11.7), Inches(0.5))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "The AI only finds facts and explains them — it never approves a purchase on its own."
    p_b.font.size = Pt(12)
    p_b.font.italic = True
    p_b.font.color.rgb = SLATE_MUTED

    set_notes(s7,
        "Agentic tool orchestration combines duplicate checks and RAG vendor sourcing before human supervisor sign-off.",
        "This is our agentic architecture: The agent checks stock and duplicates via deterministic tools, runs RAG retrieval for qualitative supplier feedback, and produces one clear executive summary. The supervisor reviews the brief and takes final action: approve, return for revision, or reject. AI advises—humans decide.",
        "1.0 min",
        "How do we evaluate suppliers? Let us look at structured metrics vs human experience.")

    # =========================================================================
    # SLIDE 8: Data Remembers Numbers. People Remember Experience.
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_category_header(s8, "VENDOR INTELLIGENCE", "Data Remembers Numbers. People Remember Experience.")

    c_left = make_card(s8, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.3), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf_l = c_left.text_frame
    tf_l.margin_left = tf_l.margin_top = Inches(0.5)
    p = tf_l.paragraphs[0]
    p.text = "DATA REMEMBERS\nTHE NUMBERS"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT

    metrics = ["QUALITY RATING: 94%", "ON-TIME DELIVERY: 88%", "HISTORICAL FULFILLMENT: 85%"]
    for m in metrics:
        pm = tf_l.add_paragraph()
        pm.text = m
        pm.font.size = Pt(16)
        pm.font.bold = True
        pm.font.color.rgb = WHITE
        pm.space_before = Pt(18)

    c_right = make_card(s8, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.3), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_r = c_right.text_frame
    tf_r.margin_left = tf_r.margin_top = Inches(0.5)
    p = tf_r.paragraphs[0]
    p.text = "PEOPLE REMEMBER\nTHE EXPERIENCE"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    pq = tf_r.add_paragraph()
    pq.text = "\n\"Delivery was recovered quickly.\nCommunication during delays wasn't.\""
    pq.font.size = Pt(18)
    pq.font.bold = True
    pq.font.color.rgb = SLATE_LIGHT

    p_sub = tf_r.add_paragraph()
    p_sub.text = "\n— Quarterly Vendor Survey Ingestion"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = SLATE_MUTED

    tb_b = s8.shapes.add_textbox(Inches(0.8), Inches(6.4), Inches(11.7), Inches(0.6))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "Structured data tells us what happened. Human experience helps us understand why."
    p_b.font.size = Pt(15)
    p_b.font.bold = True
    p_b.font.color.rgb = CYAN_ACCENT

    set_notes(s8,
        "Quarterly feedback collection provides qualitative context that raw metrics miss.",
        "Every quarter, engineers and procurement stakeholders submit qualitative reviews. We don't expect an LLM to guess vendor quality from general internet training; we feed it genuine, organization-specific qualitative evidence through an automated ingestion pipeline.",
        "1.0 min",
        "How does that feedback become actionable intelligence?")

    # =========================================================================
    # SLIDE 9: How Human Experience Becomes Intelligence (RAG Pipeline)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9)
    add_category_header(s9, "RAG ARCHITECTURE", "How Does Human Experience Become Intelligence?")

    rag_steps = [
        ("01", "QUARTERLY FEEDBACK", "Survey reviews & operational logs", SLATE_MUTED),
        ("02", "DENSE VECTOR SEARCH", "Semantic similarity matching", CYAN_ACCENT),
        ("03", "GROUNDED EVIDENCE", "KPI metrics + Retrieved text", MICRON_BLUE),
        ("04", "SYNTHESIZED INSIGHT", "Strengths, risks & confidence badges", EMERALD)
    ]
    for i, (num, title, sub, col) in enumerate(rag_steps):
        c = make_card(s9, Inches(0.8 + i * 3.0), Inches(2.2), Inches(2.8), Inches(3.2), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{num}\n\n{title}\n\n{sub}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = col

    tb_b = s9.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "AI does not search the organization blindly. It reasons over retrieved evidence."
    p_b.font.size = Pt(17)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s9,
        "Retrieval-Augmented Generation extracts relevant context to ground LLM reasoning.",
        "Our RAG pipeline performs dense vector search over stored feedback embeddings. It constructs a compact, relevant evidence packet that combines quantitative scores with historical reviews, prompting the LLM to output executive strengths, risks, and confidence ratings with zero speculation.",
        "1.0 min",
        "Where do we draw the line on using AI?")

    # =========================================================================
    # SLIDE 10: Where We Deliberately Chose NOT to Use AI
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10)
    add_category_header(s10, "ARCHITECTURAL RIGOR", "Where We Deliberately Chose NOT to Use AI")

    c_left = make_card(s10, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.0), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf_l = c_left.text_frame
    tf_l.margin_left = tf_l.margin_top = Inches(0.4)
    p = tf_l.paragraphs[0]
    p.text = "2 + 2 = 4\nDON'T CALL AI."
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub_l = tf_l.add_paragraph()
    p_sub_l.text = "\n• Inventory Shortage Calculation\n• ±20% Duplicate Window Matching\n• 5-Factor Quotation Scoring V2\n• Idempotent PO Record Creation"
    p_sub_l.font.size = Pt(14)
    p_sub_l.font.color.rgb = SLATE_MUTED

    c_right = make_card(s10, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.0), bg=NAVY_CARD, border=CYAN_ACCENT)
    tf_r = c_right.text_frame
    tf_r.margin_left = tf_r.margin_top = Inches(0.4)
    p = tf_r.paragraphs[0]
    p.text = "\"Which vendor is safer\nfor cleanroom urgency?\"\nNOW AI HELPS."
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT

    p_sub_r = tf_r.add_paragraph()
    p_sub_r.text = "\n• Qualitative Review Synthesis\n• Sentiment & Risk Extraction\n• Contextual Copilot Policy QA"
    p_sub_r.font.size = Pt(14)
    p_sub_r.font.color.rgb = WHITE

    tb_b = s10.shapes.add_textbox(Inches(0.8), Inches(6.0), Inches(11.7), Inches(0.9))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = '\"WE USE AI FOR AMBIGUITY. NOT ARITHMETIC.\"'
    p_b.font.size = Pt(24)
    p_b.font.bold = True
    p_b.font.color.rgb = EMERALD

    set_notes(s10,
        "Zero-hallucination guarantee: math and state transitions are deterministic; LLMs handle qualitative ambiguity.",
        "We never let an LLM do math, track budgets, or execute state transitions. Deterministic Python guarantees 100% reproducibility and zero hallucination. Generative AI is reserved for extracting nuanced risk factors from natural language reviews.",
        "1.0 min",
        "How do we prevent paying for the same AI intelligence repeatedly?")

    # =========================================================================
    # SLIDE 11: AI Cost Control — Recommendation Snapshots
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_bg(s11)
    add_category_header(s11, "COST CONTROL", "And We Don't Pay for the Same Intelligence Twice")

    c_left = make_card(s11, Inches(1.2), Inches(2.2), Inches(5.0), Inches(3.2), bg=RGBColor(6, 44, 34), border=EMERALD)
    tf_l = c_left.text_frame
    tf_l.margin_top = Inches(0.5)
    p = tf_l.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "SAME CONTEXT\n\nSnapshot Cache Hit\n0 Tokens Incurred\nSub-5ms Latency"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c_right = make_card(s11, Inches(7.1), Inches(2.2), Inches(5.0), Inches(3.2), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_r = c_right.text_frame
    tf_r.margin_top = Inches(0.5)
    p = tf_r.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "NEW CONTEXT\n\nExplicit User Click\nOn-Demand RAG\nNew Snapshot Version"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT

    tb_b = s11.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "AI should be expensive only when new intelligence is required."
    p_b.font.size = Pt(18)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s11,
        "Recommendation snapshots eliminate redundant LLM token costs when reviewing requests.",
        "When an employee generates a recommendation, IPMS persists a versioned recommendation snapshot. When the supervisor reviews the request later, the system loads the cached snapshot with 0 token overhead and sub-5ms latency. AI runs on demand, not on every page reload.",
        "1.0 min",
        "When the AI recommends a vendor, who retains the final decision authority?")

    # =========================================================================
    # SLIDE 12: Recommendation ≠ Authority (Audited Overrides)
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_bg(s12)
    add_category_header(s12, "GOVERNANCE & ACCOUNTABILITY", "Recommendation ≠ Authority")

    tb = s12.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(11.7), Inches(1.4))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "RECOMMENDATION ≠ AUTHORITY"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c1 = make_card(s12, Inches(1.5), Inches(3.4), Inches(4.8), Inches(2.0), bg=NAVY_CARD, border=CYAN_ACCENT)
    tf1 = c1.text_frame
    tf1.margin_top = Inches(0.4)
    p = tf1.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "AI RECOMMENDS\n\nSurfaces Evidence & Scores"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c2 = make_card(s12, Inches(7.0), Inches(3.4), Inches(4.8), Inches(2.0), bg=NAVY_CARD, border=AMBER)
    tf2 = c2.text_frame
    tf2.margin_top = Inches(0.4)
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "HUMAN DECIDES\n\nOverride Requires Justification"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = AMBER

    tb_b = s12.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(1.0))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = '\"The System Owns Intelligence. Humans Own Accountability.\"'
    p_b.font.size = Pt(22)
    p_b.font.bold = True
    p_b.font.color.rgb = CYAN_ACCENT

    set_notes(s12,
        "Supervisors retain absolute decision authority; overrides require mandatory auditable justification.",
        "In IPMS, the AI recommends, but the supervisor decides. If a supervisor overrides the system recommendation, a mandatory justification modal is triggered and logged in the immutable audit ledger. Intelligence assists—humans remain accountable.",
        "1.0 min",
        "How do recommendations become actual market competition?")

    # =========================================================================
    # SLIDE 13: A Recommendation Isn't a Purchase Order (RFQ + Vendor Portal)
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_bg(s13)
    add_category_header(s13, "MARKET COMPETITION", "A Recommendation Isn't a Purchase Order")

    steps13 = [
        ("01", "RECOMMEND", "Top 3 Suppliers", SLATE_MUTED),
        ("02", "INVITE", "Multi-Vendor RFQ", CYAN_ACCENT),
        ("03", "COMPETE", "Supplier Portal Bids", MICRON_BLUE),
        ("04", "COMPARE", "5-Factor Model V2", EMERALD)
    ]
    for i, (num, title, sub, col) in enumerate(steps13):
        c = make_card(s13, Inches(0.8 + i * 3.0), Inches(2.2), Inches(2.8), Inches(3.0), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{num}\n\n{title}\n\n{sub}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = col

    tb_b = s13.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "Recommendation identifies who to consider. Competition reveals the actual offer."
    p_b.font.size = Pt(18)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s13,
        "IPMS converts recommendations into real competition by issuing RFQs to up to 3 suppliers via a dedicated portal.",
        "We never buy directly based on an AI recommendation. Instead, the supervisor issues an RFQ to the top 3 suppliers. Suppliers log into their dedicated Vendor Portal to submit binding quotes with unit rates, lead times, and committed delivery dates.",
        "1.0 min",
        "When quotes arrive, how do we evaluate trade-offs?")

    # =========================================================================
    # SLIDE 14: Three Vendors. Three Different Trade-Offs. (5-Factor Model V2)
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_bg(s14)
    add_category_header(s14, "QUOTATION EVALUATION", "Three Vendors. Three Different Trade-Offs.")

    v_data = [
        ("VENDOR A", "$42 / Unit", "7 Days Lead Time", "88% Quality Score", ROSE),
        ("VENDOR B", "$48 / Unit", "2 Days Lead Time", "96% Quality Score", EMERALD),
        ("VENDOR C", "$45 / Unit", "4 Days Lead Time", "91% Quality Score", MICRON_BLUE)
    ]
    for i, (v_name, prc, lead, qlty, col) in enumerate(v_data):
        c = make_card(s14, Inches(0.8 + i * 4.0), Inches(2.0), Inches(3.7), Inches(2.8), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.3)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{v_name}\n\n{prc}\n{lead}\n{qlty}"
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = WHITE

    tb_b = s14.shapes.add_textbox(Inches(0.8), Inches(5.1), Inches(11.7), Inches(1.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "5-Factor Model V2: Price (35%) + Delivery Date (20%) + Lead Time (15%) + Reliability (15%) + Quality (15%)"
    p_b.font.size = Pt(13)
    p_b.font.color.rgb = CYAN_ACCENT

    p_b2 = tb_b.text_frame.add_paragraph()
    p_b2.alignment = PP_ALIGN.CENTER
    p_b2.text = '\"We don\'t optimize for the cheapest quote. We optimize for the best procurement outcome.\"'
    p_b2.font.size = Pt(18)
    p_b2.font.bold = True
    p_b2.font.color.rgb = WHITE
    p_b2.space_before = Pt(8)

    set_notes(s14,
        "The 5-Factor Quotation Model V2 evaluates total cost of ownership against lead time velocity and defect rates.",
        "Vendor A is the cheapest at $42, but takes 7 days with higher defect risk. Vendor B is $48, but delivers in 2 days with 96% quality. Our deterministic 5-Factor Model V2 scores price at 35%, delivery date at 20%, lead time at 15%, reliability at 15%, and quality at 15%—safeguarding against lowball bids that fail SLAs.",
        "1.0 min",
        "Once confirmed, how does execution happen?")

    # =========================================================================
    # SLIDE 15: Intelligence Is Useless If Execution Isn't Reliable
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_bg(s15)
    add_category_header(s15, "SAFE EXECUTION", "Intelligence Is Useless If Execution Isn't Reliable")

    c1 = make_card(s15, Inches(0.8), Inches(2.2), Inches(3.6), Inches(2.8), bg=NAVY_CARD, border=NAVY_CARD_BORDER)
    tf1 = c1.text_frame
    p = tf1.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "SUPERVISOR\nAPPROVAL\n\nFinal Sign-off\nDepartment Ledger"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c2 = make_card(s15, Inches(4.8), Inches(2.2), Inches(3.7), Inches(2.8), bg=NAVY_CARD, border=MICRON_BLUE)
    tf2 = c2.text_frame
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "IDEMPOTENT\nPO ENGINE\n\nZero Duplicate Risk\nReportLab PDF"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = CYAN_ACCENT

    c3 = make_card(s15, Inches(8.9), Inches(2.2), Inches(3.6), Inches(2.8), bg=NAVY_CARD, border=EMERALD)
    tf3 = c3.text_frame
    p = tf3.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "OFFICIAL PO\n& PDF ISSUED\n\nInstant In-App Alert\nVendor Email Dispatch"
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = EMERALD

    tb_b = s15.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "One Decision → One Safe, Legally Binding Purchase Order."
    p_b.font.size = Pt(18)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s15,
        "Idempotent PO generation guarantees single PDF creation and automated vendor alerts.",
        "Upon final approval, IPMS generates an official Purchase Order and compiles an immutable PDF via ReportLab. Our idempotent architecture ensures that network retries or repeated clicks never produce duplicate PO records or charges.",
        "1.0 min",
        "Let us examine the complete 4-tier system architecture.")

    # =========================================================================
    # SLIDE 16: SYSTEM ARCHITECTURE — 4-Tier Blueprint
    # (Incorporating Uploaded Screenshot #2)
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    set_bg(s16)
    add_category_header(s16, "SYSTEM ARCHITECTURE", "Intelligent Procurement System")

    tiers = [
        ("Actors & Roles", "Requester / Employee   |   Department Supervisor   |   Vendor Supplier", CYAN_ACCENT),
        ("Presentation Layer", "PR Creation Modal   |   Supervisor Checking Sheet   |   Quotation Matrix & Vendor Portal", WHITE),
        ("FastAPI Backend & Intelligence Engine", "Core: PR State Machine, RFQ Engine, Quotations, Idempotent PO\n3-Tier Intelligence: 1. Deterministic Engine  |  2. Analytical Engine  |  3. Generative Copilot & RAG", MICRON_BLUE),
        ("Data & Storage", "Relational Database (SQLAlchemy)   |   pgvector / Vector Embeddings   |   Local Filesystem for PO PDFs", EMERALD)
    ]

    for i, (t_title, t_content, col) in enumerate(tiers):
        h = Inches(1.3) if i == 2 else Inches(0.95)
        top_y = Inches(1.8 + i * 1.15) if i < 3 else Inches(1.8 + 2 * 1.15 + 1.4)
        c = make_card(s16, Inches(0.8), top_y, Inches(11.733), h, bg=NAVY_CARD, border=NAVY_CARD_BORDER)
        tf = c.text_frame
        tf.margin_left = Inches(0.4)
        tf.margin_top = Inches(0.12)

        p = tf.paragraphs[0]
        p.text = t_title.upper()
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = col

        p_sub = tf.add_paragraph()
        p_sub.text = t_content
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = SLATE_LIGHT

    set_notes(s16,
        "Complete 4-tier architecture: actors, Next.js presentation, FastAPI backend with 3 intelligence tiers, and database persistence.",
        "Here is the complete system blueprint: Three distinct actor roles interact through Next.js 14. The FastAPI backend orchestrates core state machines alongside our Three-Tier Intelligence Engine: Deterministic for stock and duplicate rules, Analytical for 5-factor scoring, and Generative for RAG qualitative synthesis. All backed by ACID persistence and PDF storage.",
        "1.0 min",
        "Let us look at how the technology stack is structured.")

    # =========================================================================
    # SLIDE 17: TECH STACK — A Modular Monolith, Not a Maze of Services
    # (Incorporating Uploaded Screenshot #5)
    # =========================================================================
    s17 = prs.slides.add_slide(blank_layout)
    set_bg(s17)
    add_category_header(s17, "TECH STACK", "A modular monolith, not a maze of services")

    tech_cards = [
        ("Frontend", "Next.js 14\nReact 18\nTypeScript\nTailwind CSS\nLucide Icons", CYAN_ACCENT),
        ("Backend", "Python 3.12\nFastAPI\nSQLAlchemy\nPydantic v2\nReportLab PDF", WHITE),
        ("Database", "PostgreSQL\nSQLite Async\npgvector\nEmbeddings", MICRON_BLUE),
        ("Auth & Security", "JWT Bearer\nBCrypt Passwords\nBackend RBAC\nAudit Logs", AMBER),
        ("AI / LLM", "Google Gemini\nPluggable RAG\nSnapshot Cache\nOffline Fallback", EMERALD)
    ]

    for i, (title, details, col) in enumerate(tech_cards):
        c = make_card(s17, Inches(0.8 + i * 2.4), Inches(1.9), Inches(2.2), Inches(3.7), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.3)

        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = title
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = f"\n{details}"
        p2.font.size = Pt(12)
        p2.font.color.rgb = SLATE_LIGHT

    tb_b = s17.shapes.add_textbox(Inches(0.8), Inches(5.9), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "A modular monolith with clear internal separation — zero unnecessary microservice complexity."
    p_b.font.size = Pt(14)
    p_b.font.bold = True
    p_b.font.color.rgb = CYAN_ACCENT

    set_notes(s17,
        "Engineered for high maintainability, low operational complexity, and graceful offline fallback.",
        "We chose a modular monolith over microservice sprawl: Next.js 14 on the frontend, FastAPI and SQLAlchemy on the backend, JWT security, and pluggable AI providers with automatic fallback. If external AI APIs are unreachable, core procurement, inventory checks, and quotation scoring run 100% uninterrupted.",
        "1.0 min",
        "How does our engineering align with Micron Technology values?")

    # =========================================================================
    # SLIDE 18: Alignment with Micron Technology Values
    # =========================================================================
    s18 = prs.slides.add_slide(blank_layout)
    set_bg(s18)
    add_category_header(s18, "STRATEGIC ALIGNMENT", "Why This Thinking Is Relevant to Micron")

    values = [
        ("PEOPLE", "Human experience fuels organizational intelligence through quarterly reviews", CYAN_ACCENT),
        ("INNOVATION", "Hybrid deterministic + RAG AI architecture engineered for zero hallucination", WHITE),
        ("COLLABORATION", "Unified workflow connecting Requesters, Supervisors, and Suppliers in one loop", MICRON_BLUE),
        ("TENACITY & QUALITY", "Governed overrides, audited revisions, and 5-factor quality scoring", EMERALD)
    ]
    for i, (val_title, desc, col) in enumerate(values):
        c = make_card(s18, Inches(0.8 + i * 3.0), Inches(2.2), Inches(2.8), Inches(3.2), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{val_title}\n\n{desc}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = col

    tb_b = s18.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = '\"We didn\'t just apply AI to procurement. We designed intelligence around responsible decisions.\"'
    p_b.font.size = Pt(17)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s18,
        "Direct alignment with Micron core values: People, Innovation, Collaboration, Tenacity, and Quality.",
        "Micron leads global semiconductor innovation, where precision and quality are paramount. IPMS directly embodies Micron values: valuing human experience, pioneering hybrid AI architecture, uniting cross-functional teams, and upholding uncompromising governance.",
        "1.0 min",
        "Let us examine our measurable business impact.")

    # =========================================================================
    # SLIDE 19: So What Does Better Intelligence Actually Create?
    # =========================================================================
    s19 = prs.slides.add_slide(blank_layout)
    set_bg(s19)
    add_category_header(s19, "BUSINESS VALUE", "So What Does Better Intelligence Actually Create?")

    outcomes = [
        ("LESS WASTE", "Inventory stock checks prevent unnecessary purchasing", EMERALD),
        ("LESS DUPLICATION", "±20% duplicate window flags parallel orders early", AMBER),
        ("BETTER OUTCOMES", "5-Factor Model V2 balances price, lead time & defect rates", CYAN_ACCENT),
        ("MORE TIME", "Instant decision context replaces manual data hunting", WHITE)
    ]
    for i, (otitle, odesc, col) in enumerate(outcomes):
        c = make_card(s19, Inches(0.8 + i * 3.0), Inches(2.2), Inches(2.8), Inches(3.2), bg=NAVY_CARD, border=col)
        tf = c.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{otitle}\n\n{odesc}"
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = col

    tb_b = s19.shapes.add_textbox(Inches(0.8), Inches(5.8), Inches(11.7), Inches(0.8))
    p_b = tb_b.text_frame.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "The ROI comes from empowering professionals to make decisions instead of hunting for data."
    p_b.font.size = Pt(16)
    p_b.font.bold = True
    p_b.font.color.rgb = WHITE

    set_notes(s19,
        "Four pillars of ROI: cost avoidance, duplicate prevention, quotation optimization, and engineering productivity.",
        "IPMS delivers value across four tangible dimensions: utilizing existing warehouse reserves, preventing duplicate spend, selecting bids based on total cost of ownership, and saving engineering hours spent searching for context.",
        "1.0 min",
        "Let us look at our transparent ROI framework.")

    # =========================================================================
    # SLIDE 20: Every Decision Has a Measurable Value (ROI Equation)
    # =========================================================================
    s20 = prs.slides.add_slide(blank_layout)
    set_bg(s20)
    add_category_header(s20, "ROI FRAMEWORK", "Every Decision Has a Measurable Value")

    v_metrics = [
        ("DON'T BUY\nWHAT YOU HAVE", "Stock Avoidance\n[Qty × Cost]"),
        ("DON'T BUY\nTWICE", "Duplicate Avoidance\n[PR Value]"),
        ("CHOOSE\nBETTER", "Quotation Optimization\n[SLA + Price]"),
        ("SEARCH\nLESS", "Productivity Recovery\n[Review Time Saved]")
    ]
    for i, (vm_title, vm_eq) in enumerate(v_metrics):
        c = make_card(s20, Inches(0.8 + i * 3.0), Inches(2.0), Inches(2.8), Inches(2.5),
                      bg=NAVY_CARD, border=CYAN_ACCENT)
        tf = c.text_frame
        tf.margin_top = Inches(0.3)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{vm_title}\n\n{vm_eq}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = WHITE

    c_eq = make_card(s20, Inches(0.8), Inches(4.8), Inches(11.733), Inches(1.6),
                     bg=RGBColor(6, 44, 34), border=EMERALD)
    tf_eq = c_eq.text_frame
    tf_eq.margin_top = Inches(0.2)
    p = tf_eq.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "MEASURABLE VALUE CREATED  −  SYSTEM OPERATING COST  =  TRUE ROI"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub = tf_eq.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Demonstrated Prototype Scenario: $1,250 stock avoided + $840 duplicate spend prevented on first 5 PRs."
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = RGBColor(236, 253, 245)
    p_sub.space_before = Pt(6)

    set_notes(s20,
        "Transparent ROI formula balancing tangible cost avoidance against operating costs.",
        "We do not extrapolate ungrounded enterprise savings. Instead, we provide a mathematically sound ROI equation: stock utilized times avoided cost, plus prevented duplicates, plus quotation optimization, minus operating cost. In our demonstrated prototype test runs, stock checks and duplicate alerts intercepted over $2,000 in unnecessary spend on the first batch alone.",
        "1.0 min",
        "Let us move to the closing statement and launch our live demonstration.")

    # =========================================================================
    # SLIDE 21: CLOSING & LIVE DEMO TRANSITION
    # =========================================================================
    s21 = prs.slides.add_slide(blank_layout)
    set_bg(s21)

    bar = s21.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(2.0), Inches(0.06))
    bar.fill.solid()
    bar.fill.fore_color.rgb = CYAN_ACCENT
    bar.line.fill.background()

    tb = s21.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(3.0))
    p = tb.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = '\"We Didn\'t Automate a Purchase Request.\"'
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p2 = tb.text_frame.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = "We Made Every Decision Around It More Intelligent."
    p2.font.size = Pt(30)
    p2.font.bold = True
    p2.font.color.rgb = CYAN_ACCENT
    p2.space_before = Pt(14)

    p3 = tb.text_frame.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = "From Processing Procurement to Understanding Procurement."
    p3.font.size = Pt(18)
    p3.font.color.rgb = SLATE_MUTED
    p3.space_before = Pt(18)

    c_demo = make_card(s21, Inches(3.6), Inches(5.1), Inches(6.1), Inches(1.4),
                       bg=MICRON_BLUE, border=CYAN_ACCENT)
    tf_d = c_demo.text_frame
    tf_d.margin_top = Inches(0.2)
    p_d = tf_d.paragraphs[0]
    p_d.alignment = PP_ALIGN.CENTER
    p_d.text = "LIVE SYSTEM DEMONSTRATION"
    p_d.font.size = Pt(18)
    p_d.font.bold = True
    p_d.font.color.rgb = WHITE

    p_d2 = tf_d.add_paragraph()
    p_d2.alignment = PP_ALIGN.CENTER
    p_d2.text = "http://localhost:3000"
    p_d2.font.size = Pt(13)
    p_d2.font.color.rgb = RGBColor(224, 242, 254)
    p_d2.space_before = Pt(4)

    set_notes(s21,
        "Transition into the live 8-10 minute end-to-end interactive demo across Employee, Supervisor, and Vendor roles.",
        "We have explained the decisions. Now let us follow an actual purchase request through the live application. We will switch to our live environment at localhost:3000 to demonstrate the employee request, stock check, duplicate detection, supervisor revision loop, vendor bidding portal, 5-factor quotation scoring, and instant PO generation in real time. Thank you.",
        "1.0 min",
        "Begin live demo.")

    out_paths = [
        r"d:\MICRO-HACK\IPMS_Micron_Presentation_Final_Deck.pptx",
        r"d:\MICRO-HACK\IPMS_Keynote_Presentation.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Hackathon_Final_Presentation.pptx"
    ]
    saved_any = False
    for p in out_paths:
        try:
            prs.save(p)
            print(f"Successfully created presentation: {p}")
            saved_any = True
        except Exception as e:
            print(f"Note: {p} is currently open in PowerPoint (skipped write).")

if __name__ == '__main__':
    build_deck()
