import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.core.security import get_password_hash
from app.models.entities import (
    Department, User, UserRole, Item, Inventory, Vendor, VendorPerformance,
    VendorItemPerformance, VendorBadge, HistoricalPrice, PurchaseRequest,
    PurchaseRequestItem, PurchaseRequestReview, RFQ, Quotation, VendorSelectionDecision,
    PurchaseOrder, PRStatus, BadgeType, Notification, AuditLog, KnowledgeDocument, KnowledgeChunk
)
from app.intelligence.analytical import compute_vendor_badges
from app.ai.rag import ingest_document

def seed_database(db: Session, force: bool = False):
    """
    Seeds rich, realistic, enterprise procurement data with domain-specialized suppliers,
    differentiated product categories, and distinct preferred vendor choices for each product.
    """
    if not force and db.query(Department).first():
        return

    print("Seeding database with authentic enterprise procurement data...")

    # Clear existing data if forcing reseed
    if force:
        from app.core.database import Base, engine, SessionLocal
        db.rollback()
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()

    now = datetime.utcnow()

    # =========================================================================
    # 1. DEPARTMENTS
    # =========================================================================
    dept_it = Department(name="Information Technology")
    dept_ops = Department(name="Operations & Logistics")
    dept_fac = Department(name="Facilities & Ergonomics")
    dept_mkt = Department(name="Marketing & Communications")
    db.add_all([dept_it, dept_ops, dept_fac, dept_mkt])
    db.commit()

    # =========================================================================
    # 2. USERS (Supervisors, Employees, Admins)
    # =========================================================================
    hashed_pwd = get_password_hash("password123")

    sup_it = User(
        name="David Miller (IT Supervisor)",
        email="david.supervisor@company.com",
        password_hash=hashed_pwd,
        role=UserRole.SUPERVISOR.value,
        department_id=dept_it.id
    )
    sup_ops = User(
        name="Rachel Zhang (Ops Supervisor)",
        email="rachel.supervisor@company.com",
        password_hash=hashed_pwd,
        role=UserRole.SUPERVISOR.value,
        department_id=dept_ops.id
    )
    admin_user = User(
        name="System Administrator",
        email="admin@company.com",
        password_hash=hashed_pwd,
        role=UserRole.ADMIN.value
    )
    db.add_all([sup_it, sup_ops, admin_user])
    db.commit()

    dept_it.supervisors.append(sup_it)
    dept_fac.supervisors.append(sup_it)
    dept_ops.supervisors.append(sup_ops)
    dept_mkt.supervisors.append(sup_ops)

    emp_alex = User(
        name="Alex Turner (Senior DevOps)",
        email="alex.employee@company.com",
        password_hash=hashed_pwd,
        role=UserRole.EMPLOYEE.value,
        department_id=dept_it.id
    )
    emp_sarah = User(
        name="Sarah Jenkins (Ops Coordinator)",
        email="sarah.employee@company.com",
        password_hash=hashed_pwd,
        role=UserRole.EMPLOYEE.value,
        department_id=dept_ops.id
    )
    db.add_all([emp_alex, emp_sarah])
    db.commit()

    # =========================================================================
    # 3. VENDORS (Domain-Specialized Real Enterprise Suppliers)
    # =========================================================================
    # Hardware & Server Suppliers
    v_apex = Vendor(name="Apex Tech Supplies", email="sales@apextech.com", phone="+1-555-0101")
    v_silicon = Vendor(name="Silicon Edge Systems", email="enterprise@siliconedge.com", phone="+1-555-0102")
    v_bytecraft = Vendor(name="ByteCraft Computing", email="quotes@bytecraft.io", phone="+1-555-0103")

    # Ergonomic Furniture Suppliers
    v_ergo = Vendor(name="ErgoComfort Workspaces", email="b2b@ergocomfort.com", phone="+1-555-0104")
    v_modern = Vendor(name="Modern Office Interiors", email="commercial@modernoffice.com", phone="+1-555-0105")

    # Networking & Security Suppliers
    v_netcore = Vendor(name="NetCore Global Systems", email="networking@netcoresystems.com", phone="+1-555-0106")
    v_prime = Vendor(name="Prime Telecom Direct", email="enterprise@primetelecom.com", phone="+1-555-0107")

    # Office Supplies & Consumables
    v_budget = Vendor(name="Budget Wholesale Corp", email="bulk@budgetwholesale.com", phone="+1-555-0108")

    # Industrial Safety & Facilities
    v_safeguard = Vendor(name="SafeGuard Industrial Safety", email="orders@safeguardindustrial.com", phone="+1-555-0109")

    all_vendors = [v_apex, v_silicon, v_bytecraft, v_ergo, v_modern, v_netcore, v_prime, v_budget, v_safeguard]
    db.add_all(all_vendors)
    db.commit()

    # Vendor Portal User Accounts (All 9 Specialized Suppliers)
    u_v_apex = User(name="Apex Tech Rep", email="vendor.apex@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_apex.id)
    u_v_silicon = User(name="Silicon Edge Rep", email="vendor.quick@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_silicon.id)
    u_v_bytecraft = User(name="ByteCraft Rep", email="vendor.bytecraft@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_bytecraft.id)
    u_v_ergo = User(name="ErgoComfort Rep", email="vendor.ergo@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_ergo.id)
    u_v_modern = User(name="Modern Office Rep", email="vendor.modern@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_modern.id)
    u_v_netcore = User(name="NetCore Rep", email="vendor.netcore@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_netcore.id)
    u_v_prime = User(name="Prime Telecom Rep", email="vendor.prime@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_prime.id)
    u_v_budget = User(name="Budget Wholesale Rep", email="vendor.budget@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_budget.id)
    u_v_safeguard = User(name="SafeGuard Rep", email="vendor.safeguard@company.com", password_hash=hashed_pwd, role=UserRole.VENDOR.value, vendor_id=v_safeguard.id)
    db.add_all([u_v_apex, u_v_silicon, u_v_bytecraft, u_v_ergo, u_v_modern, u_v_netcore, u_v_prime, u_v_budget, u_v_safeguard])
    db.commit()

    # =========================================================================
    # 4. ITEMS & INVENTORY (Differentiated Product Catalog)
    # =========================================================================
    item_dell = Item(name="Dell Precision 5820 Workstation", description="Intel Xeon W-2245, 64GB ECC RAM, 1TB NVMe, NVIDIA RTX A4000 16GB", category="Hardware", unit="units")
    item_macbook = Item(name="Apple MacBook Pro 16\" (M3 Max)", description="16-inch Liquid Retina XDR, M3 Max 16-Core CPU, 64GB Unified RAM, 1TB SSD", category="Hardware", unit="units")
    item_monitor = Item(name="Dell UltraSharp 34\" Curved USB-C Monitor", description="3440 x 1440 WQHD, IPS, 90W USB-C Power Delivery, KVM Switch", category="Hardware", unit="units")
    item_chair = Item(name="Ergonomic Herman Miller Aeron Chair", description="PostureFit SL lumbar support, fully adjustable arms, Forward Tilt, Graphite", category="Furniture", unit="units")
    item_desk = Item(name="Steelcase Migration Height-Adjustable Desk", description="Electric dual-motor standing desk, 60x30 inch oak finish, memory controller", category="Furniture", unit="units")
    item_cisco = Item(name="Cisco Catalyst 9300 48-Port PoE+ Switch", description="48-Port Gigabit PoE+, 4x 10G SFP+ uplinks, Cisco DNA Layer 3 Essentials", category="Networking", unit="units")
    item_firewall = Item(name="Fortinet FortiGate 100F Enterprise Firewall", description="1 Gbps Threat Protection, 22x GE RJ45 ports, Dual Power Supplies", category="Networking", unit="units")
    item_toner = Item(name="HP LaserJet High-Yield Toner (89X Black)", description="Original HP 89X High Yield Black Toner Cartridge (10,000 page yield)", category="Office Supplies", unit="cartridges")
    item_helmet = Item(name="Industrial ANSI Safety Helmet with Face Visor", description="ANSI/ISEA Z89.1 Type 1 Class E certified, 6-point ratchet suspension with integrated flip visor", category="Safety & Facilities", unit="pieces")

    catalog_items = [item_dell, item_macbook, item_monitor, item_chair, item_desk, item_cisco, item_firewall, item_toner, item_helmet]
    db.add_all(catalog_items)
    db.commit()

    # Domain-Specific Supplier Mappings (Vendors only supply relevant items)
    item_dell.vendors.extend([v_apex, v_silicon, v_bytecraft])
    item_macbook.vendors.extend([v_silicon, v_apex])
    item_monitor.vendors.extend([v_bytecraft, v_silicon, v_apex])
    item_chair.vendors.extend([v_ergo, v_modern])
    item_desk.vendors.extend([v_modern, v_ergo])
    item_cisco.vendors.extend([v_netcore, v_prime])
    item_firewall.vendors.extend([v_prime, v_netcore])
    item_toner.vendors.extend([v_budget, v_silicon])
    item_helmet.vendors.extend([v_safeguard, v_budget])
    db.commit()

    # Inventory Quantities
    inventories = [
        Inventory(item_id=item_dell.id, available_quantity=45.0),     # Sufficient stock
        Inventory(item_id=item_macbook.id, available_quantity=4.0),   # Low stock
        Inventory(item_id=item_monitor.id, available_quantity=18.0),  # Moderate stock
        Inventory(item_id=item_chair.id, available_quantity=3.0),     # Low stock
        Inventory(item_id=item_desk.id, available_quantity=8.0),      # Moderate stock
        Inventory(item_id=item_cisco.id, available_quantity=0.0),     # Zero stock (Out of stock)
        Inventory(item_id=item_firewall.id, available_quantity=2.0),  # Low stock
        Inventory(item_id=item_toner.id, available_quantity=24.0),    # Sufficient stock
        Inventory(item_id=item_helmet.id, available_quantity=15.0)    # Moderate stock
    ]
    db.add_all(inventories)
    db.commit()

    # =========================================================================
    # 5. VENDOR PERFORMANCE, ITEM-SPECIFIC SCORING & BADGES
    # =========================================================================
    # (Vendor, Quality, Delivery, Responsiveness, Price, Fulfillment)
    vendor_metrics = [
        (v_apex, 95.0, 92.0, 90.0, 82.0, 95.0),       # High-End IT Leader
        (v_silicon, 89.0, 96.0, 94.0, 86.0, 93.0),    # Fast-Delivery IT Hardware
        (v_bytecraft, 84.0, 86.0, 88.0, 95.0, 88.0),  # Budget Developer Hardware
        (v_ergo, 96.0, 93.0, 92.0, 84.0, 96.0),       # Premium Furniture Specialist
        (v_modern, 88.0, 88.0, 86.0, 92.0, 89.0),     # Commercial Office Value
        (v_netcore, 96.0, 94.0, 92.0, 83.0, 96.0),    # Cisco Premier Networking
        (v_prime, 88.0, 95.0, 90.0, 89.0, 92.0),      # Fast Telecom & Infrastructure
        (v_budget, 82.0, 85.0, 84.0, 97.0, 86.0),     # Cost Champion for Supplies
        (v_safeguard, 96.0, 93.0, 91.0, 88.0, 95.0),  # Certified Safety Equipment
    ]

    for vendor, q, d, r, p, f in vendor_metrics:
        vp = VendorPerformance(
            vendor_id=vendor.id,
            measurement_period=now,
            quality_score=q,
            delivery_reliability_score=d,
            responsiveness_score=r,
            price_competitiveness_score=p,
            historical_fulfillment_score=f
        )
        db.add(vp)
        badges = compute_vendor_badges((q*0.25 + d*0.25 + p*0.15 + f*0.10 + r*0.05 + q*0.20), q, d, p)
        for b in badges:
            vb = VendorBadge(vendor_id=vendor.id, badge_type=b, awarded_at=now)
            db.add(vb)

    db.commit()

    # Item-Specific Calibrated Performance (Ensures DIFFERENT winners for each product)
    item_perf_records = [
        # Dell Workstation -> Apex is #1 (96), Silicon (88), ByteCraft (83)
        (v_apex, item_dell, 96.0),
        (v_silicon, item_dell, 88.0),
        (v_bytecraft, item_dell, 83.0),
        # MacBook Pro -> Silicon Edge is #1 (96), Apex (90)
        (v_silicon, item_macbook, 96.0),
        (v_apex, item_macbook, 90.0),
        # Curved Monitor -> ByteCraft is #1 (95), Silicon (88), Apex (86)
        (v_bytecraft, item_monitor, 95.0),
        (v_silicon, item_monitor, 88.0),
        (v_apex, item_monitor, 86.0),
        # Herman Miller Chair -> ErgoComfort is #1 (97), Modern Office (87)
        (v_ergo, item_chair, 97.0),
        (v_modern, item_chair, 87.0),
        # Steelcase Standing Desk -> Modern Office is #1 (94), ErgoComfort (91)
        (v_modern, item_desk, 94.0),
        (v_ergo, item_desk, 91.0),
        # Cisco Switch -> NetCore Global is #1 (97), Prime Telecom (88)
        (v_netcore, item_cisco, 97.0),
        (v_prime, item_cisco, 88.0),
        # Fortinet Firewall -> Prime Telecom is #1 (95), NetCore (90)
        (v_prime, item_firewall, 95.0),
        (v_netcore, item_firewall, 90.0),
        # HP Toner -> Budget Wholesale is #1 (97), Silicon Edge (84)
        (v_budget, item_toner, 97.0),
        (v_silicon, item_toner, 84.0),
        # Safety Helmet -> SafeGuard Industrial is #1 (97), Budget Wholesale (85)
        (v_safeguard, item_helmet, 97.0),
        (v_budget, item_helmet, 85.0)
    ]

    for v, itm, score in item_perf_records:
        vip = VendorItemPerformance(
            vendor_id=v.id,
            item_id=itm.id,
            item_specific_score=score,
            measurement_period=now
        )
        db.add(vip)

    # Historical Prices for Indicative Cost Calculation
    hist_prices = [
        (item_dell, v_apex, 2450.0, 10.0),
        (item_dell, v_silicon, 2520.0, 5.0),
        (item_dell, v_bytecraft, 2380.0, 15.0),
        (item_macbook, v_silicon, 3499.0, 4.0),
        (item_macbook, v_apex, 3550.0, 2.0),
        (item_monitor, v_bytecraft, 650.0, 10.0),
        (item_monitor, v_silicon, 680.0, 8.0),
        (item_chair, v_ergo, 1250.0, 20.0),
        (item_chair, v_modern, 1180.0, 15.0),
        (item_desk, v_modern, 860.0, 12.0),
        (item_desk, v_ergo, 890.0, 10.0),
        (item_cisco, v_netcore, 4200.0, 4.0),
        (item_cisco, v_prime, 4350.0, 2.0),
        (item_firewall, v_prime, 2800.0, 3.0),
        (item_firewall, v_netcore, 2890.0, 2.0),
        (item_toner, v_budget, 175.0, 50.0),
        (item_toner, v_silicon, 195.0, 20.0),
        (item_helmet, v_safeguard, 62.0, 100.0),
        (item_helmet, v_budget, 58.0, 50.0),
    ]

    for it, v, price, qty in hist_prices:
        hp = HistoricalPrice(item_id=it.id, vendor_id=v.id, unit_price=price, quantity=qty, recorded_at=now - timedelta(days=20))
        db.add(hp)

    db.commit()

    # =========================================================================
    # 6. DEMONSTRATION PURCHASE REQUESTS & WORKFLOW STAGES
    # =========================================================================

    # PR 1: SUBMITTED (Alex Turner -> Dell Workstation)
    pr1 = PurchaseRequest(
        reference_number="PR-2026-000101",
        requester_id=emp_alex.id,
        department_id=dept_it.id,
        selected_vendor_id=v_apex.id,
        status=PRStatus.SUBMITTED.value,
        notes="Q3 Engineering team hardware refresh (Dell Precision workstations).",
        duplicate_acknowledged=False,
        created_at=now - timedelta(hours=4)
    )
    db.add(pr1)
    db.commit()
    db.add(PurchaseRequestItem(purchase_request_id=pr1.id, item_id=item_dell.id, quantity=10.0))
    db.commit()

    # PR 2: VENDOR_SELECTION_PENDING with 2 competitive bids (Sarah Jenkins -> Herman Miller Chairs)
    # Ready for "Evaluate Bids"!
    pr2 = PurchaseRequest(
        reference_number="PR-2026-000102",
        requester_id=emp_sarah.id,
        department_id=dept_fac.id,
        selected_vendor_id=v_ergo.id,
        status=PRStatus.VENDOR_SELECTION_PENDING.value,
        notes="Ergonomic seating upgrade for 15 operational dispatch workstations.",
        duplicate_acknowledged=False,
        created_at=now - timedelta(days=2)
    )
    db.add(pr2)
    db.commit()
    db.add(PurchaseRequestItem(purchase_request_id=pr2.id, item_id=item_chair.id, quantity=15.0))
    db.commit()

    # Issue RFQs & Quotes for PR 2 from ErgoComfort ($1,220) and Modern Office ($1,160)
    rfq_ergo = RFQ(reference_number="RFQ-2026-0021", purchase_request_id=pr2.id, vendor_id=v_ergo.id, status="QUOTED", issued_at=now - timedelta(days=2))
    rfq_modern = RFQ(reference_number="RFQ-2026-0022", purchase_request_id=pr2.id, vendor_id=v_modern.id, status="QUOTED", issued_at=now - timedelta(days=2))
    db.add_all([rfq_ergo, rfq_modern])
    db.commit()

    q_ergo = Quotation(
        rfq_id=rfq_ergo.id,
        vendor_id=v_ergo.id,
        quoted_unit_price=1220.0,
        total_price=1220.0 * 15.0,
        lead_time_days=5,
        validity_period="30 Days",
        notes="Premium commercial grade Herman Miller Aeron with 12-year manufacturer warranty."
    )
    q_modern = Quotation(
        rfq_id=rfq_modern.id,
        vendor_id=v_modern.id,
        quoted_unit_price=1160.0,
        total_price=1160.0 * 15.0,
        lead_time_days=12,
        validity_period="30 Days",
        notes="Volume discounted commercial Herman Miller chairs, standard dispatch."
    )
    db.add_all([q_ergo, q_modern])
    db.commit()

    # PR 3: VENDOR_SELECTION_PENDING with 2 competitive bids (Alex Turner -> Cisco Switch)
    # Ready for "Evaluate Bids"!
    pr3 = PurchaseRequest(
        reference_number="PR-2026-000103",
        requester_id=emp_alex.id,
        department_id=dept_it.id,
        selected_vendor_id=v_netcore.id,
        status=PRStatus.VENDOR_SELECTION_PENDING.value,
        notes="Core switch replacement for datacenter server rack A.",
        duplicate_acknowledged=False,
        created_at=now - timedelta(days=3)
    )
    db.add(pr3)
    db.commit()
    db.add(PurchaseRequestItem(purchase_request_id=pr3.id, item_id=item_cisco.id, quantity=2.0))
    db.commit()

    rfq_netcore = RFQ(reference_number="RFQ-2026-0031", purchase_request_id=pr3.id, vendor_id=v_netcore.id, status="QUOTED", issued_at=now - timedelta(days=3))
    rfq_prime = RFQ(reference_number="RFQ-2026-0032", purchase_request_id=pr3.id, vendor_id=v_prime.id, status="QUOTED", issued_at=now - timedelta(days=3))
    rfq_silicon = RFQ(reference_number="RFQ-2026-0033", purchase_request_id=pr3.id, vendor_id=v_silicon.id, status="QUOTED", issued_at=now - timedelta(days=3))
    db.add_all([rfq_netcore, rfq_prime, rfq_silicon])
    db.commit()

    q_netcore = Quotation(
        rfq_id=rfq_netcore.id,
        vendor_id=v_netcore.id,
        quoted_unit_price=4150.0,
        total_price=4150.0 * 2.0,
        lead_time_days=4,
        validity_period="45 Days",
        notes="Cisco Authorized Premier Partner with next-business-day SMARTnet warranty."
    )
    q_prime = Quotation(
        rfq_id=rfq_prime.id,
        vendor_id=v_prime.id,
        quoted_unit_price=4280.0,
        total_price=4280.0 * 2.0,
        lead_time_days=2,
        validity_period="30 Days",
        notes="In-stock expedited express shipping."
    )
    q_silicon = Quotation(
        rfq_id=rfq_silicon.id,
        vendor_id=v_silicon.id,
        quoted_unit_price=4450.0,
        total_price=4450.0 * 2.0,
        lead_time_days=1,
        validity_period="15 Days",
        notes="Same-day expedited critical courier dispatch."
    )
    db.add_all([q_netcore, q_prime, q_silicon])
    db.commit()

    # PR 4: PO_GENERATED (Sarah Jenkins -> HP Toner -> Budget Wholesale Corp)
    pr4 = PurchaseRequest(
        reference_number="PR-2026-000104",
        requester_id=emp_sarah.id,
        department_id=dept_ops.id,
        selected_vendor_id=v_budget.id,
        status=PRStatus.PO_GENERATED.value,
        notes="Monthly operations printer consumables replenishment.",
        duplicate_acknowledged=False,
        created_at=now - timedelta(days=5)
    )
    db.add(pr4)
    db.commit()
    db.add(PurchaseRequestItem(purchase_request_id=pr4.id, item_id=item_toner.id, quantity=20.0))
    db.commit()

    # Create RFQ and Quotation for PR 4
    rfq_toner = RFQ(reference_number="RFQ-2026-0041", purchase_request_id=pr4.id, vendor_id=v_budget.id, status="QUOTED", issued_at=now - timedelta(days=5))
    db.add(rfq_toner)
    db.commit()

    q_toner = Quotation(
        rfq_id=rfq_toner.id,
        vendor_id=v_budget.id,
        quoted_unit_price=175.0,
        total_price=3500.0,
        lead_time_days=3,
        validity_period="30 Days",
        notes="Standard contract delivery terms."
    )
    db.add(q_toner)
    db.commit()

    # Create PO for PR 4
    po4_num = f"PO-{now.year}-4410D44D"
    from app.services.po_service import generate_po_pdf
    po4_pdf = generate_po_pdf(
        po_number=po4_num,
        pr_ref=pr4.reference_number,
        vendor_name=v_budget.name,
        vendor_email=v_budget.email,
        item_name=item_toner.name,
        quantity=20.0,
        unit=item_toner.unit,
        unit_price=175.0,
        total_amount=3500.0,
        lead_time_days=3,
        supervisor_name=sup_ops.name,
        generated_at=now - timedelta(days=4)
    )
    po4 = PurchaseOrder(
        po_number=po4_num,
        purchase_request_id=pr4.id,
        vendor_id=v_budget.id,
        quotation_id=q_toner.id,
        approved_amount=3500.0,
        pdf_path=po4_pdf,
        status="GENERATED",
        generated_at=now - timedelta(days=4)
    )
    db.add(po4)
    db.commit()

    # PR 5: COMPLETED (Alex Turner -> Apple MacBook Pro -> Silicon Edge Systems)
    pr5 = PurchaseRequest(
        reference_number="PR-2026-000088",
        requester_id=emp_alex.id,
        department_id=dept_it.id,
        selected_vendor_id=v_silicon.id,
        status=PRStatus.COMPLETED.value,
        notes="Leadership engineering laptops.",
        duplicate_acknowledged=False,
        created_at=now - timedelta(days=45)
    )
    db.add(pr5)
    db.commit()
    db.add(PurchaseRequestItem(purchase_request_id=pr5.id, item_id=item_macbook.id, quantity=3.0))
    db.commit()

    # =========================================================================
    # 7. KNOWLEDGE BASE DOCUMENTS (Policy RAG)
    # =========================================================================
    policy_doc = (
        "ENTERPRISE PROCUREMENT POLICY AND THRESHOLD GOVERNANCE\n\n"
        "Section 1: Approval Matrix\n"
        "1.1 Purchases under $5,000 require Department Supervisor approval.\n"
        "1.2 Purchases between $5,000 and $50,000 require multi-vendor RFQ bidding with at least two qualified quotations.\n"
        "1.3 Purchases exceeding $50,000 require Finance Director review.\n\n"
        "Section 2: Vendor Selection Guidelines\n"
        "2.1 The lowest quote is not automatically awarded. Evaluators must balance unit cost (40%), lead time (20%), delivery reliability (20%), and vendor quality (20%).\n"
        "2.2 If an evaluator overrides the system-recommended vendor, a mandatory documented business rationale must be entered.\n"
        "2.3 High-reliability vendors with certified quality badges should be favored for mission-critical IT infrastructure.\n\n"
        "Section 3: Purchase Orders and Payment Terms\n"
        "3.1 No procurement commitments may be made without an officially generated Purchase Order (PO).\n"
        "3.2 PO generation is idempotent and requires prerequisite supervisor final approval.\n"
        "3.3 Net 30 payment terms apply to all certified vendor fulfillment orders."
    )
    ingest_document(db, title="Corporate Procurement Policy 2026", filename="procurement_policy_2026.txt", content=policy_doc)

    vendor_code = (
        "SUPPLIER CODE OF CONDUCT AND ON-TIME PERFORMANCE STANDARDS\n\n"
        "Section 1: Supplier Compliance\n"
        "1.1 Suppliers must maintain an on-time delivery reliability score of at least 85% to retain Preferred status.\n"
        "1.2 Defect rates exceeding 3% will result in a Needs Attention badge and mandatory performance review.\n"
        "1.3 Invoices must match PO line items and unit rates exactly."
    )
    ingest_document(db, title="Supplier Code of Conduct", filename="supplier_code_of_conduct.txt", content=vendor_code)

    # =========================================================================
    # 8. VENDOR REVIEWS (RAG + LLM Recommendation Engine Data)
    # =========================================================================
    print("Ingesting vendor review data for RAG recommendation engine...")
    try:
        from app.services.ingest_vendor_reviews import ingest_vendor_reviews
        from app.ai.provider import get_llm_provider
        llm = get_llm_provider()
        n = ingest_vendor_reviews(db, llm_provider=llm)
        print(f"Vendor reviews ingested: {n} new records with embeddings.")
    except Exception as e:
        print(f"Warning: Vendor review ingestion failed: {e}. System will use analytical fallback for recommendations.")

    print("Database seeded successfully with authentic, multi-vendor enterprise data!")

