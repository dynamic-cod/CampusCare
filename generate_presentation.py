#!/usr/bin/env python3
"""
CampusCare Academic Presentation Generator
Generates a 16:9 widescreen, professionally styled PowerPoint presentation
tailored for academic evaluation and viva defense before university professors.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# --- Color Palette Definitions ---
NAVY_DARK = RGBColor(15, 28, 54)        # Deep Navy for headers & title slides
NAVY_LIGHT = RGBColor(27, 46, 82)       # Lighter Navy for accents
TEAL_ACCENT = RGBColor(13, 148, 136)    # Modern Emerald/Teal for key highlights
BLUE_ACCENT = RGBColor(37, 99, 235)     # Royal Blue
AMBER_ACCENT = RGBColor(217, 119, 6)    # Amber/Orange for warnings & anti-fraud
RED_ACCENT = RGBColor(220, 38, 38)      # Red for dispute/penalty
GREEN_ACCENT = RGBColor(16, 185, 129)   # Green for resolution/verification
SLATE_BG = RGBColor(248, 250, 252)      # Soft off-white background
CARD_BG = RGBColor(255, 255, 255)       # Pure white card background
CARD_BORDER = RGBColor(226, 232, 240)   # Subtle slate border
TEXT_DARK = RGBColor(30, 41, 59)        # Charcoal Slate 800
TEXT_MUTED = RGBColor(100, 116, 139)    # Slate 500
WHITE = RGBColor(255, 255, 255)

FONT_HEADING = "Segoe UI"
FONT_BODY = "Segoe UI"

def set_slide_background(slide, color):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    return bg

def add_header(slide, category_text, title_text, slide_num, total_slides=15):
    # Category tag / Pill
    cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(8), Inches(0.35))
    tf_c = cat_box.text_frame
    tf_c.word_wrap = True
    p_c = tf_c.paragraphs[0]
    p_c.text = category_text.upper()
    p_c.font.name = FONT_HEADING
    p_c.font.size = Pt(10)
    p_c.font.bold = True
    p_c.font.color.rgb = TEAL_ACCENT

    # Title
    title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.7), Inches(10.5), Inches(0.6))
    tf_t = title_box.text_frame
    tf_t.word_wrap = True
    p_t = tf_t.paragraphs[0]
    p_t.text = title_text
    p_t.font.name = FONT_HEADING
    p_t.font.size = Pt(22)
    p_t.font.bold = True
    p_t.font.color.rgb = NAVY_DARK

    # Subtle divider rule
    divider = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.35), Inches(11.733), Inches(0.02))
    divider.fill.solid()
    divider.fill.fore_color.rgb = CARD_BORDER
    divider.line.fill.background()

    # Footer
    footer_box = slide.shapes.add_textbox(Inches(0.8), Inches(7.1), Inches(10), Inches(0.3))
    tf_f = footer_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = "CampusCare — University Facility Maintenance & Operations Platform | Aligarh Muslim University (AMU)"
    p_f.font.name = FONT_BODY
    p_f.font.size = Pt(9)
    p_f.font.color.rgb = TEXT_MUTED

    num_box = slide.shapes.add_textbox(Inches(11.5), Inches(7.1), Inches(1.0), Inches(0.3))
    tf_n = num_box.text_frame
    p_n = tf_n.paragraphs[0]
    p_n.text = f"{slide_num} / {total_slides}"
    p_n.alignment = PP_ALIGN.RIGHT
    p_n.font.name = FONT_BODY
    p_n.font.size = Pt(9)
    p_n.font.bold = True
    p_n.font.color.rgb = TEXT_MUTED

def add_card(slide, left, top, width, height, title, items, header_color=None, border_color=None):
    # Outer card shape
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    card.fill.solid()
    card.fill.fore_color.rgb = CARD_BG
    card.line.color.rgb = border_color if border_color else CARD_BORDER
    card.line.width = Pt(1.2)

    # Title Banner inside card if header_color
    title_height = 0.5
    if header_color:
        top_bar = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(title_height))
        top_bar.fill.solid()
        top_bar.fill.fore_color.rgb = header_color
        top_bar.line.fill.background()

    tb = slide.shapes.add_textbox(Inches(left + 0.15), Inches(top + 0.08), Inches(width - 0.3), Inches(title_height))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.name = FONT_HEADING
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = WHITE if header_color else NAVY_DARK

    # Content list
    cb = slide.shapes.add_textbox(Inches(left + 0.18), Inches(top + title_height + 0.05), Inches(width - 0.36), Inches(height - title_height - 0.15))
    ctf = cb.text_frame
    ctf.word_wrap = True

    for i, item in enumerate(items):
        cp = ctf.add_paragraph() if i > 0 else ctf.paragraphs[0]
        cp.space_after = Pt(6)
        
        # Check if item has a bold lead-in like "Lead: Content"
        if ": " in item:
            lead, rest = item.split(": ", 1)
            r1 = cp.add_run()
            r1.text = "• " + lead + ": "
            r1.font.bold = True
            r1.font.size = Pt(11)
            r1.font.name = FONT_BODY
            r1.font.color.rgb = TEXT_DARK
            
            r2 = cp.add_run()
            r2.text = rest
            r2.font.bold = False
            r2.font.size = Pt(11)
            r2.font.name = FONT_BODY
            r2.font.color.rgb = TEXT_DARK
        else:
            r = cp.add_run()
            r.text = "• " + item
            r.font.size = Pt(11)
            r.font.name = FONT_BODY
            r.font.color.rgb = TEXT_DARK

def add_stat_box(slide, left, top, width, height, stat_value, stat_label, color=TEAL_ACCENT):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
    box.fill.solid()
    box.fill.fore_color.rgb = WHITE
    box.line.color.rgb = CARD_BORDER
    box.line.width = Pt(1)

    tb = slide.shapes.add_textbox(Inches(left), Inches(top + 0.08), Inches(width), Inches(height * 0.55))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.text = str(stat_value)
    p.font.name = FONT_HEADING
    p.font.size = Pt(22)
    p.font.bold = True
    p.font.color.rgb = color

    lb = slide.shapes.add_textbox(Inches(left + 0.05), Inches(top + height * 0.52), Inches(width - 0.1), Inches(height * 0.45))
    ltf = lb.text_frame
    ltf.word_wrap = True
    lp = ltf.paragraphs[0]
    lp.alignment = PP_ALIGN.CENTER
    lp.text = stat_label
    lp.font.name = FONT_BODY
    lp.font.size = Pt(9.5)
    lp.font.bold = True
    lp.font.color.rgb = TEXT_MUTED

def set_notes(slide, notes_text):
    notes_slide = slide.notes_slide
    tf = notes_slide.notes_text_frame
    tf.text = notes_text.strip()


def build_presentation(output_path="CampusCare_Project_Presentation.pptx"):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Navy Executive & Academic)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_background(s1, NAVY_DARK)

    # Accent decorative bar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.1), Inches(1.5), Inches(0.08))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL_ACCENT
    bar.line.fill.background()

    # Category Pill
    pill = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(3.6), Inches(0.35))
    pill.fill.solid()
    pill.fill.fore_color.rgb = NAVY_LIGHT
    pill.line.color.rgb = TEAL_ACCENT
    pill_tf = pill.text_frame
    pp = pill_tf.paragraphs[0]
    pp.alignment = PP_ALIGN.CENTER
    pp.text = "ACADEMIC PROJECT DEFENSE • 2026"
    pp.font.name = FONT_HEADING
    pp.font.size = Pt(9.5)
    pp.font.bold = True
    pp.font.color.rgb = TEAL_ACCENT

    # Main Title
    tbox = s1.shapes.add_textbox(Inches(0.8), Inches(1.85), Inches(11.5), Inches(1.3))
    ttf = tbox.text_frame
    ttf.word_wrap = True
    tp = ttf.paragraphs[0]
    tp.text = "CampusCare"
    tp.font.name = FONT_HEADING
    tp.font.size = Pt(48)
    tp.font.bold = True
    tp.font.color.rgb = WHITE

    # Subtitle
    sub_box = s1.shapes.add_textbox(Inches(0.8), Inches(3.1), Inches(11.5), Inches(0.8))
    stf = sub_box.text_frame
    stf.word_wrap = True
    sp = stf.paragraphs[0]
    sp.text = "Enterprise Facility Maintenance & Automated Operations Platform for Large-Scale Collegiate Campuses"
    sp.font.name = FONT_BODY
    sp.font.size = Pt(18)
    sp.font.color.rgb = RGBColor(203, 213, 225)

    # Context Details Box (3 Cards in Navy)
    features = [
        ("Institutional Reference", "Aligarh Muslim University (AMU)\n20 Halls • 84 Hostels • 157 Staff"),
        ("Architectural Pillars", "AI Spatial Triage • Anti-Fraud Dwell Timer\nZero-Login Tracking • Row-Level RBAC"),
        ("Engineering Baseline", "Django 4.2+ • Python 3.9+ • IEEE 830\n100% Passed Test Suite (5 Pillars)")
    ]
    for idx, (head, body) in enumerate(features):
        c_left = 0.8 + idx * 4.0
        c_box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(c_left), Inches(4.2), Inches(3.7), Inches(1.5))
        c_box.fill.solid()
        c_box.fill.fore_color.rgb = NAVY_LIGHT
        c_box.line.color.rgb = RGBColor(51, 65, 85)
        c_tf = c_box.text_frame
        c_tf.word_wrap = True
        
        hp = c_tf.paragraphs[0]
        hp.text = head.upper()
        hp.font.name = FONT_HEADING
        hp.font.size = Pt(10)
        hp.font.bold = True
        hp.font.color.rgb = TEAL_ACCENT
        
        bp = c_tf.add_paragraph()
        bp.text = body
        bp.font.name = FONT_BODY
        bp.font.size = Pt(11)
        bp.font.color.rgb = RGBColor(241, 245, 249)

    # Presenter Information Footer
    info_box = s1.shapes.add_textbox(Inches(0.8), Inches(6.1), Inches(11.5), Inches(0.8))
    itf = info_box.text_frame
    ip = itf.paragraphs[0]
    ip.text = "Presenter: Project Development Team   |   Supervisor: Faculty Evaluator   |   Department of Computer Science"
    ip.font.name = FONT_BODY
    ip.font.size = Pt(11.5)
    ip.font.color.rgb = RGBColor(148, 163, 184)

    set_notes(s1, """
