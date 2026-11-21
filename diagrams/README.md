# CampusCare — Architectural & Design Diagrams Repository

**Standard:** IEEE 830-1998 / ISO/IEC/IEEE 29148:2018 Academic Supplement  
**Institution:** Department of Computer Science, Aligarh Muslim University (AMU), Aligarh  
**Course:** M.C.A Semester - III (CAMS-3P01: Mini Project)  
**Companion to:** [`SRS.md`](../SRS.md) & [`SRS.pdf`](../SRS.pdf)  

This directory contains the authoritative, production-grade architectural and design models for **CampusCare**, generated to match the canonical 8-figure academic sequence specified in the departmental SRS guidelines.

---

## 📐 Canonical Academic Diagram Index (Figures 3.1 – 3.8)

| Figure # | Diagram Title | Source Mermaid (`.mmd`) | High-Resolution PNG (`.png`) | Primary Architectural Focus |
|---|---|---|---|---|
| **Figure 3.1** | **High-Level System Architecture** | [`figure_3_1_architecture.mmd`](./figure_3_1_architecture.mmd) | [`figure_3_1_architecture.png`](./figure_3_1_architecture.png) | 4-tier model (Presentation, Security/Gateway, Django MVT Logic & AI Engines, Normalized 3NF Storage). |
| **Figure 3.2** | **Context Diagram (0-Level DFD)** | [`figure_3_2_context_dfd.mmd`](./figure_3_2_context_dfd.mmd) | [`figure_3_2_context_dfd.png`](./figure_3_2_context_dfd.png) | High-level system boundary and external entity interfaces across Student, Technician, Provost, HOD, and Registrar. |
| **Figure 3.3** | **Data Flow Diagram Level-1 (DFD Level-1)** | [`figure_3_3_dfd_level_1.mmd`](./figure_3_3_dfd_level_1.mmd) | [`figure_3_3_dfd_level_1.png`](./figure_3_3_dfd_level_1.png) | 6 core subsystem processes (1.0 to 6.0) interfacing with 5 persistent data stores (D1 to D5). |
| **Figure 3.3b** | **Data Flow Diagram Level-2 (DFD Level-2)** | [`figure_3_3b_dfd_level_2.mmd`](./figure_3_3b_dfd_level_2.mmd) | [`figure_3_3b_dfd_level_2.png`](./figure_3_3b_dfd_level_2.png) | Detailed functional decomposition of NLP Duplicate Triage (2.0) and Automated Worker Dispatch (3.0). |
| **Figure 3.4** | **UML 2.5 Use Case Diagram** | [`figure_3_4_use_case.mmd`](./figure_3_4_use_case.mmd) | [`figure_3_4_use_case.png`](./figure_3_4_use_case.png) | 5 operational actor tiers, formal `<<include>>` anti-fraud dwell checks, and `<<extend>>` duplicate/dispute branches. |
| **Figure 3.5** | **Activity Diagram** | [`figure_3_5_activity.mmd`](./figure_3_5_activity.mmd) | [`figure_3_5_activity.png`](./figure_3_5_activity.png) | Procedural decision logic: QR scan, NLP duplicate triage, automated dispatch, 5-min dwell timer, rating & media purge. |
| **Figure 3.6** | **UML Class Diagram** | [`figure_3_6_class_diagram.mmd`](./figure_3_6_class_diagram.mmd) | [`figure_3_6_class_diagram.png`](./figure_3_6_class_diagram.png) | 12 core domain classes with attribute types, visibility (+/-), method signatures, and structural associations. |
| **Figure 3.7** | **Entity Relationship Diagram (ERD)** | [`figure_3_7_erd.mmd`](./figure_3_7_erd.mmd) | [`figure_3_7_erd.png`](./figure_3_7_erd.png) | 3NF relational schema with primary keys, foreign keys, self-referential hall-hostel blocks, and unique constraints. |
| **Figure 3.8** | **Sequence Diagram** | [`figure_3_8_sequence.mmd`](./figure_3_8_sequence.mmd) | [`figure_3_8_sequence.png`](./figure_3_8_sequence.png) | End-to-end chronological message flows across Anonymous Reporting, AI Triage, Dispatch, Anti-Fraud Execution & Verification. |

---

## 🛠️ Additional Architecture Supplements

- [`State_machine.png`](./State_machine.png) / [`diagram_2_state_machine.mmd`](./diagram_2_state_machine.mmd): Complaint Lifecycle State Machine (6 states: `OPEN` &rarr; `ASSIGNED` &rarr; `IN_PROGRESS` &rarr; `RESOLVED` &rarr; `CLOSED` / `DISPUTED`).
- [`RBAC.png`](./RBAC.png) / [`diagram_4_rbac.mmd`](./diagram_4_rbac.mmd): Row-Level Multi-Tenant RBAC Layered Scoping Architecture.
