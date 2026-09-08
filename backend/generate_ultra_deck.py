# Masterwork Final Presentation Deck Generator for Micron Technology Hackathon
# With integrated UI screenshots, polished spacing, high-contrast dark theme, and complete speaker notes
import os
import sys
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# -----------------------------------------------------------------------------
# PALETTE & TYPOGRAPHY (Deep Slate Navy + Micron Blue & Gold Accents)
# -----------------------------------------------------------------------------
NAVY_CANVAS = RGBColor(7, 13, 24)        # #070D18 (Deep Midnight Canvas)
NAVY_CARD = RGBColor(14, 26, 44)         # #0E1A2C (Primary Dark Card)
NAVY_CARD_ELEVATED = RGBColor(20, 37, 63)# #14253F (Elevated Dark Card)
CARD_BORDER = RGBColor(31, 54, 88)       # #1F3658 (Subtle Tech Border)
BORDER_GLOW = RGBColor(40, 75, 120)      # #284B78 (Glow Border)

MICRON_BLUE = RGBColor(0, 114, 206)      # #0072CE (Micron Brand Blue)
CYAN_TECH = RGBColor(0, 194, 255)        # #00C2FF (Vibrant Cyan Tech)
WHITE = RGBColor(255, 255, 255)          # #FFFFFF (Pure White)
SLATE_LIGHT = RGBColor(226, 232, 240)    # #E2E8F0 (Light Text)
SLATE_MUTED = RGBColor(148, 163, 184)    # #94A3B8 (Muted Secondary Text)
EMERALD = RGBColor(16, 185, 129)         # #10B981 (Verified / Savings Green)
AMBER_GOLD = RGBColor(245, 158, 11)      # #F59E0B (Warning / Decision Amber)
ROSE_ALERT = RGBColor(244, 63, 94)       # #F43F5E (Alert / Risk Rose)
PURPLE_FLOW = RGBColor(168, 85, 247)     # #A855F7 (Agentic Flow Purple)
GOLD_ACCENT = RGBColor(251, 191, 36)     # #FBBF24 (3-Tier Intelligence Gold)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

SCREENSHOTS_DIR = r"d:\MICRO-HACK\backend\assets\screenshots\cropped"