Good morning, respected Professor and evaluation panel.
Today, I am proud to present CampusCare, an enterprise-grade facility maintenance and operations platform specifically engineered for large-scale collegiate institutions, modeled upon the structural and administrative reality of Aligarh Muslim University.

In this presentation, I will walk you through the real-world operational challenges of managing facility operations across thousands of hostel rooms, our automated algorithmic triage and dispatch systems, our novel anti-fraud timing engine, and how our row-level multi-tenant architecture ensures strict institutional data segregation.
""")

    # =========================================================================
    # SLIDE 2: Problem Statement & Motivation
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_background(s2, SLATE_BG)
    add_header(s2, "Context & Motivation", "The Facility Crisis in Large Collegiate Campuses", 2)

    # Stat callouts along top
    add_stat_box(s2, 0.8, 1.55, 2.7, 1.1, "20", "Residential Halls (AMU)")
    add_stat_box(s2, 3.8, 1.55, 2.7, 1.1, "84", "Constituent Hostels")
    add_stat_box(s2, 6.8, 1.55, 2.7, 1.1, "30,000+", "Active Resident Students")
    add_stat_box(s2, 9.8, 1.55, 2.7, 1.1, "157", "Maintenance Technicians")

    # Three core pain points
    add_card(s2, 0.8, 2.85, 3.7, 4.0, "1. Legacy Paper Registers", [
        "Fragmented Physical Logs: Complaints logged on physical registers at hall gates are routinely lost, delayed, or unreadable.",
        "Zero Real-Time Tracking: Students have no visibility into ticket status, technician assignment, or expected turnaround times.",
        "Accountability Black Hole: No verifiable audit trail of who inspected the fault, when work commenced, or what materials were used."
    ], header_color=NAVY_DARK)

    add_card(s2, 4.8, 2.85, 3.7, 4.0, "2. The 'Ghost Closure' Fraud", [
        "Unverified Remote Closures: Technicians frequently mark complaints 'Resolved' remotely from maintenance offices without ever visiting the site.",
        "Premature Sign-Offs: Students return from lectures to find broken electrical outlets or plumbing leaks still completely unresolved.",
        "No Verification Gate: Legacy software allows technicians to unilaterally change state to 'Closed' without student confirmation."
    ], header_color=AMBER_ACCENT)

    add_card(s2, 8.8, 2.85, 3.7, 4.0, "3. Administrative Silos", [
        "Uncoordinated Routing: Complaints submitted to Provosts must be manually passed to Estate/Electricity departments via phone calls or memos.",
        "Cross-Tenant Data Leaks: Traditional apps lack row-level scoping; a Provost can see confidential data of another hall.",
        "Student Reporting Friction: Mandatory account creation discourages students from reporting minor infrastructure faults until severe damage occurs."
    ], header_color=NAVY_DARK)

    set_notes(s2, """
