# 🏛️ CampusCare: University Facility Maintenance & Operations Platform

[![Django](https://img.shields.io/badge/Django-5.0+-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed%20(100%25)-brightgreen.svg)](core/tests.py)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-emerald.svg)]()

**CampusCare** is an enterprise-grade, multi-tenant facility management and automated complaint lifecycle resolution system built for massive collegiate campuses (modeled on Aligarh Muslim University - AMU). It bridges students, campus administration, and maintenance staff through friction-free, zero-login student tracking and technician task execution.

---

## 🌟 Key Features

### 1. 🏢 Complete Campus Spatial Hierarchy
- **20 Residential Halls & 84 Constituent Hostels**: Complete model hierarchy with self-referential `parent` relations, wing details, room capacities, and floor maps.
- **Academic & Operational Facilities**: Isolated academic faculties, departments, and central services.
- **Dynamic Room Lookups**: Real-time room, hall, and hostel resolution via `/api/room-lookup/` and QR code tokens.

### 2. 🔐 Row-Level Multi-Tenant RBAC Scoping
- **Registrar Global Console**: Complete university-wide overview across all halls, departments, and services.
- **Provost Console**: Scoped strictly to the specific Residential Hall and its child constituent hostels (e.g., Sir Syed Hall North + 8 hostels). Zero cross-tenant data leaks.
- **HOD Console**: Scoped strictly to the department's trade jurisdiction (e.g., Electrical Maintenance, Civil, Sanitation).

### 3. 🤖 AI Spatial Triage & Auto-Dispatch
- **NLP Category Suggestion**: Automatic heuristics and ML-assisted category prediction (e.g., *Estate Plumbing*, *Electrical*, *Sanitation*).
- **Automated Technician Roster Dispatch**: Automatically routes tickets to on-duty technicians mapped from a 157-person AMU maintenance staff directory based on geographic proximity, trade specialization, and current active task load.
- **Explainable SLA & Urgency Scoring**: Rule-based priority assignment (Urgent: 2h, High: 6h, Normal: 24h, Low: 72h).

### 4. 👷 Zero-Login Technician Workflow & Anti-Fraud Timing
- **Tokenized Access**: Technicians receive a secure direct task link (`/task/<uuid:staff_task_token>/`) requiring zero password login.
- **Anti-Fraud Dwell Timer**: Enforces a strict minimum **5-minute dwell time** between marking a task `in_progress` and attempting `resolved` to eliminate fraudulent remote closures.
- **Mandatory Camera Proof**: Resolution requires photo proof, compressed in-memory via Pillow before disk persistence.
- **Closure Protection**: Technicians cannot close complaints—only mark them `resolved` awaiting student verification.

### 5. 🔄 Closed-Loop Student Verification & Automated Media Purge
- **Zero-Login Student Tracking**: Students report complaints anonymously with their enrollment number and track updates in real-time via a private 32-character `tracking_token`.
- **Student Verification & Rating**: Once resolved, the student confirms closure with star ratings and feedback.
- **Storage Cleanup**: Upon confirmation, `complaint.purge_attached_media()` automatically unlinks and permanently deletes evidence and resolution photos from disk storage.

### 6. ⚠️ Dispute & Technician Accountability Engine
- **Dispute with Mandatory Proof**: Students can reopen disputed resolutions within the tracking portal by providing detailed reasons (≥ 10 chars) and mandatory camera proof.
- **Automated Escalation**: Reopened complaints escalate automatically to `Urgent` priority (`priority_score = 95`).
- **Accountability Penalty**: Assigned technicians receive an automatic **-15 point deduction** from their `accountability_score` upon legitimate student dispute.

---

## 📂 Project Directory Structure

```text
CampusCare/
├── manage.py                                 # Django management CLI entrypoint
├── requirements.txt                          # Project Python dependencies
├── sync_git.sh                              # One-click continuous Git sync helper
├── AMU Halls and Hostels - Sheet1.csv       # 20 Halls & 84 Constituent Hostels data
├── updated AMU - ... - Teaching Depts.csv    # Teaching departments & services CSV
├── staff list.xlsx                           # AMU staff & technician directory
│
├── campuscare/                               # Project Configuration
│   ├── settings.py                          # Core Django settings (Asia/Kolkata TZ, etc.)
│   ├── urls.py                              # Root URL router
│   ├── wsgi.py & asgi.py                    # Web server gateway interfaces
│
├── core/                                     # Core Application
│   ├── models.py                            # Spatial, Complaint, UserProfile & Feedback models
│   ├── views.py                             # Dashboard, complaint lifecycle, token APIs
│   ├── urls.py                              # App endpoints and reverse aliases
│   ├── forms.py                             # Validated submission and management forms
│   ├── permissions.py                       # Multi-tenant RBAC row-level query scoping
│   ├── ai_triage.py                         # AI spatial triage & room resolution
│   ├── staff_matcher.py                     # Staff roster matcher & heuristic allocation
│   ├── dispatcher.py                        # Automated complaint auto-dispatch
│   ├── smart.py                             # NLP category suggestion & heuristic priority
│   ├── tests.py                             # Official unit & integration test suite (28 tests)
│   ├── migrations/                          # 10 production migrations (clean & idempotent)
│   └── ml_models/                           # Trained ML urgency classifier & metadata
│
├── templates/                                # HTML Templates
│   ├── base.html                            # Master responsive layout
│   ├── registration/                        # Unified authentication views
│   └── core/                                # Feature views (halls, dashboards, task portal)
│
├── static/                                   # Static JavaScript & CSS stylesheets
└── media/                                    # Uploaded media storage (protected via .gitkeep)
```

---

## 🚀 Quick Start & Installation

### Prerequisites
- Python 3.9+
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/dynamic-cod/CampusCare.git
cd CampusCare

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Database Migrations
```bash
python manage.py migrate
```

### 3. Synchronize Campus Data & Sub-Admin Accounts
```bash
python sync_departments.py
python sync_halls_hostels.py
```

### 4. Run Automated QA & Test Suites
```bash
# Run Django official test suite (28 tests)
python manage.py test core

# Run route integrity audit
python test_route_integrity.py

# Run end-to-end integration and anti-fraud lifecycle suite
python test_system_flows.py

# Run spatial hierarchy and Provost credential audit
python verify_halls_hostels.py
```

### 5. Launch the Development Server
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/` in your browser.

---

## 👥 Default Credentials (Development)

| Role | Username | Password | Jurisdiction |
| :--- | :--- | :--- | :--- |
| **Registrar** | `registrar_office` | `CampusAdmin@2026` | Global University Jurisdiction |
| **Provost (SSN)** | `provost_ssn` | `CampusAdmin@2026` | Sir Syed Hall North + 8 Hostels |
| **Provost (SNH)** | `provost_snh` | `CampusAdmin@2026` | Sarojini Naidu Hall + 2 Hostels |
| **HOD (Electrical)** | `hod_elec` | `CampusAdmin@2026` | Electrical Maintenance Department |
| **Student** | *No account needed* | *Direct Submission* | Anonymous tracking via Token |
| **Technician** | *No account needed* | *Task Token Link* | Zero-login direct portal access |

---

## 🔄 Continuous Sync Helper

To stage, commit, and push updates in one command:
```bash
./sync_git.sh "feat: add your commit message here"
```

---

## 📄 License
This project is licensed under the MIT License.