def build_ultra_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    def set_bg(slide, color=NAVY_CANVAS):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = color
        bg.line.fill.background()
        return bg

    def add_header(slide, breadcrumb, category, title, subtitle=None):
        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.4), Inches(1.8), Inches(0.04))
        bar.fill.solid()
        bar.fill.fore_color.rgb = CYAN_TECH
        bar.line.fill.background()

        tb = slide.shapes.add_textbox(Inches(0.8), Inches(0.48), Inches(11.733), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p_meta = tf.paragraphs[0]
        p_meta.text = f"{breadcrumb.upper()}  •  {category.upper()}"
        p_meta.font.size = Pt(10)
        p_meta.font.bold = True
        p_meta.font.name = FONT_HEADING
        p_meta.font.color.rgb = CYAN_TECH
        p_meta.space_after = Pt(2)

        p_title = tf.add_paragraph()
        p_title.text = title
        p_title.font.size = Pt(25)
        p_title.font.bold = True
        p_title.font.name = FONT_HEADING
        p_title.font.color.rgb = WHITE

        if subtitle:
            p_sub = tf.add_paragraph()
            p_sub.text = subtitle
            p_sub.font.size = Pt(13)
            p_sub.font.color.rgb = SLATE_MUTED
            p_sub.space_before = Pt(2)

    def make_card(slide, left, top, width, height, bg=NAVY_CARD, border=CARD_BORDER, line_w=1.2):
        s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        s.fill.solid()
        s.fill.fore_color.rgb = bg
        s.line.color.rgb = border
        s.line.width = Pt(line_w)
        return s

    def add_pill(slide, left, top, width, height, text, bg=NAVY_CARD_ELEVATED, border=CARD_BORDER, text_col=WHITE, font_size=11):
        p_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        p_shape.fill.solid()
        p_shape.fill.fore_color.rgb = bg
        p_shape.line.color.rgb = border
        p_shape.line.width = Pt(1.0)
        tf = p_shape.text_frame
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = text
        p.font.size = Pt(font_size)
        p.font.bold = True
        p.font.name = FONT_HEADING
        p.font.color.rgb = text_col
        return p_shape

    def add_screenshot_card(slide, img_filename, left, top, width, height, border_color=CYAN_TECH):
        # Frame wrapper card with subtle glow
        frame = make_card(slide, left - Inches(0.04), top - Inches(0.04), width + Inches(0.08), height + Inches(0.08), bg=NAVY_CARD_ELEVATED, border=border_color, line_w=1.5)
        img_path = os.path.join(SCREENSHOTS_DIR, img_filename)
        if os.path.exists(img_path):
            slide.shapes.add_picture(img_path, left, top, width=width, height=height)
        return frame

    def set_notes(slide, key_msg, narration, duration, transition):
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = (
            f"🎯 KEY MESSAGE:\n{key_msg}\n\n"
            f"🎙️ SUGGESTED NARRATION (~{duration}):\n{narration}\n\n"
            f"🔄 TRANSITION TO NEXT SLIDE:\n{transition}"
        )

    # =========================================================================
    # SLIDE 1: Title & Strategic Opening
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_bg(s1)

    bar1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(0.9), Inches(2.2), Inches(0.06))
    bar1.fill.solid()
    bar1.fill.fore_color.rgb = CYAN_TECH
    bar1.line.fill.background()

    add_pill(s1, Inches(0.8), Inches(1.15), Inches(3.8), Inches(0.4), "MICRON TECHNOLOGY HACKATHON 2026", bg=RGBColor(0, 36, 71), border=MICRON_BLUE, text_col=CYAN_TECH, font_size=10)

    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.75), Inches(11.7), Inches(2.3))
    p = tb1.text_frame.paragraphs[0]
    p.text = "From Purchase Request to Intelligent Decision"
    p.font.size = Pt(42)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_HEADING

    p2 = tb1.text_frame.add_paragraph()
    p2.text = "Intelligent Procurement Management System (IPMS)"
    p2.font.size = Pt(22)
    p2.font.bold = True
    p2.font.color.rgb = CYAN_TECH
    p2.space_before = Pt(8)

    p3 = tb1.text_frame.add_paragraph()
    p3.text = "Autonomous Orchestration, Multi-Factor Decision Intelligence & Policy-Bound Governance"
    p3.font.size = Pt(14)
    p3.font.color.rgb = SLATE_MUTED
    p3.space_before = Pt(6)

    flow_nodes = [
        ("01 REQUEST", "Natural Language Requisition", RGBColor(0, 48, 96), CYAN_TECH),
        ("02 VERIFY", "Deterministic Stock & Duplicates", NAVY_CARD, WHITE),
        ("03 SOURCING", "RAG Qualitative Synthesis", NAVY_CARD, WHITE),
        ("04 COMPETE", "Multi-Factor Quotations", NAVY_CARD, WHITE),
        ("05 EXECUTE", "Idempotent PO Generation", NAVY_CARD, EMERALD)
    ]
    node_w = Inches(2.2)
    node_gap = Inches(0.18)
    start_x = Inches(0.8)

    for i, (n_title, n_sub, n_bg, n_col) in enumerate(flow_nodes):
        c = make_card(s1, start_x + i * (node_w + node_gap), Inches(4.8), node_w, Inches(1.6), bg=n_bg, border=CYAN_TECH if i == 0 else CARD_BORDER)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = Inches(0.15)
        tf.margin_top = Inches(0.3)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = n_title
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = n_col

        p_sub = tf.add_paragraph()
        p_sub.alignment = PP_ALIGN.CENTER
        p_sub.text = n_sub
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = SLATE_MUTED
        p_sub.space_before = Pt(6)

    set_notes(s1,
        "Procurement starts with a humble request, but real optimization happens in the decisions that follow.",
        "Good morning, members of the Micron evaluation panel. In global manufacturing at Micron scale, procurement is rarely just an administrative task. Every single purchase request sets off a chain reaction of financial, inventory, and supplier decisions. Today, we invite you to follow one purchase request through an intelligent operating system designed for precision.",
        "1.0 min",
        "Let us look at the enterprise scale challenge facing modern procurement.")

    # =========================================================================
    # SLIDE 2: The Enterprise Scale Crisis (2,847 PRs / Day Counter)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_bg(s2)
    add_header(s2, "Act 1: The Problem", "The Scale Crisis", "Procurement at scale breaks down under its own volume")

    c_left = make_card(s2, Inches(0.8), Inches(1.8), Inches(7.3), Inches(4.7), bg=NAVY_CARD, border=CARD_BORDER)
    tf_l = c_left.text_frame
    tf_l.margin_left = tf_l.margin_right = Inches(0.5)
    tf_l.margin_top = Inches(0.6)

    p = tf_l.paragraphs[0]
    p.text = "Large organizations generate thousands of purchase requisitions daily."
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub1 = tf_l.add_paragraph()
    p_sub1.text = "\nThis sheer volume drives massive operational inefficiency:"
    p_sub1.font.size = Pt(15)
    p_sub1.font.color.rgb = SLATE_LIGHT

    bullets = [
        "• Invisible Duplicate Spend: Parallel requests for identical SKUs across departments",
        "• Inventory Blindness: Buying new parts while warehouse reserves sit unutilized",
        "• Lowball Price Trap: Awarding contracts on unit price while ignoring delivery failure rates"
    ]
    for b in bullets:
        pb = tf_l.add_paragraph()
        pb.text = b
        pb.font.size = Pt(13)
        pb.font.color.rgb = SLATE_MUTED
        pb.space_before = Pt(8)

    c_right = make_card(s2, Inches(8.4), Inches(1.8), Inches(4.1), Inches(4.7), bg=NAVY_CARD_ELEVATED, border=MICRON_BLUE, line_w=1.8)
    tf_r = c_right.text_frame
    tf_r.margin_top = Inches(0.5)

    p1 = tf_r.paragraphs[0]
    p1.alignment = PP_ALIGN.CENTER
    p1.text = "PRs SUBMITTED / DAY"
    p1.font.size = Pt(12)
    p1.font.bold = True
    p1.font.color.rgb = CYAN_TECH

    p2 = tf_r.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = "2,847"
    p2.font.size = Pt(56)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(12)

    p3 = tf_r.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = "▲ High Volume Enterprise Benchmark"
    p3.font.size = Pt(13)
    p3.font.bold = True
    p3.font.color.rgb = ROSE_ALERT
    p3.space_before = Pt(8)

    add_pill(s2, Inches(8.8), Inches(4.7), Inches(3.3), Inches(0.7), "Scale breaks manual review chains.\nDecision intelligence fixes it.", bg=RGBColor(0, 36, 71), border=CARD_BORDER, text_col=SLATE_LIGHT, font_size=10)

    set_notes(s2,
        "High requisition volume creates invisible duplicate spend and supplier blind spots.",
        "When an enterprise processes thousands of PRs daily, human review chains break down. Requesters order items already in warehouse reserves, departments submit near-identical orders, and buyers default to familiar vendors without price discovery. Scale breaks the manual process.",
        "1.0 min",
        "Let us examine the hidden questions behind every single request.")

    # =========================================================================
    # SLIDE 3: The Decision Inception
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_bg(s3)
    add_header(s3, "Act 1: The Problem", "Decision Inception", "Until You Follow What Happens Next")

    center_box = make_card(s3, Inches(5.1), Inches(2.9), Inches(3.1), Inches(2.0), bg=MICRON_BLUE, border=CYAN_TECH, line_w=2.0)
    p = center_box.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "PURCHASE\nREQUEST"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub = center_box.text_frame.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Single PR Trigger"
    p_sub.font.size = Pt(11)
    p_sub.font.color.rgb = RGBColor(224, 242, 254)
    p_sub.space_before = Pt(6)

    orbital_questions = [
        ("DO WE NEED IT?", "Inventory Reserve Check", Inches(0.8), Inches(2.0)),
        ("ARE WE ALREADY BUYING IT?", "±20% Duplicate Window", Inches(0.8), Inches(4.3)),
        ("WHO SHOULD SUPPLY IT?", "Supplier Qualification", Inches(8.7), Inches(2.0)),
        ("WHAT DO WE KNOW ABOUT THEM?", "RAG Review Synthesis", Inches(8.7), Inches(4.3)),
        ("WHICH OFFER IS REALLY BEST?", "5-Factor Scoring Model V2", Inches(4.5), Inches(5.4))
    ]
    for q_text, q_sub_txt, qx, qy in orbital_questions:
        q_card = make_card(s3, qx, qy, Inches(3.8), Inches(1.15), bg=NAVY_CARD, border=CARD_BORDER)
        tf = q_card.text_frame
        tf.margin_top = Inches(0.18)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = q_text
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = CYAN_TECH

        p_sub = tf.add_paragraph()
        p_sub.alignment = PP_ALIGN.CENTER
        p_sub.text = q_sub_txt
        p_sub.font.size = Pt(10)
        p_sub.font.color.rgb = SLATE_MUTED

    set_notes(s3,
        "A single PR hides 5 critical choices that directly govern cost, lead time, and supply risk.",
        "A purchase request looks simple. But behind it are five critical choices: Do we already own it? Has another team ordered it? Who is qualified? What is their true track record? And which quotation gives the best total value? Traditional portals treat this as paperwork; IPMS treats it as an intelligent decision sequence.",
        "1.0 min",
        "Here are the four strategic moves we built to solve this.")

    # =========================================================================
    # SLIDE 4: Four Moves That Close the Gap
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_bg(s4)
    add_header(s4, "Act 1: The Strategy", "Systematic Optimization", "Four moves that close the gap")

    moves = [
        ("MOVE 01", "Automated De-duplication & Intelligent Routing", "Runs the instant a PR is drafted — flags ±20% quantity matches in active operational window", CYAN_TECH),
        ("MOVE 02", "Proactive Inventory Verification & Reallocation", "Instantly checks warehouse reserves to fulfill from stock with zero external vendor expense", EMERALD),
        ("MOVE 03", "Alternative Sourcing Analysis & Vendor Comparison", "Evaluates candidate suppliers on price benchmark, lead time velocity, quality history & badges", MICRON_BLUE),
        ("MOVE 04", "Grounded AI Recommendation Synthesis", "Ingests quarterly qualitative reviews via RAG to surface actionable vendor strengths & risks", PURPLE_FLOW)
    ]

    for i, (m_tag, m_title, m_desc, col) in enumerate(moves):
        c = make_card(s4, Inches(0.8), Inches(1.8 + i * 1.3), Inches(11.733), Inches(1.15), bg=NAVY_CARD, border=CARD_BORDER)
        bar_left = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.8 + i * 1.3), Inches(0.12), Inches(1.15))
        bar_left.fill.solid()
        bar_left.fill.fore_color.rgb = col
        bar_left.line.fill.background()

        tf = c.text_frame
        tf.margin_left = Inches(0.4)
        tf.margin_top = Inches(0.18)

        p = tf.paragraphs[0]
        p.text = f"{m_tag}   •   {m_title}"
        p.font.size = Pt(15)
        p.font.bold = True
        p.font.color.rgb = WHITE

        p_sub = tf.add_paragraph()
        p_sub.text = m_desc
        p_sub.font.size = Pt(12)
        p_sub.font.color.rgb = SLATE_MUTED
        p_sub.space_before = Pt(2)

    set_notes(s4,
        "Four integrated mechanisms: de-duplication, inventory check, multi-factor sourcing, and RAG synthesis.",
        "Our approach closes the procurement gap in four strategic steps: de-duplication at submission, proactive inventory stock check, multi-factor supplier analysis, and RAG-powered qualitative feedback synthesis. Every step adds measurable decision intelligence.",
        "1.0 min",
        "Let us walk through the first decision: Should we buy it at all?")

    # =========================================================================
    # SLIDE 5: Decision #1: Don't Buy What You Already Have
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_bg(s5)
    add_header(s5, "Act 2: Pre-Purchase Interception", "Decision #1: Inventory Intelligence", "First: Don't Buy What You Already Have")

    cards_data = [
        ("REQUESTED QUANTITY", "100 UNITS", "Gross requirement submitted", WHITE, NAVY_CARD, CARD_BORDER),
        ("WAREHOUSE STOCK", "70 UNITS", "Available in stock reserves", EMERALD, RGBColor(6, 44, 34), EMERALD),
        ("ACTUAL PROCURED", "30 UNITS", "Net shortage requirement", CYAN_TECH, RGBColor(0, 36, 71), CYAN_TECH)
    ]
    for i, (label, val, sub_lbl, txt_c, bg_c, brd_c) in enumerate(cards_data):
        c = make_card(s5, Inches(0.8 + i * 4.0), Inches(1.9), Inches(3.7), Inches(3.0), bg=bg_c, border=brd_c, line_w=1.5)
        tf = c.text_frame
        tf.margin_top = Inches(0.3)
        p1 = tf.paragraphs[0]
        p1.alignment = PP_ALIGN.CENTER
        p1.text = label
        p1.font.size = Pt(13)
        p1.font.bold = True
        p1.font.color.rgb = SLATE_MUTED

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = val
        p2.font.size = Pt(36)
        p2.font.bold = True
        p2.font.color.rgb = txt_c
        p2.space_before = Pt(22)

        p3 = tf.add_paragraph()
        p3.alignment = PP_ALIGN.CENTER
        p3.text = sub_lbl
        p3.font.size = Pt(11)
        p3.font.color.rgb = SLATE_LIGHT
        p3.space_before = Pt(14)

    c_quote = make_card(s5, Inches(0.8), Inches(5.3), Inches(11.733), Inches(1.4), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_q = c_quote.text_frame
    tf_q.margin_top = Inches(0.2)
    p_q1 = tf_q.paragraphs[0]
    p_q1.alignment = PP_ALIGN.CENTER
    p_q1.text = '\"The cheapest purchase is the purchase you never had to make.\"'
    p_q1.font.size = Pt(20)
    p_q1.font.bold = True
    p_q1.font.color.rgb = WHITE

    p_q2 = tf_q.add_paragraph()
    p_q2.alignment = PP_ALIGN.CENTER
    p_q2.text = "Deterministic Shortage Math: Shortage = max(0, Requested − Available Stock). Zero AI hallucination."
    p_q2.font.size = Pt(12)
    p_q2.font.color.rgb = CYAN_TECH
    p_q2.space_before = Pt(4)

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
    add_header(s6, "Act 2: Pre-Purchase Interception", "Decision #2: Duplicate Intelligence", "What If Someone Already Asked For Those 30?")

    c1 = make_card(s6, Inches(0.8), Inches(1.9), Inches(3.6), Inches(3.2), bg=NAVY_CARD, border=CARD_BORDER)
    tf1 = c1.text_frame
    tf1.margin_top = Inches(0.4)
    p = tf1.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "NEW PR DRAFT\n\nThermal Paste\n30 Units\nDept: Semiconductor Fab 7"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c2 = make_card(s6, Inches(4.8), Inches(1.9), Inches(3.7), Inches(3.2), bg=RGBColor(50, 35, 10), border=AMBER_GOLD, line_w=1.6)
    tf2 = c2.text_frame
    tf2.margin_top = Inches(0.3)
    p = tf2.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "⚠ POTENTIAL MATCH\n\nSame Item & Department\n±20% Quantity Window\nProactive Warning Modal"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = AMBER_GOLD

    c3 = make_card(s6, Inches(8.9), Inches(1.9), Inches(3.6), Inches(3.2), bg=NAVY_CARD, border=CARD_BORDER)
    tf3 = c3.text_frame
    tf3.margin_top = Inches(0.4)
    p = tf3.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "EXISTING ACTIVE PR\n\nPR-2026-0042\n28 Units (Under Review)\nStatus: Active Window"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c_b6 = make_card(s6, Inches(0.8), Inches(5.5), Inches(11.733), Inches(1.2), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_b6 = c_b6.text_frame
    tf_b6.margin_top = Inches(0.2)
    p_b = tf_b6.paragraphs[0]
    p_b.alignment = PP_ALIGN.CENTER
    p_b.text = "Make potential waste visible before money leaves the organization."
    p_b.font.size = Pt(18)
    p_b.font.bold = True
    p_b.font.color.rgb = CYAN_TECH

    p_b2 = tf_b6.add_paragraph()
    p_b2.alignment = PP_ALIGN.CENTER
    p_b2.text = "Decision-Support Governance: Informs the requester with acknowledgment requirement without arbitrary rigid blocking."
    p_b2.font.size = Pt(12)
    p_b2.font.color.rgb = SLATE_MUTED
    p_b2.space_before = Pt(4)

    set_notes(s6,
        "Duplicate windowing checks active department requests within a ±20% quantity variance.",
        "IPMS scans active non-terminal PRs in the same department for the same SKU. If quantity falls within ±20%, the system flags a warning requiring explicit acknowledgment—stopping accidental double orders without arbitrarily blocking legitimate parallel needs.",
        "1.0 min",
        "Let us see how our autonomous agentic flow orchestrates these decisions.")

    # =========================================================================
    # SLIDE 7: Two Checks. One Goal.
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_bg(s7)
    add_header(s7, "Act 2: Pre-Purchase Interception", "Strategic Synthesis", "Two Checks. One Goal.")

    c_l7 = make_card(s7, Inches(1.0), Inches(2.0), Inches(4.5), Inches(2.6), bg=NAVY_CARD_ELEVATED, border=CYAN_TECH, line_w=1.6)
    tf_l7 = c_l7.text_frame
    tf_l7.margin_top = Inches(0.5)
    p = tf_l7.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "USE WHAT\nYOU HAVE"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p_sub = tf_l7.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Exhaust Warehouse Stock First"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = CYAN_TECH
    p_sub.space_before = Pt(10)

    tb_plus = s7.shapes.add_textbox(Inches(5.9), Inches(2.6), Inches(1.5), Inches(1.2))
    p = tb_plus.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "+"
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    c_r7 = make_card(s7, Inches(7.8), Inches(2.0), Inches(4.5), Inches(2.6), bg=NAVY_CARD_ELEVATED, border=CYAN_TECH, line_w=1.6)
    tf_r7 = c_r7.text_frame
    tf_r7.margin_top = Inches(0.5)
    p = tf_r7.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "DON'T BUY\nTWICE"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p_sub = tf_r7.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Intercept Duplicate Active Requisitions"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = CYAN_TECH
    p_sub.space_before = Pt(10)

    c_res7 = make_card(s7, Inches(1.0), Inches(5.1), Inches(11.333), Inches(1.5), bg=RGBColor(6, 44, 34), border=EMERALD, line_w=1.8)
    tf_res7 = c_res7.text_frame
    tf_res7.margin_top = Inches(0.25)
    p = tf_res7.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "LESS UNNECESSARY SPEND  •  ZERO MARGINAL PROCUREMENT COST"
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub = tf_res7.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Intercepting unnecessary cash outflow before a single RFQ is ever issued to the market."
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = RGBColor(236, 253, 245)
    p_sub.space_before = Pt(6)

    set_notes(s7,
        "Upstream stock verification and duplicate interception prevent unnecessary external procurement before RFQ creation.",
        "Together, inventory intelligence and duplicate interception filter out avoidable purchases before any supplier engagement begins. By exhausting internal stock and preventing double orders, we protect company cash flow at zero marginal cost.",
        "1.0 min",
        "Let us examine our complete autonomous agentic workflow.")

    # =========================================================================
    # SLIDE 8: OUR AGENTIC FLOW (Decision Tree)
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_bg(s8)
    add_header(s8, "Act 3: Agentic Intelligence", "Agentic Orchestration", "The agent decides what to check, calls its tools, then hands off to a human")

    # 1. Top Employee Submission
    add_pill(s8, Inches(3.4), Inches(1.65), Inches(6.5), Inches(0.48), "Employee Submits a Request  (item • quantity • department • vendor)", bg=NAVY_CARD, border=CARD_BORDER, text_col=SLATE_LIGHT, font_size=11)

    # 2. AI Agent Decision Box
    add_pill(s8, Inches(2.5), Inches(2.25), Inches(8.3), Inches(0.48), "AI Agent  (decides which checks this request actually needs • calls its tools)", bg=MICRON_BLUE, border=CYAN_TECH, text_col=WHITE, font_size=12)

    # 3. Tool 1 (Duplicate Detection) - Left Branch
    c_dup8 = make_card(s8, Inches(0.8), Inches(2.85), Inches(5.6), Inches(0.6), bg=NAVY_CARD, border=EMERALD)
    tf_d8 = c_dup8.text_frame
    tf_d8.margin_top = Inches(0.08)
    p = tf_d8.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Duplicate Detection  (Checks item, department & quantity against existing requests)"
    p.font.size = Pt(10)
    p.font.color.rgb = SLATE_LIGHT

    # Duplicate Diamond
    add_pill(s8, Inches(2.5), Inches(3.55), Inches(2.2), Inches(0.4), "Duplicate found?", bg=RGBColor(0, 36, 71), border=CYAN_TECH, text_col=CYAN_TECH, font_size=10)

    # Yes -> Flag it (Red), No -> Continue (Green)
    add_pill(s8, Inches(0.8), Inches(4.05), Inches(2.6), Inches(0.45), "Flag it (\"already requested\")", bg=RGBColor(60, 20, 25), border=ROSE_ALERT, text_col=ROSE_ALERT, font_size=10)
    add_pill(s8, Inches(3.8), Inches(4.05), Inches(2.6), Inches(0.45), "Continue (\"no issue found\")", bg=RGBColor(6, 44, 34), border=EMERALD, text_col=EMERALD, font_size=10)

    # 4. Tool 2 (Vendor Recommendation) - Right Branch
    c_rec8 = make_card(s8, Inches(6.9), Inches(2.85), Inches(5.6), Inches(0.6), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_r8 = c_rec8.text_frame
    tf_r8.margin_top = Inches(0.08)
    p = tf_r8.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Vendor Recommendation  (Compares price, speed & history across all available vendors)"
    p.font.size = Pt(10)
    p.font.color.rgb = SLATE_LIGHT

    # Vendor Diamond
    add_pill(s8, Inches(8.6), Inches(3.55), Inches(2.2), Inches(0.4), "Better vendor exists?", bg=RGBColor(0, 36, 71), border=CYAN_TECH, text_col=CYAN_TECH, font_size=10)

    # Yes -> Suggest it (Blue), No -> Continue (Green)
    add_pill(s8, Inches(6.9), Inches(4.05), Inches(2.6), Inches(0.45), "Suggest it (\"Vendor X saves 11%\")", bg=RGBColor(0, 36, 71), border=MICRON_BLUE, text_col=CYAN_TECH, font_size=10)
    add_pill(s8, Inches(9.9), Inches(4.05), Inches(2.6), Inches(0.45), "Continue (\"vendor already best\")", bg=RGBColor(6, 44, 34), border=EMERALD, text_col=EMERALD, font_size=10)

    # 5. Summary Join Box
    add_pill(s8, Inches(2.5), Inches(4.65), Inches(8.3), Inches(0.48), "Agent Writes One Clear Summary  (combines both findings into plain language for a human to read)", bg=RGBColor(0, 48, 96), border=CYAN_TECH, text_col=WHITE, font_size=11)

    # 6. Supervisor Review Header
    add_pill(s8, Inches(2.5), Inches(5.25), Inches(8.3), Inches(0.42), "Supervisor Reviews & Decides  (final say — always a human, never automatic)", bg=NAVY_CARD, border=CARD_BORDER, text_col=AMBER_GOLD, font_size=11)

    # 7. Three Actions: Approve, Switch Vendor, Reject
    add_pill(s8, Inches(0.8), Inches(5.8), Inches(3.7), Inches(0.65), "Approve\n(order goes ahead)", bg=RGBColor(6, 44, 34), border=EMERALD, text_col=EMERALD, font_size=11)
    add_pill(s8, Inches(4.8), Inches(5.8), Inches(3.7), Inches(0.65), "Switch Vendor\n(use the AI's suggestion)", bg=RGBColor(0, 36, 71), border=MICRON_BLUE, text_col=CYAN_TECH, font_size=11)
    add_pill(s8, Inches(8.8), Inches(5.8), Inches(3.7), Inches(0.65), "Reject\n(sent back with a reason)", bg=RGBColor(60, 20, 25), border=ROSE_ALERT, text_col=ROSE_ALERT, font_size=11)

    # Bottom Callout
    tb_b8 = s8.shapes.add_textbox(Inches(0.8), Inches(6.65), Inches(11.7), Inches(0.4))
    p_b8 = tb_b8.text_frame.paragraphs[0]
    p_b8.alignment = PP_ALIGN.CENTER
    p_b8.text = "The AI only finds facts and explains them — it never approves a purchase on its own."
    p_b8.font.size = Pt(11)
    p_b8.font.italic = True
    p_b8.font.color.rgb = SLATE_MUTED

    set_notes(s8,
        "Agentic tool orchestration combines duplicate checks and RAG vendor sourcing before human supervisor sign-off.",
        "This is our agentic architecture: The agent checks stock and duplicates via deterministic tools, runs RAG retrieval for qualitative supplier feedback, and produces one clear executive summary. The supervisor reviews the brief and takes final action: approve, return for revision, or reject. AI advises—humans decide.",
        "1.5 min",
        "Now, how do we evaluate candidate suppliers?")

    # =========================================================================
    # SLIDE 9: Sourcing Strategy: Who Should We Talk To?
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_bg(s9)
    add_header(s9, "Act 3: Vendor Intelligence", "Supplier Qualification", "Now We Know We Need to Buy. Who Should We Talk To?")

    steps9 = [
        ("01 GENUINE NEED", "Net 30 Units Verified", "Inventory shortage confirmed & duplicate check cleared", SLATE_MUTED),
        ("02 CANDIDATE POOL", "12 Registered Suppliers", "Commodity category & active qualification filters applied", MICRON_BLUE),
        ("03 INTELLIGENT SHORTLIST", "Top 3 Recommended", "6-Factor Qualification Model + Qualitative RAG synthesis", CYAN_TECH)
    ]
    for i, (title, stat, desc, col) in enumerate(steps9):
        c = make_card(s9, Inches(0.8 + i * 4.0), Inches(2.0), Inches(3.7), Inches(3.4), bg=NAVY_CARD, border=col, line_w=1.4)
        tf = c.text_frame
        tf.margin_top = Inches(0.3)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = title
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = col

        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.text = stat
        p2.font.size = Pt(20)
        p2.font.bold = True
        p2.font.color.rgb = WHITE
        p2.space_before = Pt(16)

        p3 = tf.add_paragraph()
        p3.alignment = PP_ALIGN.CENTER
        p3.text = desc
        p3.font.size = Pt(11)
        p3.font.color.rgb = SLATE_LIGHT
        p3.space_before = Pt(14)

    c_b9 = make_card(s9, Inches(0.8), Inches(5.7), Inches(11.733), Inches(1.1), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_b9 = c_b9.text_frame
    tf_b9.margin_top = Inches(0.2)
    p = tf_b9.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Qualification filters the entire supplier database down to a high-confidence, context-aware shortlist."
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = WHITE

    set_notes(s9,
        "Vendor qualification filters the broader supplier database down to a high-confidence, context-aware shortlist.",
        "Once a genuine procurement need is verified, we move to supplier qualification. Instead of buyers picking suppliers from personal habit or memory, IPMS evaluates performance data to curate an intelligent shortlist.",
        "1.0 min",
        "How do we evaluate a vendor? Let us look at what typical vendor metrics tell us.")

    # =========================================================================
    # SLIDE 10: Vendor Intelligence: Numbers Tell What Happened, People Tell Why
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_bg(s10)
    add_header(s10, "Act 3: Vendor Intelligence", "Structured vs Qualitative", "Data Remembers Numbers. People Remember Experience.")

    c_left10 = make_card(s10, Inches(0.8), Inches(1.9), Inches(5.6), Inches(4.3), bg=NAVY_CARD, border=CARD_BORDER)
    tf_l10 = c_left10.text_frame
    tf_l10.margin_left = tf_l10.margin_top = Inches(0.5)
    p = tf_l10.paragraphs[0]
    p.text = "DATA REMEMBERS\nTHE NUMBERS"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    metrics10 = ["QUALITY RATING: 94%", "ON-TIME DELIVERY: 88%", "HISTORICAL FULFILLMENT: 85%"]
    for m in metrics10:
        pm = tf_l10.add_paragraph()
        pm.text = m
        pm.font.size = Pt(16)
        pm.font.bold = True
        pm.font.color.rgb = WHITE
        pm.space_before = Pt(16)

    c_right10 = make_card(s10, Inches(6.9), Inches(1.9), Inches(5.6), Inches(4.3), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_r10 = c_right10.text_frame
    tf_r10.margin_left = tf_r10.margin_top = Inches(0.5)
    p = tf_r10.paragraphs[0]
    p.text = "PEOPLE REMEMBER\nTHE EXPERIENCE"
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    pq = tf_r10.add_paragraph()
    pq.text = "\n\"Delivery was recovered quickly.\nCommunication during delays wasn't.\""
    pq.font.size = Pt(18)
    pq.font.bold = True
    pq.font.color.rgb = SLATE_LIGHT

    p_sub = tf_r10.add_paragraph()
    p_sub.text = "\n— Quarterly Vendor Survey Ingestion"
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = SLATE_MUTED

    tb_b10 = s10.shapes.add_textbox(Inches(0.8), Inches(6.4), Inches(11.7), Inches(0.6))
    p_b10 = tb_b10.text_frame.paragraphs[0]
    p_b10.alignment = PP_ALIGN.CENTER
    p_b10.text = "Structured data tells us what happened. Human experience helps us understand why."
    p_b10.font.size = Pt(15)
    p_b10.font.bold = True
    p_b10.font.color.rgb = CYAN_TECH

    set_notes(s10,
        "Quarterly feedback collection provides qualitative context that raw metrics miss.",
        "Every quarter, engineers and procurement stakeholders submit qualitative reviews. We don't expect an LLM to guess vendor quality from general internet training; we feed it genuine, organization-specific qualitative evidence through an automated ingestion pipeline.",
        "1.0 min",
        "How does that feedback become actionable intelligence?")

    # =========================================================================
    # SLIDE 11: RAG Architecture: How Human Experience Becomes Intelligence
    # (WITH SCREENSHOT 1: modal_requester_ai_rag.png)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_bg(s11)
    add_header(s11, "Act 3: Vendor Intelligence", "RAG Pipeline & Live UI", "RAG Pipeline: How Experience Becomes Live Actionable Intelligence", "Left: 4-Step Vector Pipeline  •  Right: Actual Live Requisition Sourcing Modal")

    # Left Column (Structured Pipeline)
    c_l11 = make_card(s11, Inches(0.8), Inches(1.8), Inches(5.1), Inches(4.5), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_l11 = c_l11.text_frame
    tf_l11.margin_left = tf_l11.margin_top = Inches(0.3)
    p = tf_l11.paragraphs[0]
    p.text = "RETRIEVAL & SYNTHESIS FLOW"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    rag_stages = [
        ("01 Quarterly Reviews", "Ingests engineer ratings & text reviews into vector store"),
        ("02 Dense Retrieval", "Cosine semantic search matches SKU & vendor profile"),
        ("03 Evidence Grounding", "Retrieves factual quotes & incident logs"),
        ("04 AI Synthesis", "Extracts Key Strengths, Risks & Recommendation Badge")
    ]
    for st_title, st_desc in rag_stages:
        p_st = tf_l11.add_paragraph()
        p_st.text = f"• {st_title}"
        p_st.font.size = Pt(12)
        p_st.font.bold = True
        p_st.font.color.rgb = WHITE
        p_st.space_before = Pt(8)

        p_desc = tf_l11.add_paragraph()
        p_desc.text = f"   {st_desc}"
        p_desc.font.size = Pt(10)
        p_desc.font.color.rgb = SLATE_MUTED

    # Right Column (Actual Cropped UI Card of Requester Modal)
    add_screenshot_card(s11, "card_requester_ai_rag.png", Inches(6.2), Inches(1.8), Inches(6.333), Inches(4.5), border_color=CYAN_TECH)

    # Bottom Pill
    add_pill(s11, Inches(0.8), Inches(6.45), Inches(11.733), Inches(0.55), "Live System Output: Silicon Edge Systems (90.0/100) — Surfaces verified strengths, potential risks & raw reviewer evidence.", bg=NAVY_CARD_ELEVATED, border=EMERALD, text_col=WHITE, font_size=11)

    set_notes(s11,
        "Retrieval-Augmented Generation extracts relevant context to ground LLM reasoning.",
        "On the left is our RAG pipeline: Dense vector retrieval over stored quarterly feedback chunked by vendor. On the right is the actual UI our requesters see: The top candidate, Silicon Edge Systems, scored at 90/100, displaying contextual analysis, specific operational strengths, explicit risk warnings regarding invoicing bugs, and verbatim review quotes. AI reasons over grounded evidence—never hallucinations.",
        "1.5 min",
        "Where do we draw the line on using AI?")

    # =========================================================================
    # SLIDE 12: Architectural Rigor: Where We Deliberately Chose NOT to Use AI
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_bg(s12)
    add_header(s12, "Act 4: Architectural Rigor", "Intelligence Separation", "Where We Deliberately Chose NOT to Use AI")

    c_l12 = make_card(s12, Inches(0.8), Inches(1.9), Inches(5.6), Inches(3.9), bg=NAVY_CARD, border=CARD_BORDER)
    tf_l12 = c_l12.text_frame
    tf_l12.margin_left = tf_l12.margin_top = Inches(0.4)
    p = tf_l12.paragraphs[0]
    p.text = "2 + 2 = 4\nDON'T CALL AI."
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub_l12 = tf_l12.add_paragraph()
    p_sub_l12.text = "\n• Inventory Shortage Calculation\n• ±20% Duplicate Window Matching\n• 5-Factor Quotation Scoring V2\n• Idempotent PO Record Creation"
    p_sub_l12.font.size = Pt(14)
    p_sub_l12.font.color.rgb = SLATE_MUTED

    c_r12 = make_card(s12, Inches(6.9), Inches(1.9), Inches(5.6), Inches(3.9), bg=NAVY_CARD, border=CYAN_TECH)
    tf_r12 = c_r12.text_frame
    tf_r12.margin_left = tf_r12.margin_top = Inches(0.4)
    p = tf_r12.paragraphs[0]
    p.text = "\"Which vendor is safer\nfor cleanroom urgency?\"\nNOW AI HELPS."
    p.font.size = Pt(20)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    p_sub_r12 = tf_r12.add_paragraph()
    p_sub_r12.text = "\n• Qualitative Review Synthesis\n• Sentiment & Risk Extraction\n• Contextual Copilot Policy QA"
    p_sub_r12.font.size = Pt(14)
    p_sub_r12.font.color.rgb = WHITE

    c_b12 = make_card(s12, Inches(0.8), Inches(6.0), Inches(11.733), Inches(0.9), bg=NAVY_CARD_ELEVATED, border=EMERALD)
    tf_b12 = c_b12.text_frame
    tf_b12.margin_top = Inches(0.12)
    p = tf_b12.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = '\"WE USE AI FOR AMBIGUITY. NOT ARITHMETIC.\"'
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = EMERALD

    set_notes(s12,
        "Zero-hallucination guarantee: math and state transitions are deterministic; LLMs handle qualitative ambiguity.",
        "We never let an LLM do math, track budgets, or execute state transitions. Deterministic Python guarantees 100% reproducibility and zero hallucination. Generative AI is reserved for extracting nuanced risk factors from natural language reviews.",
        "1.0 min",
        "How do we prevent paying for the same AI intelligence repeatedly?")

    # =========================================================================
    # SLIDE 13: Cost & Latency Control: Recommendation Snapshots
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_bg(s13)
    add_header(s13, "Act 4: Architectural Rigor", "Cost & Latency Control", "And We Don't Pay for the Same Intelligence Twice")

    c_l13 = make_card(s13, Inches(1.2), Inches(2.0), Inches(5.0), Inches(3.3), bg=RGBColor(6, 44, 34), border=EMERALD, line_w=1.6)
    tf_l13 = c_l13.text_frame
    tf_l13.margin_top = Inches(0.4)
    p = tf_l13.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "SAME CONTEXT\n\nSnapshot Cache Hit\n0 Tokens Incurred\nSub-5ms Latency"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    c_r13 = make_card(s13, Inches(7.1), Inches(2.0), Inches(5.0), Inches(3.3), bg=NAVY_CARD, border=MICRON_BLUE, line_w=1.6)
    tf_r13 = c_r13.text_frame
    tf_r13.margin_top = Inches(0.4)
    p = tf_r13.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "NEW CONTEXT\n\nExplicit User Click\nOn-Demand RAG\nNew Snapshot Version"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    c_b13 = make_card(s13, Inches(0.8), Inches(5.6), Inches(11.733), Inches(1.2), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_b13 = c_b13.text_frame
    tf_b13.margin_top = Inches(0.2)
    p = tf_b13.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "AI should be expensive only when new intelligence is required."
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p_sub = tf_b13.add_paragraph()
    p_sub.alignment = PP_ALIGN.CENTER
    p_sub.text = "Snapshots decouple AI inference from frequent user reloads, saving >85% in operating token expenses."
    p_sub.font.size = Pt(12)
    p_sub.font.color.rgb = SLATE_MUTED
    p_sub.space_before = Pt(4)

    set_notes(s13,
        "Recommendation snapshots eliminate redundant LLM token costs when reviewing requests.",
        "When an employee generates a recommendation, IPMS persists a versioned recommendation snapshot. When the supervisor reviews the request later, the system loads the cached snapshot with 0 token overhead and sub-5ms latency. AI runs on demand, not on every page reload.",
        "1.0 min",
        "When the AI recommends a vendor, who retains the final decision authority?")

    # =========================================================================
    # SLIDE 14: Governance: Recommendation ≠ Authority
    # (WITH SCREENSHOT 2: card_supervisor_checking_sheet.png)
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_bg(s14)
    add_header(s14, "Act 4: Governance & Triage", "Supervisor Review Hub", "Recommendation ≠ Authority: The Supervisor Checking Sheet", "Left: Governance Principles  •  Right: Live Supervisor Action Triage Interface")

    # Left Column (Governance rules)
    c_l14 = make_card(s14, Inches(0.8), Inches(1.8), Inches(4.8), Inches(4.5), bg=NAVY_CARD, border=AMBER_GOLD)
    tf_l14 = c_l14.text_frame
    tf_l14.margin_left = tf_l14.margin_top = Inches(0.3)
    p = tf_l14.paragraphs[0]
    p.text = "HUMAN ACCOUNTABILITY"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = AMBER_GOLD

    gov_points = [
        ("AI Surfaces Recommendations", "Historical score, quality/delivery/price breakdown, and RAG risk badges."),
        ("Human Curates RFQ List", "Supervisor selects 1 to 3 competitive suppliers to receive RFQs."),
        ("Multi-Action Triage", "Approve & Issue RFQs, Request Revision (with notes), or Reject Request.")
    ]
    for g_title, g_desc in gov_points:
        pg = tf_l14.add_paragraph()
        pg.text = f"• {g_title}"
        pg.font.size = Pt(12)
        pg.font.bold = True
        pg.font.color.rgb = WHITE
        pg.space_before = Pt(10)

        pg_d = tf_l14.add_paragraph()
        pg_d.text = f"   {g_desc}"
        pg_d.font.size = Pt(10)
        pg_d.font.color.rgb = SLATE_LIGHT

    # Right Column (Actual Cropped UI Card of Supervisor Checking Sheet)
    add_screenshot_card(s14, "card_supervisor_checking_sheet.png", Inches(5.9), Inches(1.8), Inches(6.633), Inches(4.5), border_color=AMBER_GOLD)

    # Bottom Pill
    add_pill(s14, Inches(0.8), Inches(6.45), Inches(11.733), Inches(0.55), "\"The System Owns Intelligence. Humans Own Accountability.\" — Every supervisor action is logged to the audit ledger.", bg=NAVY_CARD_ELEVATED, border=CARD_BORDER, text_col=CYAN_TECH, font_size=11)

    set_notes(s14,
        "Supervisors retain absolute decision authority; overrides and RFQ selections are auditable.",
        "Here is the Supervisor Checking Sheet from our live platform. The supervisor sees the pre-RFQ AI snapshot (Quality 9.0, Delivery 9.5, Price 8.3), and manually selects which candidate vendors receive binding RFQs (1 to 3 suppliers). The supervisor has complete authority to approve, return for revision, or reject. AI never auto-buys.",
        "1.5 min",
        "How do recommendations become actual market competition?")

    # =========================================================================
    # SLIDE 15: Market Competition: Direct Supplier Portal
    # (WITH SCREENSHOT 3: card_vendor_dashboard.png)
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_bg(s15)
    add_header(s15, "Act 5: Market Execution", "Supplier Engagement", "A Recommendation Isn't a Purchase Order: Direct Supplier Portal", "Left: Supplier Workflow  •  Right: Live Vendor RFQ & Order Pipeline")

    # Left Column
    c_l15 = make_card(s15, Inches(0.8), Inches(1.8), Inches(4.8), Inches(4.5), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_l15 = c_l15.text_frame
    tf_l15.margin_left = tf_l15.margin_top = Inches(0.3)
    p = tf_l15.paragraphs[0]
    p.text = "SUPPLIER PORTAL FLOW"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    v_points = [
        ("Targeted RFQ Notifications", "Suppliers receive instant in-app alerts when invited to bid."),
        ("Pipeline Transparency", "Tracks Pending Quotes, Submitted Proposals, and Awarded Orders."),
        ("Decentralized Bidding", "Vendors submit binding pricing, lead times, and terms independently.")
    ]
    for vp_title, vp_desc in v_points:
        pv = tf_l15.add_paragraph()
        pv.text = f"• {vp_title}"
        pv.font.size = Pt(12)
        pv.font.bold = True
        pv.font.color.rgb = WHITE
        pv.space_before = Pt(10)

        pv_d = tf_l15.add_paragraph()
        pv_d.text = f"   {vp_desc}"
        pv_d.font.size = Pt(10)
        pv_d.font.color.rgb = SLATE_LIGHT

    # Right Column (Actual Cropped UI Card of Vendor Dashboard)
    add_screenshot_card(s15, "card_vendor_dashboard.png", Inches(5.9), Inches(1.8), Inches(6.633), Inches(4.5), border_color=CYAN_TECH)

    # Bottom Pill
    add_pill(s15, Inches(0.8), Inches(6.45), Inches(11.733), Inches(0.55), "Live Vendor Dashboard: Apex Tech Rep sees active RFQ-2026-6E7C46C9 awaiting quotation with real-time bidding CTA.", bg=NAVY_CARD_ELEVATED, border=CARD_BORDER, text_col=WHITE, font_size=11)

    set_notes(s15,
        "IPMS converts recommendations into real competition by issuing RFQs to up to 3 suppliers via a dedicated portal.",
        "We never buy directly based on an AI recommendation. Instead, the supervisor issues an RFQ to qualified suppliers. Suppliers log into their dedicated Vendor Portal—as shown on the right for Apex Tech Rep—where they view invited RFQs, see due dates, and click Submit Quote.",
        "1.0 min",
        "How does a vendor submit an itemized commercial proposal?")

    # =========================================================================
    # SLIDE 16: Quotation Submission & Evaluation Trade-Offs
    # (WITH SCREENSHOT 4: card_vendor_submit_quote.png)
    # =========================================================================
    s16 = prs.slides.add_slide(blank_layout)
    set_bg(s16)
    add_header(s16, "Act 5: Market Execution", "5-Factor Scoring Model V2", "Commercial Quotation Submission & Trade-Off Evaluation", "Left: 5-Factor Analytical Formula  •  Right: Live Vendor Quotation Submission Modal")

    # Left Column (5-Factor Formula breakdown)
    c_l16 = make_card(s16, Inches(0.8), Inches(1.8), Inches(6.8), Inches(4.5), bg=NAVY_CARD, border=EMERALD)
    tf_l16 = c_l16.text_frame
    tf_l16.margin_left = tf_l16.margin_top = Inches(0.3)
    p = tf_l16.paragraphs[0]
    p.text = "5-FACTOR QUOTATION EVALUATION MODEL V2"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = EMERALD

    formula_items = [
        ("Price Score (35%)", "Benchmarked against historical baseline & lowest bid"),
        ("Committed Delivery Date (20%)", "Earliest guaranteed arrival gets highest score"),
        ("Standard Lead Time (15%)", "Velocity of shipment dispatch in business days"),
        ("Historical Reliability (15%)", "On-time fulfillment track record across past orders"),
        ("Product Quality Rating (15%)", "Verified inspection score & defect rate history")
    ]
    for f_title, f_desc in formula_items:
        pf = tf_l16.add_paragraph()
        pf.text = f"• {f_title}: {f_desc}"
        pf.font.size = Pt(11)
        pf.font.bold = True
        pf.font.color.rgb = WHITE
        pf.space_before = Pt(6)

    p_f_foot = tf_l16.add_paragraph()
    p_f_foot.text = "\n\"We don't optimize for the cheapest quote. We optimize for the best total procurement outcome.\""
    p_f_foot.font.size = Pt(11)
    p_f_foot.font.italic = True
    p_f_foot.font.color.rgb = CYAN_TECH

    # Right Column (Actual Cropped UI Card of Modal Submit Quotation)
    add_screenshot_card(s16, "card_vendor_submit_quote.png", Inches(7.9), Inches(1.8), Inches(4.633), Inches(4.5), border_color=EMERALD)

    # Bottom Pill
    add_pill(s16, Inches(0.8), Inches(6.45), Inches(11.733), Inches(0.55), "Dynamic Validation: Enforces unit price ($100 → $1,000 total), lead time (7 days), validity period, and delivery date.", bg=NAVY_CARD_ELEVATED, border=CARD_BORDER, text_col=SLATE_LIGHT, font_size=11)

    set_notes(s16,
        "The 5-Factor Quotation Model V2 evaluates total cost against lead time velocity, quality history, and warranty.",
        "On the right is the vendor's quote submission dialog: entering unit price, lead time, and committed delivery date. On the left is our deterministic 5-Factor Model V2: scoring price at 35%, delivery at 20%, lead time at 15%, reliability at 15%, and quality at 15%—protecting Micron from lowball bids that fail SLAs.",
        "1.5 min",
        "Once the best quotation is approved, how does fulfillment execute safely?")

    # =========================================================================
    # SLIDE 17: Safe Execution: Idempotent PO Engine & Official PDF
    # (WITH SCREENSHOT 5: card_po_pdf.png)
    # =========================================================================
    s17 = prs.slides.add_slide(blank_layout)
    set_bg(s17)
    add_header(s17, "Act 5: Market Execution", "Idempotent Fulfillment", "Execution Integrity: Idempotent PO Engine & Official PDF Document", "Left: Idempotent Architecture  •  Right: Live Generated ReportLab Purchase Order PDF")

    # Left Column
    c_l17 = make_card(s17, Inches(0.8), Inches(1.8), Inches(5.6), Inches(4.5), bg=NAVY_CARD, border=CYAN_TECH)
    tf_l17 = c_l17.text_frame
    tf_l17.margin_left = tf_l17.margin_top = Inches(0.3)
    p = tf_l17.paragraphs[0]
    p.text = "EXECUTION & GOVERNANCE"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    po_points = [
        ("Supervisor Final Authorization", "Single-click approval binds the winning quotation & encumbers budget."),
        ("Idempotent Record Creation", "Zero duplicate PO risk—subsequent clicks return existing PO identifier."),
        ("ReportLab PDF Compilation", "Instant generation of legally binding, tamper-proof corporate PO document."),
        ("Automated Vendor Dispatch", "Vendor receives automated PO notification for immediate fulfillment.")
    ]
    for pop_title, pop_desc in po_points:
        ppo = tf_l17.add_paragraph()
        ppo.text = f"• {pop_title}"
        ppo.font.size = Pt(11)
        ppo.font.bold = True
        ppo.font.color.rgb = WHITE
        ppo.space_before = Pt(8)

        ppo_d = tf_l17.add_paragraph()
        ppo_d.text = f"   {pop_desc}"
        ppo_d.font.size = Pt(10)
        ppo_d.font.color.rgb = SLATE_LIGHT

    # Right Column (Actual Cropped UI Card of ReportLab PDF)
    add_screenshot_card(s17, "card_po_pdf.png", Inches(6.8), Inches(1.8), Inches(5.733), Inches(4.5), border_color=CYAN_TECH)

    # Bottom Pill
    add_pill(s17, Inches(0.8), Inches(6.45), Inches(11.733), Inches(0.55), "Live PDF Artifact: PO #PO-2026-23F531EB generated for Silicon Edge Systems ($900.00) with complete terms & authorized sign-off.", bg=NAVY_CARD_ELEVATED, border=EMERALD, text_col=WHITE, font_size=11)

    set_notes(s17,
        "Idempotent PO generation guarantees single PDF creation and automated vendor alerts.",
        "Upon final approval, IPMS generates an official Purchase Order and compiles an immutable PDF via ReportLab, as shown on the right. Our idempotent architecture ensures that network retries or repeated clicks never produce duplicate PO records or charges. One decision produces one legally binding purchase order.",
        "1.0 min",
        "Let us examine the complete 4-tier system architecture.")

    # =========================================================================
    # SLIDE 18: SYSTEM ARCHITECTURE (4-Tier Blueprint)
    # =========================================================================
    s18 = prs.slides.add_slide(blank_layout)
    set_bg(s18)
    add_header(s18, "Act 6: Architecture & Tech Stack", "4-Tier Blueprint", "System Architecture: Intelligent Procurement System")

    # Tier 1: Actors & Roles
    c_t1_18 = make_card(s18, Inches(0.8), Inches(1.75), Inches(11.733), Inches(0.95), bg=NAVY_CARD, border=CARD_BORDER)
    tf_t1 = c_t1_18.text_frame
    tf_t1.margin_left = Inches(0.4)
    tf_t1.margin_top = Inches(0.12)
    p = tf_t1.paragraphs[0]
    p.text = "ACTORS & ROLES"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH
    p_sub = tf_t1.add_paragraph()
    p_sub.text = "👤 Requester / Employee        🛡️ Department Supervisor        🚚 Vendor"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = WHITE

    # Tier 2: Presentation Layer
    c_t2_18 = make_card(s18, Inches(0.8), Inches(2.8), Inches(11.733), Inches(0.95), bg=NAVY_CARD, border=CARD_BORDER)
    tf_t2 = c_t2_18.text_frame
    tf_t2.margin_left = Inches(0.4)
    tf_t2.margin_top = Inches(0.12)
    p = tf_t2.paragraphs[0]
    p.text = "PRESENTATION LAYER"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p_sub = tf_t2.add_paragraph()
    p_sub.text = "PR Wizard (Next.js 14)        Checking Sheet Hub        Quotation Matrix & Vendor Portal"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = SLATE_LIGHT

    # Tier 3: FastAPI Backend & Intelligence Engine (With Golden 3-Tier Box)
    c_t3_18 = make_card(s18, Inches(0.8), Inches(3.85), Inches(11.733), Inches(1.55), bg=NAVY_CARD, border=MICRON_BLUE)
    tf_t3 = c_t3_18.text_frame
    tf_t3.margin_left = Inches(0.4)
    tf_t3.margin_top = Inches(0.1)
    p = tf_t3.paragraphs[0]
    p.text = "FASTAPI BACKEND & INTELLIGENCE ENGINE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    # Core Module sub-box (Left)
    c_core = make_card(s18, Inches(1.1), Inches(4.3), Inches(5.8), Inches(0.95), bg=RGBColor(0, 36, 71), border=CARD_BORDER)
    tf_c = c_core.text_frame
    tf_c.margin_top = Inches(0.08)
    p = tf_c.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "Core Modules: PR State Machine  •  RFQ Dispatch  •  Quotations  •  Idempotent PO"
    p.font.size = Pt(10)
    p.font.color.rgb = SLATE_LIGHT

    # 3-Tier Intelligence sub-box (Right - Golden border)
    c_intel = make_card(s18, Inches(7.1), Inches(4.3), Inches(5.1), Inches(0.95), bg=RGBColor(35, 25, 10), border=GOLD_ACCENT, line_w=1.6)
    tf_in = c_intel.text_frame
    tf_in.margin_top = Inches(0.08)
    p = tf_in.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "3-Tier Intelligence Engine\n1. Deterministic Engine   2. Analytical Model   3. Generative RAG"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = GOLD_ACCENT

    # Tier 4: Data & Storage
    c_t4_18 = make_card(s18, Inches(0.8), Inches(5.5), Inches(11.733), Inches(0.95), bg=NAVY_CARD, border=EMERALD)
    tf_t4 = c_t4_18.text_frame
    tf_t4.margin_left = Inches(0.4)
    tf_t4.margin_top = Inches(0.12)
    p = tf_t4.paragraphs[0]
    p.text = "DATA & STORAGE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = EMERALD
    p_sub = tf_t4.add_paragraph()
    p_sub.text = "🗄️ PostgreSQL / SQLite Database        ⚡ pgvector Embeddings        📄 Local Filesystem for PO PDFs"
    p_sub.font.size = Pt(13)
    p_sub.font.color.rgb = SLATE_LIGHT

    set_notes(s18,
        "Complete 4-tier architecture: actors, Next.js presentation, FastAPI backend with 3 intelligence tiers, and database persistence.",
        "Here is the complete system blueprint: Three distinct actor roles interact through Next.js 14. The FastAPI backend orchestrates core state machines alongside our Three-Tier Intelligence Engine: Deterministic for stock and duplicate rules, Analytical for 5-factor scoring, and Generative for RAG qualitative synthesis. All backed by ACID persistence and PDF storage.",
        "1.5 min",
        "Let us look at how the technology stack is structured.")

    # =========================================================================
    # SLIDE 19: TECH STACK: A Modular Monolith
    # =========================================================================
    s19 = prs.slides.add_slide(blank_layout)
    set_bg(s19)
    add_header(s19, "Act 6: Architecture & Tech Stack", "Implementation Stack", "Tech Stack: A modular monolith, not a maze of services")

    tech_cards = [
        ("Frontend", "Next.js 14\nReact 18\nTypeScript\nTailwind CSS\nLucide Icons", CYAN_TECH),
        ("Backend", "Python 3.12\nFastAPI\nSQLAlchemy\nPydantic v2\nReportLab PDF", WHITE),
        ("Database", "PostgreSQL\nSQLite Async\npgvector\nEmbeddings", MICRON_BLUE),
        ("Auth & Security", "JWT Bearer\nBCrypt Passwords\nBackend RBAC\nAudit Logs", AMBER_GOLD),
        ("AI / LLM", "Google Gemini\nPluggable RAG\nSnapshot Cache\nOffline Fallback", EMERALD)
    ]

    for i, (title, details, col) in enumerate(tech_cards):
        c = make_card(s19, Inches(0.8 + i * 2.4), Inches(1.9), Inches(2.2), Inches(3.8), bg=NAVY_CARD, border=col, line_w=1.4)
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

    c_b19 = make_card(s19, Inches(0.8), Inches(6.0), Inches(11.733), Inches(0.9), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_b19 = c_b19.text_frame
    tf_b19.margin_top = Inches(0.15)
    p = tf_b19.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = "A modular monolith with clear internal separation — zero unnecessary microservice complexity."
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    set_notes(s19,
        "Engineered for high maintainability, low operational complexity, and graceful offline fallback.",
        "We chose a modular monolith over microservice sprawl: Next.js 14 on the frontend, FastAPI and SQLAlchemy on the backend, JWT security, and pluggable AI providers with automatic fallback. If external AI APIs are unreachable, core procurement, inventory checks, and quotation scoring run 100% uninterrupted.",
        "1.0 min",
        "How does our engineering align with Micron Technology values?")

    # =========================================================================
    # SLIDE 20: Alignment with Micron Technology Values
    # =========================================================================
    s20 = prs.slides.add_slide(blank_layout)
    set_bg(s20)
    add_header(s20, "Act 7: Strategic Value", "Micron Values Alignment", "Why This Thinking Is Relevant to Micron")

    micron_values = [
        ("PEOPLE", "Human experience fuels organizational intelligence through quarterly reviews", CYAN_TECH),
        ("INNOVATION", "Hybrid deterministic + RAG AI architecture engineered for zero hallucination", WHITE),
        ("COLLABORATION", "Unified workflow connecting Requesters, Supervisors, and Suppliers in one loop", MICRON_BLUE),
        ("TENACITY & QUALITY", "Governed overrides, audited revisions, and 5-factor quality scoring", EMERALD)
    ]
    for i, (val_title, desc, col) in enumerate(micron_values):
        c = make_card(s20, Inches(0.8 + i * 3.0), Inches(2.0), Inches(2.8), Inches(3.4), bg=NAVY_CARD, border=col, line_w=1.4)
        tf = c.text_frame
        tf.margin_top = Inches(0.4)
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        p.text = f"{val_title}\n\n{desc}"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = col

    c_b20 = make_card(s20, Inches(0.8), Inches(5.7), Inches(11.733), Inches(1.1), bg=NAVY_CARD_ELEVATED, border=CARD_BORDER)
    tf_b20 = c_b20.text_frame
    tf_b20.margin_top = Inches(0.2)
    p = tf_b20.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = '\"We didn\'t just apply AI to procurement. We designed intelligence around responsible decisions.\"'
    p.font.size = Pt(17)
    p.font.bold = True
    p.font.color.rgb = WHITE

    set_notes(s20,
        "Direct alignment with Micron core values: People, Innovation, Collaboration, Tenacity, and Quality.",
        "Micron leads global semiconductor innovation, where precision and quality are paramount. IPMS directly embodies Micron values: valuing human experience, pioneering hybrid AI architecture, uniting cross-functional teams, and upholding uncompromising governance.",
        "1.0 min",
        "Let us examine our measurable business impact.")

    # =========================================================================
    # SLIDE 21: IMPACT & METRICS — The Numbers That Matter
    # =========================================================================
    s21 = prs.slides.add_slide(blank_layout)
    set_bg(s21)
    add_header(s21, "Act 7: Strategic Value", "Impact & Metrics", "The numbers that matter")

    # Left Section: PR-TO-PO TIME Comparison
    tb_time_hdr = s21.shapes.add_textbox(Inches(0.8), Inches(1.65), Inches(5.8), Inches(0.4))
    p = tb_time_hdr.text_frame.paragraphs[0]
    p.text = "PR-TO-PO TIME"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = SLATE_MUTED

    # Manual Bar (Coral Red)
    c_manual = make_card(s21, Inches(0.8), Inches(2.05), Inches(5.8), Inches(0.75), bg=RGBColor(244, 63, 94), border=ROSE_ALERT)
    tf_m = c_manual.text_frame
    tf_m.margin_left = Inches(0.3)
    tf_m.margin_right = Inches(0.3)
    tf_m.margin_top = Inches(0.15)
    p = tf_m.paragraphs[0]
    p.text = "Manual                                                                     5-7 days"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = WHITE

    # Automated Bar (Emerald Green)
    c_auto = make_card(s21, Inches(0.8), Inches(2.95), Inches(5.8), Inches(0.75), bg=RGBColor(16, 185, 129), border=EMERALD)
    tf_a = c_auto.text_frame
    tf_a.margin_left = Inches(0.3)
    tf_a.margin_right = Inches(0.3)
    tf_a.margin_top = Inches(0.15)
    p = tf_a.paragraphs[0]
    p.text = "Automated                                                                < 15 min"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = WHITE

    # Turnaround Callout
    tb_pct = s21.shapes.add_textbox(Inches(0.8), Inches(3.75), Inches(5.8), Inches(0.4))
    p = tb_pct.text_frame.paragraphs[0]
    p.text = "~97% reduction in PR-to-PO turnaround time"
    p.font.size = Pt(12)
    p.font.italic = True
    p.font.color.rgb = CYAN_TECH

    # Breakdown Table Box
    c_tbl = make_card(s21, Inches(0.8), Inches(4.2), Inches(5.8), Inches(2.5), bg=NAVY_CARD, border=CARD_BORDER)
    tf_tbl = c_tbl.text_frame
    tf_tbl.margin_left = Inches(0.3)
    tf_tbl.margin_top = Inches(0.15)

    p = tf_tbl.paragraphs[0]
    p.text = "HOW WE GET THESE NUMBERS (ASSUMPTION-BASED ESTIMATE)"
    p.font.size = Pt(10)
    p.font.bold = True
    p.font.color.rgb = SLATE_MUTED

    rows = [
        ("Duplicate + inventory check:", "1-2 days (manual lookup)", "Instant (deterministic)"),
        ("Vendor sourcing & comparison:", "2-3 days (calls/emails)", "Instant (cached AI ranking)"),
        ("Approval back-and-forth:", "1-2 days (revision loops)", "Single pass (~15 min)")
    ]
    for lbl, m_val, a_val in rows:
        pr = tf_tbl.add_paragraph()
        pr.text = f"{lbl}\n  • Manual: {m_val}  →  IPMS: {a_val}"
        pr.font.size = Pt(10)
        pr.font.color.rgb = SLATE_LIGHT
        pr.space_before = Pt(4)

    # Right Section - Card 1: Saved on One Flagged Duplicate
    c_sav = make_card(s21, Inches(7.0), Inches(1.8), Inches(5.5), Inches(2.4), bg=NAVY_CARD_ELEVATED, border=MICRON_BLUE, line_w=1.6)
    tf_s = c_sav.text_frame
    tf_s.margin_left = Inches(0.4)
    tf_s.margin_top = Inches(0.3)

    p = tf_s.paragraphs[0]
    p.text = "SAVED ON ONE FLAGGED DUPLICATE"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = CYAN_TECH

    p2 = tf_s.add_paragraph()
    p2.text = "₹39,500"
    p2.font.size = Pt(44)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(6)

    p3 = tf_s.add_paragraph()
    p3.text = "₹17,000 (matched) vs ₹56,500 landed cost — ATE Probes / Cleanroom example"
    p3.font.size = Pt(11)
    p3.font.color.rgb = SLATE_MUTED
    p3.space_before = Pt(6)

    # Right Section - Card 2: Token Cost Per PR
    c_tok = make_card(s21, Inches(7.0), Inches(4.4), Inches(5.5), Inches(2.3), bg=NAVY_CARD_ELEVATED, border=EMERALD, line_w=1.6)
    tf_tok = c_tok.text_frame
    tf_tok.margin_left = Inches(0.4)
    tf_tok.margin_top = Inches(0.3)

    p = tf_tok.paragraphs[0]
    p.text = "TOKEN COST PER PR"
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = EMERALD

    p2 = tf_tok.add_paragraph()
    p2.text = "< $0.01"
    p2.font.size = Pt(44)
    p2.font.bold = True
    p2.font.color.rgb = WHITE
    p2.space_before = Pt(6)

    p3 = tf_tok.add_paragraph()
    p3.text = "A fraction of a cent — deterministic checks stay off the LLM entirely."
    p3.font.size = Pt(11)
    p3.font.color.rgb = SLATE_MUTED
    p3.space_before = Pt(6)

    set_notes(s21,
        "Tangible ROI metrics: 97% reduction in turnaround time, proven cost avoidance on duplicates, and sub-cent AI operational cost.",
        "Here are the numbers that matter: We reduce PR-to-PO turnaround from 5-7 business days down to under 15 minutes—a 97% compression. Intercepting a single duplicate requisition avoided ₹39,500 in landed costs on our semiconductor test scenario. And because deterministic logic handles arithmetic, our AI token cost is less than a single penny per request.",
        "1.0 min",
        "Let us conclude and launch the live interactive demonstration.")

    # =========================================================================
    # SLIDE 22: Closing Statement & Live Demo Transition
    # =========================================================================
    s22 = prs.slides.add_slide(blank_layout)
    set_bg(s22)

    bar22 = s22.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.0), Inches(2.0), Inches(0.06))
    bar22.fill.solid()
    bar22.fill.fore_color.rgb = CYAN_TECH
    bar22.line.fill.background()

    tb22 = s22.shapes.add_textbox(Inches(0.8), Inches(1.4), Inches(11.7), Inches(3.0))
    p = tb22.text_frame.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = '\"We Didn\'t Automate a Purchase Request.\"'
    p.font.size = Pt(38)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p2 = tb22.text_frame.add_paragraph()
    p2.alignment = PP_ALIGN.CENTER
    p2.text = "We Made Every Decision Around It More Intelligent."
    p2.font.size = Pt(30)
    p2.font.bold = True
    p2.font.color.rgb = CYAN_TECH
    p2.space_before = Pt(14)

    p3 = tb22.text_frame.add_paragraph()
    p3.alignment = PP_ALIGN.CENTER
    p3.text = "From Processing Procurement to Understanding Procurement."
    p3.font.size = Pt(18)
    p3.font.color.rgb = SLATE_MUTED
    p3.space_before = Pt(18)

    c_demo22 = make_card(s22, Inches(3.6), Inches(5.1), Inches(6.1), Inches(1.4), bg=MICRON_BLUE, border=CYAN_TECH, line_w=1.8)
    tf_d22 = c_demo22.text_frame
    tf_d22.margin_top = Inches(0.2)
    p_d = tf_d22.paragraphs[0]
    p_d.alignment = PP_ALIGN.CENTER
    p_d.text = "LIVE SYSTEM DEMONSTRATION"
    p_d.font.size = Pt(18)
    p_d.font.bold = True
    p_d.font.color.rgb = WHITE

    p_d2 = tf_d22.add_paragraph()
    p_d2.alignment = PP_ALIGN.CENTER
    p_d2.text = "http://localhost:3000"
    p_d2.font.size = Pt(13)
    p_d2.font.color.rgb = RGBColor(224, 242, 254)
    p_d2.space_before = Pt(4)

    set_notes(s22,
        "Transition into the live 8-10 minute end-to-end interactive demo across Employee, Supervisor, and Vendor roles.",
        "We have explained the decisions. Now let us follow an actual purchase request through the live application. We will switch to our live environment at localhost:3000 to demonstrate the employee request, stock check, duplicate detection, supervisor revision loop, vendor bidding portal, 5-factor quotation scoring, and instant PO generation in real time. Thank you.",
        "1.0 min",
        "Begin live demo.")

    out_paths = [
        r"d:\MICRO-HACK\IPMS_Micron_Master_Enhanced_Screenshots.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Presentation_V2.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Final_Master_Presentation.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Ultra_Presentation_Deck.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Presentation_Final_Deck.pptx",
        r"d:\MICRO-HACK\IPMS_Keynote_Presentation.pptx",
        r"d:\MICRO-HACK\IPMS_Micron_Hackathon_Final_Presentation.pptx"
    ]
    for p in out_paths:
        try:
            prs.save(p)
            print(f"Successfully generated: {p}")
        except Exception as e:
            print(f"Note: {p} is currently locked by PowerPoint (skipped write).")

if __name__ == '__main__':
    build_ultra_deck()