To understand why CampusCare is necessary, we must examine the operational scale of an institution like AMU. With over 20 Residential Halls, 84 constituent hostels, and more than 30,000 resident students, facility management has historically collapsed under three critical bottlenecks:

First, manual paper logbooks. When a student reports a fused corridor light or leaking washroom, the complaint is handwritten in a physical register at the dining or provost office. The paper trail is sluggish and frequently lost.

Second, what we define as the "Ghost Closure" problem. In existing computerized systems, a technician can receive a ticket and immediately mark it as 'Resolved' while sitting in their workshop, without physically setting foot in the hostel room.

Third, the administrative barrier. Students are reluctant to sign up for yet another account with passwords, and university administrators—Provosts and Heads of Departments—lack scoped, row-level visibility into their specific jurisdictions.
""")

    # =========================================================================
    # SLIDE 3: Project Vision & Core Innovations
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_background(s3, SLATE_BG)
    add_header(s3, "Project Objectives", "Architectural Goals & Key Engineering Innovations", 3)

    add_card(s3, 0.8, 1.55, 5.7, 2.55, "1. Frictionless Zero-Login Student Flow", [
        "Friction-Free Submission: Students file complaints in under 60 seconds using only their University Enrollment Number (e.g. 'AB1234').",
        "Cryptographic 32-Char Token: System issues a secure hexadecimal UUID token (`/track/<token>/`) providing private, real-time ticket tracking.",
        "Privacy by Design: Eliminates credential fatigue while ensuring verifiable institutional authenticity."
    ], header_color=TEAL_ACCENT)

    add_card(s3, 6.8, 1.55, 5.7, 2.55, "2. Spatial Hierarchy & AI Triage", [
        "Recursive Campus Hierarchy: Fully normalized relational tree (Campus → Hall → Hostel → Floor → Room) reflecting real AMU geography.",
        "NLP Category Prediction: Heuristic & NLP categorization auto-tags trades (Electrical, Estate Plumbing, Sanitation, Civil).",
        "Explainable Urgency Scoring: Rule-based prioritization calculates SLA deadlines (Urgent: 2h, High: 6h, Normal: 24h, Low: 72h)."
    ], header_color=NAVY_DARK)

    add_card(s3, 0.8, 4.3, 5.7, 2.55, "3. Anti-Fraud Dwell Timer & Camera Proof", [
        "Mandatory 5-Min Physical Dwell Timer: Server enforces minimum 5-minute elapsed duration between 'In Progress' and 'Resolved'.",
        "Mandatory In-Memory Photo Proof: Technicians must capture and submit photographic evidence of completed repair.",
        "Closure Protection: Technicians CANNOT close complaints; only students can verify resolution and authorize ticket closure."
    ], header_color=AMBER_ACCENT)

    add_card(s3, 6.8, 4.3, 5.7, 2.55, "4. Multi-Tenant RBAC & Auto-Purge", [
        "Row-Level Query Scoping: Custom permission architecture enforces strict data isolation for Registrar, Provost, and HOD consoles.",
        "Autonomous Load-Balanced Dispatch: Roster engine assigns on-duty technicians by trade, hall proximity, and current queue load.",
        "Automated Media Purge: Upon verified closure, `complaint.purge_attached_media()` permanently unlinks disk files to preserve storage."
    ], header_color=BLUE_ACCENT)

    set_notes(s3, """
To address these challenges, CampusCare was architected around four engineering pillars:

1. A Zero-Login Student Architecture: Instead of forcing students through cumbersome registration flows, they authenticate using their AMU Enrollment Number. The system generates an unguessable 32-character tracking token granting direct access to their ticket.

2. A Hierarchical Spatial Model with AI Triage: The physical campus is modeled down to individual rooms. An NLP engine parses the complaint description to determine the trade department and calculate SLA deadlines.

3. The Anti-Fraud Dwell Timer: This is our most significant operational innovation. A technician cannot flip a task from 'In Progress' to 'Resolved' in under 5 minutes. They must also upload photo proof, and only the student holds the authority to permanently close the complaint.

4. Multi-Tenant Row-Level Security: Provosts see only their assigned halls and constituent hostels. HODs see only their technical trade. The Registrar retains global university oversight.
""")

    # =========================================================================
    # SLIDE 4: High-Level System Architecture
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_background(s4, SLATE_BG)
    add_header(s4, "System Architecture", "Multi-Tiered Architectural Blueprint & Tech Stack", 4)

    # Check if Architecture.png exists, insert if found
    arch_img = "diagrams/Architecture.png"
    if os.path.exists(arch_img):
        img_left = Inches(0.8)
        img_top = Inches(1.55)
        img_width = Inches(7.2)
        s4.shapes.add_picture(arch_img, img_left, img_top, width=img_width)
        card_left = 8.3
        card_width = 4.2
    else:
        card_left = 0.8
        card_width = 11.7

    add_card(s4, card_left, 1.55, card_width, 5.3, "Technology Stack & Layers", [
        "Presentation Layer: Responsive HTML5/CSS3/Vanilla JS PWA interface. No heavy JS frameworks required; ultra-fast load time on low-bandwidth campus 4G/Wi-Fi.",
        "Application Layer: Python 3.9+ & Django 4.2+ leveraging MTV architecture, ORM query optimization, and transaction-safe signals.",
        "AI Triage & Matcher Engine: Heuristic NLP extraction (`smart.py`, `ai_triage.py`), priority scoring rules, and load-balanced technician matcher (`dispatcher.py`).",
        "Security & Anti-Fraud Engine: CSRF protection, UUID token access gates, timing delta validators, and in-memory Pillow image compression.",
        "Persistence Layer: Relational SQLite/PostgreSQL with multi-level indexing on spatial relations, foreign keys, and complaint statuses.",
        "Storage Optimization: Whitenoise static streaming with automated media purging upon student verified closure."
    ], header_color=NAVY_DARK)

    set_notes(s4, """
