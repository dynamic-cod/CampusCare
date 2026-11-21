# CampusCare — Visual Architecture Diagrams

**Document ID:** CC-ARCH-2025-v1.0  
**Companion to:** `SRS.md` (CC-SRS-2025-v1.0)  
**Standard:** IEEE 830-1998 / ISO/IEC/IEEE 29148:2018 — Architecture Supplement  
**Date:** October 2025  

> All diagrams render in Antigravity IDE / VS Code Markdown Preview (Mermaid.js).  
> ASCII backups follow each diagram for terminal and plain-text compatibility.

---

## Table of Contents

1. [Diagram 1 — Entity-Relationship Diagram (ERD)](#diagram-1--entity-relationship-diagram-erd)
2. [Diagram 2 — Complaint Lifecycle State Machine](#diagram-2--complaint-lifecycle-state-machine)
3. [Diagram 3 — Sequence Diagram: Anonymous Complaint Submission & AI Triage](#diagram-3--sequence-diagram-anonymous-complaint-submission--ai-triage)
4. [Diagram 4 — RBAC Layered Architecture & Role Routing](#diagram-4--rbac-layered-architecture--role-routing)
5. [Diagram 5 — High-Level Architecture & Security Boundary](#diagram-5--high-level-architecture--security-boundary)
6. [Diagram 6 — UML Use Case Diagram](#diagram-6--uml-use-case-diagram)

---

## Diagram 1 — Entity-Relationship Diagram (ERD)

This ERD captures the complete CampusCare data model as defined in `core/models.py`, including all foreign keys, self-referencing hierarchies, unique constraints, and audit trail relationships. It is the authoritative structural reference for database migration scripts and API design.

```mermaid
erDiagram
    Campus {
        bigint id PK
        string name UK
        string code UK
        text address
        bool is_active
        datetime created_at
        datetime updated_at
    }

    Building {
        bigint id PK
        string name
        string code
        string short_name
        string gender
        string building_type
        string wing_detail
        string capacity_detail
        decimal latitude
        decimal longitude
        bool is_active
        datetime created_at
        datetime updated_at
    }

    Floor {
        bigint id PK
        int number
        string label
        datetime created_at
        datetime updated_at
    }

    Room {
        bigint id PK
        string number
        string name
        string qr_code_token UK
        bool is_active
        datetime created_at
        datetime updated_at
    }

    Department {
        bigint id PK
        string name UK
        string code UK
        string email
        string phone
        bool is_active
        datetime created_at
        datetime updated_at
    }

    ComplaintCategory {
        bigint id PK
        string name UK
        text description
        int default_sla_hours
        bool is_active
        datetime created_at
        datetime updated_at
    }

    UserProfile {
        bigint id PK
        string role
        int accountability_score
        string phone
        string hall_location
        datetime created_at
        datetime updated_at
    }

    Complaint {
        bigint id PK
        string reference UK
        string tracking_token UK
        uuid staff_task_token UK
        string reporter_name
        string reporter_enrollment_number
        string title
        text description
        string priority
        int priority_score
        string priority_reason
        string status
        string location_description
        bool category_detected_automatically
        int category_detection_confidence
        image evidence
        image resolution_proof
        image reopen_proof
        text resolution_note
        text reopen_reason
        int reopen_count
        int reopened_count
        bool is_public
        string resolution_verification
        datetime assigned_at
        datetime in_progress_at
        datetime resolved_at
        datetime closed_at
        datetime reopened_at
        datetime sla_due_at
        datetime escalated_at
        int escalation_level
        datetime resolution_verified_at
        datetime created_at
        datetime updated_at
    }

    ComplaintStatusHistory {
        bigint id PK
        string status
        text note
        datetime created_at
    }

    ComplaintSupport {
        bigint id PK
        string session_key
        datetime created_at
    }

    ComplaintFeedback {
        bigint id PK
        int rating
        text comment
        datetime created_at
    }

    AuthUser {
        bigint id PK
        string username UK
        string email
        bool is_staff
        bool is_superuser
    }

    Campus ||--o{ Building : "has"
    Building ||--o| Building : "parent (hostel blocks)"
    Building ||--o{ Floor : "contains"
    Building }o--o| Department : "managed by"
    Floor ||--o{ Room : "contains"
    Department ||--o{ ComplaintCategory : "owns"
    Department ||--o{ UserProfile : "employs"
    AuthUser ||--|| UserProfile : "extends"
    UserProfile }o--o| Building : "managed_building"
    UserProfile }o--o| Department : "managed_department"
    Complaint }o--o| Room : "located in"
    Complaint }o--|| ComplaintCategory : "categorised as"
    Complaint }o--o| AuthUser : "reported by (optional)"
    Complaint }o--o| AuthUser : "assigned to"
    Complaint }o--o| AuthUser : "assigned by"
    Complaint }o--o| Complaint : "duplicate of"
    Complaint ||--o{ ComplaintStatusHistory : "audit trail"
    Complaint ||--o{ ComplaintSupport : "community votes"
    Complaint ||--o| ComplaintFeedback : "satisfaction rating"
    ComplaintStatusHistory }o--o| AuthUser : "changed by"
    ComplaintSupport }o--o| AuthUser : "cast by (or anon session)"
```

**ASCII Backup:**

```
┌─────────┐    ┌──────────┐    ┌───────┐    ┌──────┐
│ Campus  │1──*│ Building │1──*│ Floor │1──*│ Room │
└─────────┘    └──┬───────┘    └───────┘    └──┬───┘
                  │ (self-FK: parent)           │
                  │ ┌──────────────────────┐    │
                  └─┤ Constituent Hostel   │    │
                    └──────────────────────┘    │
                                                │
┌────────────┐    ┌──────────────────┐         │
│ Department │1──*│ ComplaintCategory│         │
└────┬───────┘    └────────┬─────────┘         │
     │                     │                   │
     │         ┌───────────▼───────────────────▼──┐
     │         │           Complaint               │
     │         │  reference UK | tracking_token UK │
     │         │  staff_task_token (UUID) UK        │
     │         │  priority | status | sla_due_at    │
     │         │  resolution_verification           │
     │         └───┬───────────────────────────────┘
     │             │
     │    ┌────────▼──────────────────────────────────┐
     │    │  ComplaintStatusHistory  ComplaintSupport  │
     │    │  ComplaintFeedback (1:1)                   │
     │    └───────────────────────────────────────────┘
     │
┌────▼───────────┐    ┌──────────┐
│ UserProfile    │────│ AuthUser │
│ role           │    └──────────┘
│ managed_bldg   │
│ accountability │
└────────────────┘
```

---

## Diagram 2 — Complaint Lifecycle State Machine

This state machine defines all valid transitions for `Complaint.status`, including guards (role and proof requirements), anti-fraud controls (dwell-time), and the resolution verification loop. It is the authoritative reference for all status-transition business logic in `core/views/complaints.py` and `core/views/tasks.py`.

```mermaid
stateDiagram-v2
    [*] --> OPEN : Student submits complaint\n[enrollment valid, cap < 3]

    OPEN --> ASSIGNED : Provost / HOD / Registrar assigns technician\n[staff_task_token generated, sla_due_at set]

    ASSIGNED --> IN_PROGRESS : Technician accepts task via UUID URL\n[in_progress_at = now()]

    IN_PROGRESS --> RESOLVED : Technician uploads resolution_proof\n[dwell_time >= 5 min server-side enforced]

    RESOLVED --> CLOSED : Student confirms resolution\nOR auto-close after verification window\n[media purged from disk]

    RESOLVED --> REOPENED : Student rejects resolution\n[reopen_proof required, reopen_reason required]

    REOPENED --> ASSIGNED : Provost / HOD / Registrar re-assigns\n[sla_due_at recalculated]

    CLOSED --> [*] : Terminal state\n[all media purged, ticket archived]

    note right of OPEN
        AI Triage runs on save():
        - Spatial origin detection
        - ML urgency classification
        - priority_score set
    end note

    note right of IN_PROGRESS
        Anti-Fraud Guards:
        - Dwell-time >= 5 min
        - resolution_proof mandatory
        - UUID token single-use
    end note

    note right of RESOLVED
        resolution_verification = PENDING
        Awaiting student action
    end note

    note right of CLOSED
        purge_attached_media() called:
        - evidence deleted
        - resolution_proof deleted
        - reopen_proof deleted
    end note
```

**ASCII Backup:**

```
                    [Student Submits]
                    enrollment valid
                    cap < 3 tickets
                          │
                          ▼
                       ┌──────┐
                       │ OPEN │ ◄─────────────────────────┐
                       └──┬───┘                            │
                          │ Provost/HOD/Registrar assigns  │
                          │ sla_due_at = now + SLA hours   │
                          ▼                                │
                     ┌──────────┐                         │
                     │ ASSIGNED │                         │
                     └────┬─────┘                         │
                          │ Technician accepts UUID URL    │
                          │ in_progress_at = now()        │
                          ▼                                │
                   ┌─────────────┐                        │
                   │ IN_PROGRESS │                        │
                   └──────┬──────┘                        │
                          │ Technician uploads proof       │
                          │ dwell_time >= 5min (enforced) │
                          ▼                                │
                     ┌──────────┐   Student rejects       │
                     │ RESOLVED │ ─────────────────────► ┌──────────┐
                     └────┬─────┘   reopen_proof required│ REOPENED │
                          │                               └────┬─────┘
                 Student confirms                              │ Re-assigned
                 OR auto-close                                 └─────────────┘
                          │
                          ▼
                      ┌────────┐
                      │ CLOSED │ ──► media purged from disk ──► [*]
                      └────────┘
```

---

## Diagram 3 — Sequence Diagram: Anonymous Complaint Submission & AI Triage

This sequence diagram traces the complete request lifecycle from a student's form submission through the AI triage pipeline, ML urgency classification, database persistence, and tracking token delivery. It documents the integration points between `core/views/complaints.py`, `core/ai_triage.py`, `core/smart.py`, and the Django ORM.

```mermaid
sequenceDiagram
    autonumber

    actor Student as Anonymous Student
    participant Browser as Mobile Browser
    participant ComplaintView as complaints.py<br/>complaint_create()
    participant Form as ComplaintForm<br/>forms.py
    participant SmartPy as smart.py<br/>classify_urgency()
    participant AiTriage as ai_triage.py<br/>bind_complaint_spatial_origin()
    participant Cache as In-Memory Cache<br/>_BUILDINGS_CACHE
    participant ORM as Django ORM
    participant DB as SQLite DB
    participant SuggestAPI as api.py<br/>suggest_category_api()

    Student->>Browser: Opens /complaints/new/
    Browser->>ComplaintView: GET /complaints/new/
    ComplaintView-->>Browser: Render blank ComplaintForm

    Student->>Browser: Types title + description
    Browser->>SuggestAPI: AJAX GET /api/suggest-category/?q=[query]
    SuggestAPI-->>Browser: JSON [ranked categories]
    Browser-->>Student: Auto-suggest dropdown populated

    Student->>Browser: Selects category, fills form, submits
    Browser->>ComplaintView: POST /complaints/new/ [CSRF token]
    ComplaintView->>Form: form.is_valid()
    Form->>Form: Validate enrollment number (regex)
    Form->>ORM: Check active complaint count for enrollment
    ORM->>DB: SELECT COUNT(*) WHERE enrollment=X AND status NOT IN (resolved, closed)

    alt Count >= 3
        DB-->>ORM: count = 3
        ORM-->>Form: Validation fails
        Form-->>ComplaintView: form.errors
        ComplaintView-->>Browser: Re-render form with errors
        Browser-->>Student: "Max 3 active tickets" error shown
    else Count < 3
        DB-->>ORM: count < 3
        ORM-->>Form: OK
        Form-->>ComplaintView: form.is_valid() = True

        ComplaintView->>SmartPy: classify_urgency(title + description)
        SmartPy->>SmartPy: Load urgency_classifier.joblib (cached)
        SmartPy-->>ComplaintView: {priority: "high", score: 72, reason: "..."}

        ComplaintView->>ORM: complaint.save() [pre-save hook]
        ORM->>AiTriage: bind_complaint_spatial_origin(complaint)
        AiTriage->>Cache: get_cached_buildings()

        alt Cache cold
            Cache->>DB: SELECT * FROM core_building WHERE is_active=True
            DB-->>Cache: Building list
        end

        Cache-->>AiTriage: [Building objects]
        AiTriage->>AiTriage: Alias matching on location_description
        AiTriage->>AiTriage: Floor number extraction (regex)

        alt Building + Floor matched
            AiTriage->>DB: SELECT Room WHERE floor=F AND number~=X
            DB-->>AiTriage: Room object
            AiTriage-->>ORM: complaint.room = Room
        else No match
            AiTriage-->>ORM: complaint.location_description preserved
        end

        ORM->>DB: INSERT INTO core_complaint (reference=CC-XXXXXXXX, tracking_token=[hex32], staff_task_token=[uuid4], ...)
        DB-->>ORM: complaint saved (pk assigned)
        ORM->>DB: INSERT INTO core_complaintstatushistory (status=open, ...)
        DB-->>ORM: History recorded

        ComplaintView-->>Browser: Redirect to /track/[tracking_token]/
        Browser-->>Student: Tracking page shown\n"Your reference: CC-XXXXXXXX\nToken: [hex32]"
    end
```

**ASCII Backup:**

```
Student   Browser   ComplaintView   Form   SmartPy   AiTriage   Cache   DB
  │          │            │           │        │          │         │      │
  │──GET /complaints/new/─►           │        │          │         │      │
  │          │            │──render form──────►│          │         │      │
  │──types, submits POST ─►           │        │          │         │      │
  │          │            │──is_valid()────────►           │         │      │
  │          │            │           │──regex check───────────────────────►│
  │          │            │           │──count check──────────────────────►DB
  │          │            │           │◄─count < 3 ──────────────────────DB│
  │          │            │──classify_urgency()──►        │         │      │
  │          │            │◄─{priority, score}───SmartPy  │         │      │
  │          │            │──complaint.save() ──►          │         │      │
  │          │            │                    ─bind_spatial()──────►      │
  │          │            │                               │──cache?──►Cache│
  │          │            │                               │          │──DB►│
  │          │            │                               │◄─buildings─────│
  │          │            │                               │──alias match    │
  │          │            │──INSERT Complaint ─────────────────────────────►│
  │          │            │──INSERT StatusHistory──────────────────────────►│
  │          │◄──redirect /track/[token]/─────────────────                  │
  │◄─tracking page shown─ │                                                 │
```

---

## Diagram 4 — RBAC Layered Architecture & Role Routing

This diagram maps the six CampusCare user roles to their corresponding view layers, permission decorators, and data access scopes. It documents how `core/permissions.py`, `core/decorators.py`, and `core/views/dashboards.py` cooperate to enforce the multi-tenant access control model, preventing IDOR and privilege escalation.

```mermaid
graph TB
    subgraph CLIENT["Client Tier — Browser Requests"]
        A1["🧑‍🎓 Student<br/>(Anonymous / Token-Auth)"]
        A2["🔧 Maintenance Technician<br/>(Zero-Login UUID Worker)"]
        A3["🏛️ Hall Provost / Caretaker<br/>(Building-Scoped Admin)"]
        A4["📋 Maintenance HOD<br/>(Trade-Scoped Admin)"]
        A5["🎓 Central Registrar<br/>(Global SuperAdmin Console)"]
        A6["⚙️ System Administrator<br/>(Django SuperUser)"]
    end

    subgraph ROUTING["Routing & Permission Layer — core/decorators.py + core/permissions.py"]
        R1["@login_not_required<br/>Public complaint routes"]
        R2["@token_required<br/>UUID task validation"]
        R3["@role_required(PROVOST)<br/>+ building_scope_check()"]
        R4["@role_required(HOD)<br/>+ department_scope_check()"]
        R5["@role_required(REGISTRAR|ADMIN)<br/>No scope restriction"]
        R6["@superuser_required<br/>Full system access"]
    end

    subgraph VIEWS["View Layer — core/views/ package"]
        V1["public.py<br/>home, campus_directory,<br/>complaint_create, tracking"]
        V2["tasks.py<br/>technician_task_view"]
        V3["dashboards.py<br/>provost_dashboard()"]
        V4["dashboards.py<br/>hod_dashboard()"]
        V5["dashboards.py<br/>registrar_dashboard()<br/>analytics_dashboard()<br/>complaint_report_csv()"]
        V6["dashboards.py + admin<br/>Full management views"]
    end

    subgraph DATA["Data Access Layer — Django ORM Scope Filters"]
        D1["Complaint.objects.filter(<br/>  room__floor__building=managed_building<br/>)"]
        D2["Complaint.objects.filter(<br/>  category__department=managed_department<br/>)"]
        D3["Complaint.objects.all()<br/>No filter — global"]
        D4["ALL models — unrestricted"]
    end

    subgraph DB["Database — SQLite core_complaint + related tables"]
        DB1[("core_complaint<br/>core_complaintstatushistory<br/>core_userprofile")]
    end

    A1 --> R1 --> V1
    A2 --> R2 --> V2
    A3 --> R3 --> V3 --> D1
    A4 --> R4 --> V4 --> D2
    A5 --> R5 --> V5 --> D3
    A6 --> R6 --> V6 --> D4

    D1 --> DB1
    D2 --> DB1
    D3 --> DB1
    D4 --> DB1

    style CLIENT fill:#eff6ff,stroke:#2563eb,stroke-width:1.5px,color:#0f172a
    style ROUTING fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#0f172a
    style VIEWS fill:#f5f3ff,stroke:#7c3aed,stroke-width:1.5px,color:#0f172a
    style DATA fill:#fffbeb,stroke:#d97706,stroke-width:1.5px,color:#0f172a
    style DB fill:#fdf2f8,stroke:#db2777,stroke-width:1.5px,color:#0f172a
```

**ASCII Backup:**

```
┌─────────────────────────────────────────────────────────────────────┐
│ ACTOR         AUTH METHOD         SCOPE FILTER      DATA ACCESS      │
├─────────────────────────────────────────────────────────────────────┤
│ Student       None (anon)         Own token only    Submit + Track   │
│ Technician    UUID task token     Single complaint  Accept + Resolve │
│ Provost       Session + password  managed_building  Hall complaints  │
│ HOD           Session + password  managed_dept      Dept complaints  │
│ Registrar     Session + password  None (global)     All complaints   │
│ Admin         Superuser           None (global)     All + user mgmt  │
└─────────────────────────────────────────────────────────────────────┘

IDOR Prevention:
  Provost: ORM filter → room__floor__building = managed_building
  HOD:     ORM filter → category__department = managed_department
  (Not template-level — enforced at query level)
```

---

## Diagram 5 — High-Level Architecture & Security Boundary

This C4-inspired diagram illustrates the three-tier architecture of CampusCare — Client, Application/Middleware, and Data/Storage — along with the security perimeters, middleware stack, and the intelligent services layer. It serves as the deployment and security review reference for the system's monolithic Django architecture.

```mermaid
graph TB
    subgraph INTERNET["Internet / AMU Campus Network"]
        subgraph CLIENTS["Client Tier"]
            C1["📱 Anonymous Student\nMobile Browser\nNo auth — Token tracking\nQR complaint filing"]
            C2["🔧 Zero-Login Technician\nMobile Browser\nDirect UUID task URL\nPhoto upload"]
            C3["💻 Admin Console\nDesktop Browser\nSession-authenticated\nProvost · HOD · Registrar · Admin"]
        end
    end

    subgraph SERVER["Application Server — Django Monolith (Python 3.10+)"]
        subgraph SECURITY_LAYER["Security & Input Validation Layer"]
            S1["🛡️ Django SecurityMiddleware\nHSTS · X-Frame-Options\nContent-Type-Options"]
            S2["🗜️ GZipMiddleware\nWhiteNoise StaticFiles\nCompressed responses"]
            S3["🔑 CsrfViewMiddleware\nAll POST/PUT/DELETE\nToken validation"]
            S4["📋 SessionMiddleware\nHttpOnly · Secure cookies\nAnonymous session tracking"]
            S5["🚦 Rate Limiting Layer\ncomplaint_create: throttled\nAPI endpoints: throttled\n(env-configurable)"]
        end

        subgraph APP_LAYER["Application & Business Logic Layer"]
            A1["🌐 core/views/public.py\nHome · Directory\nRegistration"]
            A2["📝 core/views/complaints.py\nSubmission · Tracking\nFeedback · Reopen"]
            A3["⚙️ core/views/tasks.py\nTechnician Task View\nDwell-time enforcement"]
            A4["📊 core/views/dashboards.py\nRole-scoped dashboards\nAnalytics · Heatmap"]
            A5["🔌 core/views/api.py\nJSON endpoints\nSuggest · Urgency · Rooms"]
        end

        subgraph INTELLIGENT["Intelligent Services Layer"]
            I1["🧠 core/ai_triage.py\nSpatial origin detection\n80+ building alias dict\nFloor + Room binding"]
            I2["🤖 core/smart.py\nML urgency classifier\nTF-IDF pipeline\nFallback: rule-based"]
            I3["👥 core/dispatcher.py\n+ staff_matcher.py\nTechnician scoring\nSLA calculation"]
            I4["📈 core/accountability.py\nScore decay/recovery\nSLA breach detection"]
        end

        subgraph PERMISSIONS["RBAC & Permission Layer"]
            P1["core/permissions.py\ncore/decorators.py\n@role_required()\nBuilding/dept scope checks\nIDOR prevention"]
        end
    end

    subgraph STORAGE["Data & Storage Tier"]
        DB["🗄️ SQLite Database\ndb.sqlite3\n11 core tables\nComposite indexes\nUQ constraints"]
        MEDIA["📁 Local Media Store\nmedia/complaint_evidence/\nmedia/resolution_proofs/\nAuto-purged on closure"]
        ML["🧮 ML Model Cache\ncore/ml_models/\nurgency_classifier.joblib\nmodel_metadata.json"]
        STATIC["📦 Static Assets\nstaticfiles/\nWhitenoise-compressed\nHash-versioned"]
    end

    C1 -->|"HTTP/HTTPS\nAnonymous"| S1
    C2 -->|"HTTP/HTTPS\nUUID URL"| S1
    C3 -->|"HTTPS\nSession cookie"| S1

    S1 --> S2 --> S3 --> S4 --> S5

    S5 --> A1
    S5 --> A2
    S5 --> A3
    S5 --> A4
    S5 --> A5

    A1 --> P1
    A2 --> P1
    A3 --> P1
    A4 --> P1
    A5 --> P1

    A2 --> I1
    A2 --> I2
    A4 --> I3
    A4 --> I4

    P1 --> DB
    I1 --> DB
    I3 --> DB
    I4 --> DB

    A2 --> MEDIA
    A3 --> MEDIA
    I2 --> ML

    A1 --> STATIC
    A4 --> STATIC

    style INTERNET fill:#f8fafc,stroke:#64748b,stroke-width:1.5px,color:#0f172a
    style SERVER fill:#f0fdf4,stroke:#16a34a,stroke-width:1.5px,color:#0f172a
    style STORAGE fill:#fdf2f8,stroke:#db2777,stroke-width:1.5px,color:#0f172a
    style CLIENTS fill:#eff6ff,stroke:#2563eb,stroke-width:1.5px,color:#0f172a
    style SECURITY_LAYER fill:#fef3c7,stroke:#d97706,stroke-width:1.5px,color:#0f172a
    style APP_LAYER fill:#f5f3ff,stroke:#7c3aed,stroke-width:1.5px,color:#0f172a
    style INTELLIGENT fill:#ecfdf5,stroke:#059669,stroke-width:1.5px,color:#0f172a
    style PERMISSIONS fill:#f0f9ff,stroke:#0284c7,stroke-width:1.5px,color:#0f172a
```

**ASCII Backup:**

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  AMU CAMPUS NETWORK                                                          ║
║  ┌─────────────┐  ┌─────────────────┐  ┌──────────────────────────────┐    ║
║  │ Anon Student│  │  Technician     │  │  Admin Console               │    ║
║  │ Mobile      │  │  UUID task URL  │  │  Provost/HOD/Registrar/Admin  │    ║
║  └──────┬──────┘  └────────┬────────┘  └──────────────┬───────────────┘    ║
║         │                  │                           │                     ║
║         └──────────────────┴───────────────────────────┘                    ║
║                               HTTP/HTTPS                                     ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  APPLICATION SERVER — Django Monolith                                        ║
║  ┌─────────────────────────────────────────────────────────────────────┐    ║
║  │  SECURITY MIDDLEWARE STACK                                           │    ║
║  │  SecurityMiddleware → GZipMiddleware → CsrfViewMiddleware →         │    ║
║  │  SessionMiddleware → AuthMiddleware → RateLimiting                  │    ║
║  ├─────────────────────────────────────────────────────────────────────┤    ║
║  │  VIEW LAYER (core/views/)                                           │    ║
║  │  public.py  │ complaints.py  │ tasks.py  │ dashboards.py  │ api.py  │    ║
║  ├─────────────────────────────────────────────────────────────────────┤    ║
║  │  RBAC LAYER: core/permissions.py + core/decorators.py               │    ║
║  │  @role_required() → ORM scope filter → IDOR prevention              │    ║
║  ├─────────────────────────────────────────────────────────────────────┤    ║
║  │  INTELLIGENT SERVICES                                                │    ║
║  │  ai_triage.py  │  smart.py (TF-IDF ML)  │  dispatcher.py           │    ║
║  │  staff_matcher.py  │  accountability.py                             │    ║
║  └─────────────────────────────────────────────────────────────────────┘    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  DATA & STORAGE TIER                                                         ║
║  ┌────────────────┐  ┌────────────────────┐  ┌────────────────────────┐    ║
║  │  SQLite DB     │  │  Media Storage     │  │  ML Model Cache        │    ║
║  │  db.sqlite3    │  │  complaint_evidence│  │  urgency_classifier    │    ║
║  │  11 tables     │  │  resolution_proofs │  │  .joblib               │    ║
║  │  4 comp. idx   │  │  (purged on close) │  │  model_metadata.json   │    ║
║  └────────────────┘  └────────────────────┘  └────────────────────────┘    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Diagram 6 — UML 2.5 Use Case Diagram

This UML 2.5 Use Case diagram models the system boundary and behavioral goals of the **AMU CampusCare Facility Maintenance Platform**. The diagram formalizes interactions across the **5 verified operational actor roles**, delineating primary actors (initiating interaction on the client side) from secondary/administrative authorities (supervisory governance), with strict separation of internal sub-processes.

```mermaid
graph TB
    subgraph CampusCare_System["System Boundary: AMU CampusCare Facility Maintenance Platform"]
        direction TB

        subgraph Sub_Student["Citizen & Student Services"]
            direction LR
            UC_Lodge(["Lodge Maintenance Complaint"])
            UC_Track(["Track Ticket Status via Token"])
            UC_Confirm(["Confirm Resolution & Purge Media"])
            UC_Reopen(["Dispute & Reopen Ticket with Proof"])
            UC_Feedback(["Submit Resolution Feedback & Rating"])
            UC_Browse(["Browse Public Issue Board & Directory"])
            UC_Upvote(["Upvote Public Issue Support"])
        end

        subgraph Sub_Shared["Automated Platform Sub-Processes (Included / Extended)"]
            direction LR
            UC_Quota(["Verify Active Ticket Quota & Enrollment"])
            UC_Triage(["Classify ML Urgency & Spatial Origin"])
            UC_QR(["Auto-Fill Room Data via QR Code"])
            UC_Dwell(["Validate Anti-Fraud 5-Min Dwell Timer"])
            UC_Matcher(["Suggest Optimal Staff via Least-Load Matcher"])
        end

        subgraph Sub_Tech["Technician Operations (Zero-Login)"]
            direction LR
            UC_AccessTask(["Access Dispatched Task via UUID URL"])
            UC_AcceptTask(["Accept Task & Start Work"])
            UC_UploadProof(["Upload Photographic Resolution Proof"])
        end

        subgraph Sub_Admin["Administrative Governance & Oversight"]
            direction LR
            UC_ManageHall(["Manage Hall Queue (Building-Scoped)"])
            UC_ManageDept(["Manage Department Queue (Trade-Scoped)"])
            UC_Dispatch(["Dispatch & Assign Technician"])
            UC_SLA(["Monitor SLA Targets & Staff Accountability"])
            UC_Analytics(["Inspect University Heatmap & Analytics"])
            UC_Export(["Export University-Wide Audit Logs"])
        end

        Sub_Student ~~~ Sub_Shared
        Sub_Shared ~~~ Sub_Tech
        Sub_Tech ~~~ Sub_Admin
    end

    %% Human Actors OUTSIDE System Boundary (UML 2.5 Strict)
    Student["🧑‍🎓 Student<br/>(Anonymous / Token-Authenticated)"]
    Technician["🔧 Maintenance Technician<br/>(Zero-Login Staff)"]
    Provost["🏛️ Hall Provost / Caretaker<br/>(Building-Scoped Admin)"]
    HOD["📋 Maintenance HOD<br/>(Trade-Scoped Admin)"]
    Registrar["🎓 Central Registrar<br/>(Global SuperAdmin Console)"]

    %% Primary Actor Associations (Solid Lines)
    Student --- UC_Lodge
    Student --- UC_Track
    Student --- UC_Confirm
    Student --- UC_Feedback
    Student --- UC_Browse

    Technician --- UC_AccessTask
    Technician --- UC_AcceptTask
    Technician --- UC_UploadProof

    %% Governance Actor Associations (Solid Lines)
    UC_ManageHall --- Provost
    UC_Dispatch --- Provost
    UC_SLA --- Provost

    UC_ManageDept --- HOD
    UC_Dispatch --- HOD
    UC_SLA --- HOD

    UC_Analytics --- Registrar
    UC_Export --- Registrar
    UC_Dispatch --- Registrar
    UC_SLA --- Registrar

    %% UML <<include>> Dependencies (Base -.-> Included)
    UC_Lodge -.->|&laquo;include&raquo;| UC_Quota
    UC_Lodge -.->|&laquo;include&raquo;| UC_Triage
    UC_UploadProof -.->|&laquo;include&raquo;| UC_Dwell
    UC_Dispatch -.->|&laquo;include&raquo;| UC_Matcher

    %% UML <<extend>> Dependencies (Extension -.-> Base)
    UC_QR -.->|&laquo;extend&raquo;| UC_Lodge
    UC_Reopen -.->|&laquo;extend&raquo;| UC_Confirm
    UC_Upvote -.->|&laquo;extend&raquo;| UC_Browse

    %% Strict UML 2.5 Styling
    style CampusCare_System fill:#f8fafc,stroke:#0f172a,stroke-width:2px
    style Sub_Student fill:#f0fdf4,stroke:#16a34a,stroke-width:1px
    style Sub_Shared fill:#f5f3ff,stroke:#7c3aed,stroke-width:1px
    style Sub_Tech fill:#fffbeb,stroke:#d97706,stroke-width:1px
    style Sub_Admin fill:#eff6ff,stroke:#2563eb,stroke-width:1px

    style Student fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px
    style Technician fill:#fef3c7,stroke:#d97706,stroke-width:1.5px
    style Provost fill:#f3e8ff,stroke:#9333ea,stroke-width:1.5px
    style HOD fill:#fce7f3,stroke:#db2777,stroke-width:1.5px
    style Registrar fill:#dcfce7,stroke:#16a34a,stroke-width:1.5px
```

**ASCII Backup:**

```
╔═══════════════════════════════════════════════════════════════════════════════════════════════╗
║                      CAMPUSCARE SYSTEM BOUNDARY: USE CASE ARCHITECTURE                        ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════╣
║  PRIMARY ACTORS (Left)                   SYSTEM BOUNDARY USE CASES                            ║
║                                                                                               ║
║  🧑‍🎓 STUDENT ──────────────────────────► (Lodge Maintenance Complaint)                        ║
║     (Anonymous / Token-Auth)             │                                                    ║
║                                          ├──<<include>>──► (Verify Active Ticket Quota)       ║
║                                          ├──<<include>>──► (Classify ML Urgency & Spatial)    ║
║                                          ▲                                                    ║
║                                          └──<<extend>>──── (Auto-Fill Room via QR Code)       ║
║                                                                                               ║
║                                ───────► (Track Ticket Status via Hex32 Token)                 ║
║                                ───────► (Confirm Resolution & Purge Media)                    ║
║                                          ▲                                                    ║
║                                          └──<<extend>>──── (Dispute & Reopen Ticket with Proof)║
║                                ───────► (Submit Resolution Feedback & Rating)                 ║
║                                ───────► (Browse Public Issue Board & Directory)               ║
║                                          ▲                                                    ║
║                                          └──<<extend>>──── (Upvote Public Issue Support)      ║
║                                                                                               ║
║  🔧 TECHNICIAN ──────────────────────► (Access Dispatched Task via Direct UUID URL)           ║
║     (Zero-Login Staff)         ───────► (Accept Task & Transition to In-Progress)             ║
║                                ───────► (Upload Photographic Resolution Proof)                ║
║                                          └──<<include>>──► (Validate Anti-Fraud 5-Min Dwell)  ║
╠═══════════════════════════════════════════════════════════════════════════════════════════════╣
║  SECONDARY / GOVERNANCE ACTORS (Right)   ADMINISTRATIVE USE CASES                             ║
║                                                                                               ║
║  🏛️ HALL PROVOST / CARETAKER ◄─────── (Manage Hall Queue - Building Scoped)                  ║
║     (Building Scoped Admin)    ◄─────── (Dispatch & Assign Technician to Ticket)              ║
║                                          └──<<include>>──► (Suggest Optimal Staff via Matcher)║
║                                ◄─────── (Monitor SLA Targets & Staff Accountability)          ║
║                                                                                               ║
║  📋 MAINTENANCE HOD ───────────◄─────── (Manage Department Queue - Trade Scoped)              ║
║     (Trade Scoped Admin)       ◄─────── (Dispatch & Assign Technician to Ticket)              ║
║                                ◄─────── (Monitor SLA Targets & Staff Accountability)          ║
║                                                                                               ║
║  🎓 CENTRAL REGISTRAR ─────────◄─────── (Inspect University Heatmap & Spatial Analytics)      ║
║     (Global SuperAdmin)        ◄─────── (Export University-Wide Audit Logs CSV)               ║
║                                ◄─────── (Dispatch & Assign Technician to Ticket)              ║
║                                ◄─────── (Monitor SLA Targets & Staff Accountability)          ║
╚═══════════════════════════════════════════════════════════════════════════════════════════════╝
```

---

## Architectural Summary

| Diagram | Purpose | Key Insight |
|---|---|---|
| ERD | Database structure | 11 entities; self-referencing Building for hostel blocks; dual-token design on Complaint |
| State Machine | Lifecycle control | 6 states; dwell-time + proof guards on critical transitions; media purge on closure |
| Sequence | Request flow | AI triage runs inline on `Complaint.save()`; ML classification precedes ORM write |
| RBAC | Access control | ORM-level scope filtering (not template-level) prevents IDOR; 6 distinct role tiers |
| Architecture | System boundaries | Single-server monolith; local ML inference; no external API dependencies; 3-tier storage |
| Use Case | System behavior & user roles | 5 operational actor tiers; strict system boundary containment; formal `<<include>>` and `<<extend>>` semantics |

---

*End of CampusCare Architecture Diagrams*  
*Document ID: CC-ARCH-2025-v1.0 | Companion to CC-SRS-2025-v1.0*