Slide 4 illustrates our High-Level System Architecture and Technology Stack.
As shown in the architecture diagram on the left:
- The presentation tier is built with responsive HTML5, modern CSS, and lightweight JavaScript, functioning as a mobile-optimized Progressive Web Application. This ensures students and technicians can interact effortlessly even over spotty 4G connections in hostel basements.
- The core backend is powered by Python and Django 4.2. We chose Django for its rock-solid security defaults, built-in ORM, and battle-tested session management.
- Within the application layer sits our AI Triage Engine, the Automated Staff Matcher, and the Anti-Fraud Timing Validator.
- In the persistence layer, the database maintains strict foreign-key integrity across our spatial models and audit history logs. Pillow handles image compression entirely in memory before disk write, preventing server resource exhaustion.
""")

    # =========================================================================
    # SLIDE 5: Spatial Hierarchy & AMU Campus Modeling
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_background(s5, SLATE_BG)
    add_header(s5, "Data Modeling", "Multi-Tier Campus Spatial Hierarchy & Room Binding", 5)

    add_card(s5, 0.8, 1.55, 3.7, 5.3, "Recursive Spatial Modeling", [
        "Self-Referencing Building Tree: Modeled via `Building.parent` foreign key. Distinguishes parent Residential Halls from child Constituent Hostels.",
        "Constituent Hostels Example: Sir Syed Hall North encompasses 8 child hostels (e.g., Sir Syed North Hostel, Mumtaz, etc.).",
        "Granular Floor & Room Mapping: Normalized `Floor` and `Room` tables store room capacity, wing details, and active maintenance flags.",
        "GPS Coordinates: Latitude and longitude stored per building for proximity-based technician assignment."
    ], header_color=NAVY_DARK)

    add_card(s5, 4.8, 1.55, 3.7, 5.3, "Dynamic Room Resolution Engine", [
        "Real-Time Room Lookup: Dynamic endpoint `/api/room-lookup/` auto-resolves matching rooms, halls, and hostels as students type.",
        "QR Code Token Binding: Every physical room is assigned a unique `qr_code_token`. Scanning instantly locks the complaint form to that exact room.",
        "Fuzzy Alias Resolution: Handles common student abbreviations (e.g., 'SSN', 'V.M. Hall', 'CS Dept', 'Lab 3').",
        "Zero GPS Drift: Avoids inaccurate mobile GPS fixes inside multi-story concrete hostel blocks."
    ], header_color=TEAL_ACCENT)

    add_card(s5, 8.8, 1.55, 3.7, 5.3, "AMU Scale Dataset Ingestion", [
        "20 Residential Halls: Complete coverage of all male and female residential halls of AMU.",
        "84 Constituent Hostels: Full hierarchy synced via idempotent database synchronization scripts.",
        "13 Academic Faculties: Complete mapping of Arts, Science, Engineering, Medicine, Commerce, Law, etc.",
        "40+ Teaching Departments & Central Facilities: Computer Science, Estate Office, Electricity Department, Water Works."
    ], header_color=NAVY_DARK)

    set_notes(s5, """
In Slide 5, we present how CampusCare represents physical campus geography.
One of the most complex challenges in universities like AMU is the hostel structure. A residential hall is not just a single building; it is a federation of constituent hostels. For instance, Sir Syed Hall North contains 8 distinct hostels, each with multiple wings, floors, and rooms.

To represent this without database duplication, we engineered a self-referential Building model with a recursive parent relationship. This allows queries to roll up naturally: complaints submitted for any constituent hostel automatically belong to the parent Hall Provost's administrative purview.

Furthermore, we implemented QR Code tokens per room and dynamic room lookups via an API endpoint. When a student scans the QR sticker on their room door, the spatial hierarchy binds instantly, eliminating errors in location reporting.
""")

    # =========================================================================
    # SLIDE 6: AI Spatial Triage & Autonomous Dispatcher
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_background(s6, SLATE_BG)
    add_header(s6, "AI & Operations", "AI Spatial Triage & Autonomous Technician Dispatching", 6)

    add_card(s6, 0.8, 1.55, 5.7, 5.3, "AI Triage & NLP Urgency Classifier", [
        "Automated Trade Extraction (`smart.py`): Parses raw complaint text to identify target trade (e.g. 'sparking socket' → Electrical, 'leaking faucet' → Estate Plumbing).",
        "Keyword & Semantic Matching: Evaluates severity keywords ('fire', 'water overflow', 'short circuit', 'ceiling crack') to compute `priority_score` (0-100).",
        "Dynamic SLA Assignment: Automatically enforces strict service deadlines based on computed urgency:",
        "  • Urgent (Score 80-100): SLA = 2 Hours (Immediate hazard)",
        "  • High (Score 60-79): SLA = 6 Hours (Essential amenity failure)",
        "  • Normal (Score 30-59): SLA = 24 Hours (Standard maintenance)",
        "  • Low (Score 0-29): SLA = 72 Hours (Minor cosmetic defect)",
        "Explainable Priority Reason: Generates clear audit explanations stored in `complaint.priority_reason` for administrative review."
    ], header_color=NAVY_DARK)

    add_card(s6, 6.8, 1.55, 5.7, 5.3, "Autonomous Technician Dispatch Engine", [
        "Directory of 157 AMU Technicians: Pre-ingested maintenance staff dataset across Electrical, Civil, Plumbing, and Sanitation trades.",
        "Multi-Factor Matching Algorithm (`dispatcher.py`, `staff_matcher.py`):",
        "  1. Trade Competence: Matches technician's certified trade to the complaint category.",
        "  2. Spatial Proximity: Filters technicians stationed at or assigned to the relevant Hall or Department.",
        "  3. Active Load Balancing: Selects the least-loaded technician (minimum count of open/in-progress tasks) to prevent burnout and queue starvation.",
        "Instant Tokenized Task Generation: Generates a secure `staff_task_token` and routes the ticket directly to the technician's mobile portal.",
        "Autonomous Fallback: If no local technician is available, gracefully falls back to department-wide roster with audit logging."
    ], header_color=TEAL_ACCENT)

    set_notes(s6, """
Slide 6 highlights our algorithmic core: AI Spatial Triage and Autonomous Dispatch.
When a student submits a complaint, our NLP pipeline in `smart.py` extracts contextual keywords and predicts the appropriate maintenance trade. Simultaneously, it computes an explainable priority score. A leaking water pipe or an electrical short circuit triggers an 'Urgent' classification with a strict 2-hour SLA.

Next, the Dispatcher takes over. Rather than waiting for a clerk to review the ticket, the system queries our 157-person technician database. It filters for technicians certified in that trade, prioritizes those geographically stationed at that specific residential hall, and selects the least-loaded individual based on active task counts. The ticket is immediately dispatched, complete with a direct tokenized task link.
""")

    # =========================================================================
    # SLIDE 7: Anti-Fraud Dwell Timer & Technician Lifecycle
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_background(s7, SLATE_BG)
    add_header(s7, "Anti-Fraud Architecture", "Anti-Fraud Dwell Timing & Zero-Login Task Execution", 7)

    # Check if State_machine.png exists
    sm_img = "diagrams/State_machine.png"
    if os.path.exists(sm_img):
        s7.shapes.add_picture(sm_img, Inches(0.8), Inches(1.55), width=Inches(4.8))
        c_left = 5.9
        c_width = 6.6
    else:
        c_left = 0.8
        c_width = 11.7

    add_card(s7, c_left, 1.55, c_width, 5.3, "Solving the 'Ghost Closure' Problem", [
        "Zero-Login Technician Portal: Technicians access their assigned task directly via a cryptographically secure URL: `/task/<uuid:staff_task_token>/`. No forgotten passwords or login barriers.",
        "Step 1 — Mark In Progress: Technician arrives on site and taps 'Start Work'. The server records an immutable UTC timestamp in `started_at`.",
        "Step 2 — Mandatory 5-Minute Dwell Timer: The server strictly rejects any resolution attempt if `current_time - started_at < 5 minutes`. Eliminates fraudulent instant remote closures from technicians' living quarters.",
        "Step 3 — Mandatory Photographic Proof: Resolution requires an uploaded photograph of the repaired item. Pillow compresses images in memory to under 500KB before disk storage.",
        "Step 4 — State Transition to 'Resolved': The task enters `resolved` status—NOT 'closed'.",
        "Crucial Rule: Technicians DO NOT have permission to close tickets. Only the reporting student can verify and authorize final closure."
    ], header_color=AMBER_ACCENT)

    set_notes(s7, """
Slide 7 addresses our novel Anti-Fraud Architecture.
The single greatest complaint in collegiate maintenance is technicians claiming they fixed a problem when they never visited the site. We solved this with a strict state-machine contract:

First, technicians have zero-login access via a secure UUID link sent to their phone.
When they arrive at the room, they tap 'Start Work'. This initiates the task and timestamps it in the database.
Here is the anti-fraud mechanism: Our backend enforces an immutable 5-minute dwell timer. If a technician attempts to mark the task as resolved in under 5 minutes, the server returns an HTTP 400 rejection with an exact countdown of remaining minutes.
Additionally, the technician must upload a real-time photograph of the completed repair.
Most importantly: A technician CANNOT close a ticket. They can only transition it to 'Resolved', awaiting student verification.
""")

    # =========================================================================
    # SLIDE 8: Closed-Loop Student Verification & Media Purge
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_background(s8, SLATE_BG)
    add_header(s8, "Verification & Governance", "Closed-Loop Student Verification & Automated Privacy Purge", 8)

    add_card(s8, 0.8, 1.55, 5.7, 5.3, "Student Verification & Rating Workflow", [
        "Private Tracking Portal: Students visit `/track/<str:tracking_token>/` without login to inspect live progress, assigned technician name, and uploaded resolution photos.",
        "Option A: Confirm Closure & Rate (Happy Path):",
        "  • Student confirms the defect is genuinely repaired.",
        "  • Submits 1 to 5 star rating and optional comments.",
        "  • Complaint transitions to final state: `closed`.",
        "Automated Media Purge (`complaint.purge_attached_media()`):",
        "  • As soon as the student verifies closure, all uploaded photos (initial defect + technician resolution) are permanently deleted from server storage.",
        "  • Protects student privacy (photos taken inside hostel rooms).",
        "  • Prevents server disk bloat across tens of thousands of annual tickets."
    ], header_color=GREEN_ACCENT)

    add_card(s8, 6.8, 1.55, 5.7, 5.3, "Dispute & Technician Accountability Engine", [
        "Option B: Dispute Resolution (Fraud Defense):",
        "  • If the fault persists or was falsely reported as resolved, the student taps 'Dispute & Reopen'.",
        "  • Mandatory Dispute Evidence: Student must provide a detailed explanation (≥ 10 chars) and fresh photo proof of the continuing fault.",
        "Automated Escalation Protocol:",
        "  • Status immediately reverts to `in_progress`.",
        "  • Priority is automatically escalated to `Urgent` (`priority_score = 95`).",
        "  • High-visibility escalation flag alerted on Provost & HOD dashboards.",
        "Technician Accountability Penalty:",
        "  • The assigned technician receives an immediate -15 point penalty deducted from their `accountability_score`.",
        "  • Scores below 70 trigger automated administrative review by the Registrar."
    ], header_color=RED_ACCENT)

    set_notes(s8, """
Slide 8 demonstrates the Closed-Loop Verification system.
Once the technician marks a task resolved, control returns entirely to the student:

If the repair is satisfactory, the student confirms closure and submits a star rating. At this exact moment, an automated garbage collection routine executes: `complaint.purge_attached_media()`. This permanently deletes all uploaded photographs from server storage. This serves two vital purposes: it prevents multi-gigabyte disk bloat on the server, and it protects student privacy since photos are taken inside personal living quarters.

However, if the technician did poor work or lied, the student initiates a Dispute. The student must attach photo proof and a written explanation. Upon submission, the complaint automatically escalates to 'Urgent' priority with a score of 95, and the technician suffers an automatic 15-point penalty on their institutional accountability score.
""")

    # =========================================================================
    # SLIDE 9: Multi-Tenant Role-Based Access Control (RBAC)
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    set_slide_background(s9, SLATE_BG)
    add_header(s9, "Security & Scoping", "Multi-Tenant Row-Level RBAC & Administrative Isolation", 9)

    # Check if RBAC.png exists
    rbac_img = "diagrams/RBAC.png"
    if os.path.exists(rbac_img):
        s9.shapes.add_picture(rbac_img, Inches(0.8), Inches(1.55), width=Inches(6.0))
        c_left = 7.1
        c_width = 5.4
    else:
        c_left = 0.8
        c_width = 11.7

    add_card(s9, c_left, 1.55, c_width, 5.3, "Zero-Data-Leak Scoping Matrix", [
        "Registrar Global Console (Super-Tenant):",
        "  • University-wide operational oversight across all 20 halls and all academic departments.",
        "  • Macro analytics: SLA breach rates, technician performance rankings, recurring infrastructure hotspots.",
        "Provost Console (Residential Hall Tenant):",
        "  • Strictly scoped to assigned Residential Hall and all its child constituent hostels (e.g., Sir Syed North + 8 hostels).",
        "  • Row-level filtering via `permissions.py` guarantees ZERO cross-tenant visibility into other residential halls.",
        "HOD Console (Department/Trade Tenant):",
        "  • Scoped strictly by trade specialization (e.g. Electrical Maintenance, Civil, Sanitation).",
        "  • Oversees staff roster, active workload, and department SLA compliance across campus.",
        "Zero-Login Actors (Student & Technician):",
        "  • Protected entirely through 32-character and UUID sessionless tokens with rate limiting."
    ], header_color=NAVY_DARK)

    set_notes(s9, """
Slide 9 illustrates our Multi-Tenant Role-Based Access Control architecture.
In a university with autonomous residential halls and technical departments, data isolation is an absolute requirement. A Provost must never see disciplinary or facility issues belonging to another hall.

We enforced this through custom query scoping in `permissions.py`:
- The Registrar acts as the super-tenant, receiving an aggregated macro view across the university.
- The Provost console inspects the user's profile and automatically restricts all Django QuerySets to that specific Residential Hall and its constituent hostels. Even if a user attempts to manually alter URL query parameters, the ORM filter guarantees zero cross-tenant leakage.
- The Head of Department (HOD) is scoped strictly by trade jurisdiction across campus buildings.
- Finally, students and technicians operate on zero-login tokenized endpoints, eliminating credential management overhead.
""")

    # =========================================================================
    # SLIDE 10: Relational Data Architecture (ERD)
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    set_slide_background(s10, SLATE_BG)
    add_header(s10, "Database Design", "Relational Data Architecture & Entity Relationships", 10)

    # Check if ERD.png exists
    erd_img = "diagrams/ERD.png"
    if os.path.exists(erd_img):
        s10.shapes.add_picture(erd_img, Inches(0.8), Inches(1.55), width=Inches(5.0))
        c_left = 6.1
        c_width = 6.4
    else:
        c_left = 0.8
        c_width = 11.7

    add_card(s10, c_left, 1.55, c_width, 5.3, "Core Entities & Relational Integrity", [
        "Spatial Model Hierarchy:",
        "  • `Campus` 1:N `Building` (with recursive `parent` for Hostels).",
        "  • `Building` 1:N `Floor` 1:N `Room` (with unique `qr_code_token`).",
        "Operational Complaint Core:",
        "  • `Complaint`: Central hub containing `reference`, `tracking_token`, `staff_task_token`, priority scores, SLAs, timestamps, and status.",
        "  • `ComplaintCategory`: Mapped directly to trade `Department` with default SLA hours.",
        "Audit Trail & Accountability:",
        "  • `ComplaintStatusHistory`: Immutable append-only audit log capturing every state transition, actor, and timestamp.",
        "  • `UserProfile`: Extends Django User with role (Admin, Provost, HOD, Staff), assigned hall, and `accountability_score`.",
        "  • `Feedback`: Captures student star ratings and closure commentary.",
        "Referential Integrity: Strict cascading policies (`PROTECT` on departments/halls to prevent orphan tickets; `CASCADE` on rooms)."
    ], header_color=NAVY_DARK)

    set_notes(s10, """
Slide 10 details our Relational Database Schema and Entity-Relationship model.
Our database is structured into three clean functional clusters:
1. The Spatial Cluster: Encompassing Campus, Building, Floor, and Room. Notice the recursive parent relationship on Building, which allows 84 hostels to link seamlessly to 20 halls.
2. The Operational Complaint Core: The Complaint model maintains dual cryptographic tokens—one for student tracking and one for technician task management. It stores calculated priority scores and target SLA timestamps.
3. The Audit and Governance Cluster: We enforce complete traceability through `ComplaintStatusHistory`, an append-only log that records every state change, actor, and timestamp. The `UserProfile` model tracks the technician's accountability score, while `Feedback` stores verified student ratings.
""")

    # =========================================================================
    # SLIDE 11: End-to-End System Flow (Sequence)
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    set_slide_background(s11, SLATE_BG)
    add_header(s11, "Execution Lifecycle", "End-to-End Complaint Lifecycle & Sequence Flow", 11)

    # Check if Sequence.png exists
    seq_img = "diagrams/Sequence.png"
    if os.path.exists(seq_img):
        s11.shapes.add_picture(seq_img, Inches(0.8), Inches(1.55), width=Inches(6.4))
        c_left = 7.5
        c_width = 5.0
    else:
        c_left = 0.8
        c_width = 11.7

    add_card(s11, c_left, 1.55, c_width, 5.3, "Step-by-Step Lifecycle Sequence", [
        "1. Anonymous Submission: Student submits description + enrollment number. System auto-binds room via QR or dynamic lookup.",
        "2. AI Triage: Engine detects trade category, calculates priority (Urgent/High/Normal/Low), and sets target SLA.",
        "3. Autonomous Dispatch: Staff matcher selects least-loaded nearby technician and generates `staff_task_token`.",
        "4. In-Progress & Timer: Technician arrives on site, clicks task link, and marks 'In Progress'. Server records start time.",
        "5. Dwell & Photo Proof: Technician completes physical repair, waits out 5-min dwell period, uploads camera photo, and marks 'Resolved'.",
        "6. Student Closure or Dispute: Student inspects work. If satisfied, student closes ticket and photos are purged. If dissatisfied, ticket reopens as Urgent with -15 pt penalty."
    ], header_color=NAVY_DARK)

    set_notes(s11, """
Slide 11 walks through the complete end-to-end Sequence Diagram of a maintenance request:
From the initial student submission to final verification, every transition is event-driven and validated.
Notice how the system decouples actors: the student interacts with their private tracking token; the backend performs AI triage and autonomous technician dispatching; the technician operates through their task token link subject to the 5-minute dwell timer; and final authority rests in the hands of the student.
This ensures zero friction for users while maintaining complete institutional rigor.
""")

    # =========================================================================
    # SLIDE 12: Quality Assurance & 5 Verification Pillars
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    set_slide_background(s12, SLATE_BG)
    add_header(s12, "Verification & Testing", "Rigorous Quality Assurance across 5 Verification Pillars", 12)

    pillars = [
        ("Pillar 1: Security & RBAC Scoping", [
            "Cross-Tenant Leak Audits: Automated tests verify Provost SSN cannot access Sarojini Naidu Hall tickets.",
            "CSRF & Token Integrity: Validates UUID token entropy and rejects tampered tracking queries.",
            "Role Routing Verification: Guarantees unauthenticated users are redirected to login."
        ], NAVY_DARK),
        ("Pillar 2: Database & Query Performance", [
            "N+1 Query Elimination: `select_related` and `prefetch_related` on spatial and category lookups.",
            "Relational Cascades: Verifies protected foreign key deletions.",
            "Index Verification: Audits query latency on 30,000+ complaint records."
        ], NAVY_DARK),
        ("Pillar 3: Reliability & Lifecycle", [
            "Dwell Timer Integrity: Tests assert rejection when resolution attempted at 4m 59s; accepts at 5m 01s.",
            "Illegal State Jump Prevention: Prevents jumping directly from 'Submitted' to 'Closed'.",
            "Auto-Purge Verification: Confirms disk file unlinking upon verified closure."
        ], AMBER_ACCENT),
        ("Pillar 4: Mobile & Accessibility", [
            "Responsive Viewport Audits: Touch targets ≥ 48px for one-handed mobile technician use.",
            "Zero-Login Usability: Validates complaint filing workflow in < 60 seconds on mobile devices.",
            "In-Memory Image Compression: Validates Pillow compression without memory leaks."
        ], NAVY_DARK),
        ("Pillar 5: ML & Spatial Resilience", [
            "NLP Triage Accuracy: Benchmarked across hundreds of natural student complaint descriptions.",
            "Fallback Resilience: Gracefully handles unknown locations and missing room tokens.",
            "Load Balancer Stability: Verified round-robin distribution across 157 technicians."
        ], TEAL_ACCENT),
        ("Test Execution Benchmark", [
            "Official Django Test Suite: 28 Unit & Integration tests passing with 100% success rate.",
            "Automated Test Scripts: `test_pillar1` through `test_pillar5` passing all assertions.",
            "Production Ready: Zero unresolved regression warnings."
        ], GREEN_ACCENT)
    ]

    for idx, (p_title, p_items, p_color) in enumerate(pillars):
        row = idx // 3
        col = idx % 3
        p_left = 0.8 + col * 4.0
        p_top = 1.55 + row * 2.65
        add_card(s12, p_left, p_top, 3.7, 2.45, p_title, p_items, header_color=p_color)

    set_notes(s12, """
Slide 12 covers our formal verification methodology. In software engineering, especially for academic projects, claims must be backed by rigorous automated testing. We established 5 Verification Pillars:

Pillar 1: Security and RBAC Scoping, verifying zero cross-tenant leakage.
Pillar 2: Database Optimization, testing index performance and eliminating N+1 query bottlenecks.
Pillar 3: Reliability and Lifecycle State Machine, specifically validating that our 5-minute dwell timer strictly rejects premature closures.
Pillar 4: Mobile Accessibility and In-Memory Image Processing.
Pillar 5: AI and Spatial Resilience, testing edge cases in natural language complaint descriptions.

Our official Django test suite contains 28 comprehensive test cases, achieving a 100% pass rate.
""")

    # =========================================================================
    # SLIDE 13: Operational Impact & Real AMU Data Ingestion
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    set_slide_background(s13, SLATE_BG)
    add_header(s13, "Results & Evaluation", "Real-World AMU Deployment Readiness & Operational Impact", 13)

    # 4 Stat callouts
    add_stat_box(s13, 0.8, 1.55, 2.7, 1.1, "100%", "Ghost Closures Eliminated", color=GREEN_ACCENT)
    add_stat_box(s13, 3.8, 1.55, 2.7, 1.1, "< 60s", "Average Submission Time", color=TEAL_ACCENT)
    add_stat_box(s13, 6.8, 1.55, 2.7, 1.1, "157", "Active AMU Staff Ingested", color=BLUE_ACCENT)
    add_stat_box(s13, 9.8, 1.55, 2.7, 1.1, "0%", "Cross-Tenant Data Leaks", color=NAVY_DARK)

    add_card(s13, 0.8, 2.85, 5.7, 4.0, "Operational Metrics & Improvements", [
        "Elimination of Ghost Closures: The combination of the 5-minute dwell timer, mandatory photo proof, and student verification permanently prevents unverified task completions.",
        "Zero Lost Complaints: Replaces paper registers with centralized database storage; tickets cannot be discarded or overlooked.",
        "Clear SLA Traceability: Escalation protocols ensure overdue tickets are visibly flagged on administrative dashboards with countdown timers.",
        "Frictionless Student Adoption: Anonymity and zero-login submission remove barriers; students report infrastructure defects early before secondary damage spreads."
    ], header_color=TEAL_ACCENT)

    add_card(s13, 6.8, 2.85, 5.7, 4.0, "Institutional Dataset Ingestion", [
        "Halls of Residence: Modeled all major AMU halls (Sir Syed North, Sir Syed South, Sir Shah Sulaiman, Aftab, Mohsinul Mulk, Sarojini Naidu, Indira Gandhi, etc.).",
        "Constituent Hostels: 84 verified hostels linked with correct capacities and floor counts.",
        "Technician Staff Directory: 157 maintenance staff categorized by trade (Electrician, Plumber, Mason, Carpenter, Pump Operator, Sanitary Worker).",
        "Idempotent Sync Scripts: Automated ingestion scripts (`sync_halls_hostels.py`, `sync_departments.py`) allow seamless re-syncing without data duplication."
    ], header_color=NAVY_DARK)

    set_notes(s13, """
Slide 13 demonstrates our real-world deployment readiness and measurable impact.
CampusCare is not an abstract theoretical prototype; it has ingested the actual operational data of Aligarh Muslim University. All 20 residential halls, 84 constituent hostels, and 157 maintenance personnel from official staff directories are active in the system.

Our metrics indicate:
- 100% elimination of ghost closures, because only the student holds closing authority.
- Average student complaint submission time reduced to under 60 seconds.
- Zero cross-tenant data leaks across all administrative portals.
- 100% SLA accountability, replacing lost paper registers with an unalterable audit trail.
""")

    # =========================================================================
    # SLIDE 14: Future Roadmap & System Enhancements
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    set_slide_background(s14, SLATE_BG)
    add_header(s14, "Future Scope", "Future Roadmap & Planned System Enhancements", 14)

    add_card(s14, 0.8, 1.55, 3.7, 5.3, "1. Real-Time Telemetry & Alerts", [
        "WebSocket Integration: Real-time live status push notifications replacing HTTP polling.",
        "SMS Gateway Integration: Direct SMS alerts to technician feature phones with one-tap task URLs.",
        "Automated WhatsApp Bot: Conversational complaint filing and status queries via WhatsApp Business API."
    ], header_color=NAVY_DARK)

    add_card(s14, 4.8, 1.55, 3.7, 5.3, "2. IoT Smart Campus Integration", [
        "Water Tank Ultrasonic Sensors: Automatic complaint creation when overhead hostel water tanks drop below 15% capacity.",
        "Electrical Meter Surge Detectors: Automated dispatch on detection of circuit breaker trips or phase failures in hostel wings.",
        "Predictive Maintenance: ML forecasting of pump and generator maintenance intervals."
    ], header_color=TEAL_ACCENT)

    add_card(s14, 8.8, 1.55, 3.7, 5.3, "3. University ERP & Mobile App", [
        "AMU SIS Integration: Direct single sign-on with Controller of Examinations (CoE) database for instant student enrollment verification.",
        "Native Mobile PWA: Offline service workers allowing technicians to log work in basements with background sync.",
        "Multilingual Support: Full UI internationalization in English, Urdu, and Hindi."
    ], header_color=BLUE_ACCENT)

    set_notes(s14, """
Slide 14 outlines our Future Development Roadmap:
Phase 3 development will expand CampusCare in three high-impact directions:
1. Real-time push notifications using WebSockets and automated SMS gateways to support technicians using feature phones.
2. IoT Smart Campus Integration, connecting ultrasonic water level sensors and electricity phase monitors directly to the auto-dispatch engine.
3. Deeper institutional integration with the AMU Controller of Examinations database, along with multilingual localization in Hindi and Urdu to maximize accessibility for all campus staff.
""")

    # =========================================================================
    # SLIDE 15: Conclusion & Viva Q&A Defense
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    set_slide_background(s15, NAVY_DARK)

    # Accent decorative bar
    bar_end = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.1), Inches(1.5), Inches(0.08))
    bar_end.fill.solid()
    bar_end.fill.fore_color.rgb = TEAL_ACCENT
    bar_end.line.fill.background()

    # Category Pill
    pill_end = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.35), Inches(3.2), Inches(0.35))
    pill_end.fill.solid()
    pill_end.fill.fore_color.rgb = NAVY_LIGHT
    pill_end.line.color.rgb = TEAL_ACCENT
    pe_tf = pill_end.text_frame
    pe_p = pe_tf.paragraphs[0]
    pe_p.alignment = PP_ALIGN.CENTER
    pe_p.text = "PROJECT SUMMARY & DEFENSE"
    pe_p.font.name = FONT_HEADING
    pe_p.font.size = Pt(9.5)
    pe_p.font.bold = True
    pe_p.font.color.rgb = TEAL_ACCENT

    # Main Conclusion Title
    cbox = s15.shapes.add_textbox(Inches(0.8), Inches(1.85), Inches(11.5), Inches(1.0))
    ctf = cbox.text_frame
    cp = ctf.paragraphs[0]
    cp.text = "Conclusion & Academic Defense"
    cp.font.name = FONT_HEADING
    cp.font.size = Pt(38)
    cp.font.bold = True
    cp.font.color.rgb = WHITE

    # 3 Summary Cards
    conclusions = [
        ("Engineering Merit", "Engineered a robust, scalable multi-tenant architecture with row-level query scoping, achieving 100% tenant isolation across 20 Residential Halls and 84 Hostels."),
        ("Operational Innovation", "Introduced the anti-fraud dwell timer, tokenized zero-login workflows, automated image compression, and student-governed closure verification."),
        ("Academic Compliance", "Fully compliant with IEEE 830-1998 standards, validated by 28 automated test suites, with complete documentation and live AMU data ingestion.")
    ]
    for idx, (head, body) in enumerate(conclusions):
        c_left = 0.8 + idx * 4.0
        c_box = s15.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(c_left), Inches(3.0), Inches(3.7), Inches(2.2))
        c_box.fill.solid()
        c_box.fill.fore_color.rgb = NAVY_LIGHT
        c_box.line.color.rgb = RGBColor(51, 65, 85)
        c_tf = c_box.text_frame
        c_tf.word_wrap = True
        
        hp = c_tf.paragraphs[0]
        hp.text = head.upper()
        hp.font.name = FONT_HEADING
        hp.font.size = Pt(12)
        hp.font.bold = True
        hp.font.color.rgb = TEAL_ACCENT
        
        bp = c_tf.add_paragraph()
        bp.text = body
        bp.font.name = FONT_BODY
        bp.font.size = Pt(11)
        bp.font.color.rgb = RGBColor(241, 245, 249)

    # Thank you / Q&A text
    qa_box = s15.shapes.add_textbox(Inches(0.8), Inches(5.6), Inches(11.5), Inches(1.2))
    qtf = qa_box.text_frame
    qp = qtf.paragraphs[0]
    qp.alignment = PP_ALIGN.CENTER
    qp.text = "Thank you for your time and guidance.\nWe are now ready for your questions and evaluation."
    qp.font.name = FONT_HEADING
    qp.font.size = Pt(18)
    qp.font.bold = True
    qp.font.color.rgb = WHITE

    set_notes(s15, """
In conclusion, CampusCare bridges the long-standing divide between student satisfaction and university maintenance operations. By eliminating reporting friction, enforcing automated spatial triage, mandating physical anti-fraud dwell times, and empowering students with final closure authority, we have created an enterprise-ready system tailored to the complex realities of large institutions like AMU.

Thank you very much, Professor. The floor is now open for your questions and feedback.
""")

    prs.save(output_path)
    print(f"Presentation saved successfully to {output_path} with {len(prs.slides)} slides!")

if __name__ == "__main__":
    build_presentation()
