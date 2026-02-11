# ClearSight 2.0 RCA Dashboard - Architecture Diagrams

## 1. System Context Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         CLEARSIGHT 2.0 ECOSYSTEM                            │
│                                                                             │
│  ┌───────────────┐         ┌──────────────┐         ┌──────────────────┐  │
│  │ Forecast      │         │ ClearSight   │         │ Reference        │  │
│  │ UI (React)    │◄───────►│ Backend API  │◄───────►│ Service          │  │
│  │               │         │ (FastAPI)    │         │                  │  │
│  └───────────────┘         └──────┬───────┘         └──────────────────┘  │
│                                   │                                         │
│                                   │                                         │
│                            ┌──────▼───────┐                                │
│                            │  PostgreSQL  │                                │
│                            │  OLTP DB     │                                │
│                            │ (fc_* tables)│                                │
│                            └──────┬───────┘                                │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
                  ▼                                   ▼
    ┌─────────────────────────┐         ┌─────────────────────────┐
    │  AWS CloudWatch Logs    │         │  ETL Pipeline (Python)  │
    │  - Forecast Service     │         │  - Extractors           │
    │  - API Logs             │────────►│  - Transformers         │
    │  - Error Logs           │         │  - Loaders              │
    └─────────────────────────┘         └──────────┬──────────────┘
                                                   │
                                                   ▼
                                        ┌────────────────────┐
                                        │  PostgreSQL        │
                                        │  Reporting DB      │
                                        │  (rpt.* tables)    │
                                        │  - Fact tables     │
                                        │  - Dimensions      │
                                        └──────────┬─────────┘
                                                   │
                                                   ▼
                                        ┌────────────────────┐
                                        │  FastAPI RCA API   │
                                        │  - Audit trail     │
                                        │  - Run diagnostics │
                                        │  - Error analysis  │
                                        └──────────┬─────────┘
                                                   │
                                                   ▼
                                        ┌────────────────────┐
                                        │  Power BI          │
                                        │  RCA Dashboard     │
                                        │  (Developer Tool)  │
                                        └────────────────────┘
```

---

## 2. ETL Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            EXTRACTION PHASE                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────────┐      ┌──────────────────┐      ┌───────────────┐ │
│  │  Source DB       │      │  CloudWatch      │      │  Reference    │ │
│  │  (read-only)     │      │  Logs            │      │  Service API  │ │
│  └────────┬─────────┘      └────────┬─────────┘      └───────┬───────┘ │
│           │                         │                        │         │
│           ▼                         ▼                        ▼         │
│  ┌──────────────────┐      ┌──────────────────┐      ┌───────────────┐ │
│  │ audit_trail.py   │      │ cloudwatch.py    │      │ (future)      │ │
│  │ - State changes  │      │ - Log extraction │      │               │ │
│  │ - User actions   │      │ - Error parsing  │      │               │ │
│  │ - Input changes  │      │ - Categorization │      │               │ │
│  └────────┬─────────┘      └────────┬─────────┘      └───────┬───────┘ │
│           │                         │                        │         │
└───────────┼─────────────────────────┼────────────────────────┼─────────┘
            │                         │                        │
            └─────────────┬───────────┴────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         TRANSFORMATION PHASE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  user_journey.py                                             │        │
│  │  ┌────────────────────────────────────────────────────────┐ │        │
│  │  │  reconstruct_user_journey()                            │ │        │
│  │  │  - Merge state changes, actions, runs chronologically │ │        │
│  │  │  - Enrich with metadata                               │ │        │
│  │  └────────────────────────────────────────────────────────┘ │        │
│  │                                                              │        │
│  │  ┌────────────────────────────────────────────────────────┐ │        │
│  │  │  identify_run_context_changes()                        │ │        │
│  │  │  - Compare runs                                        │ │        │
│  │  │  - Identify input diffs                                │ │        │
│  │  │  - Find last working run                               │ │        │
│  │  └────────────────────────────────────────────────────────┘ │        │
│  │                                                              │        │
│  │  ┌────────────────────────────────────────────────────────┐ │        │
│  │  │  group_actions_by_session()                            │ │        │
│  │  │  - Detect user sessions                                │ │        │
│  │  │  - Calculate session metrics                           │ │        │
│  │  └────────────────────────────────────────────────────────┘ │        │
│  └─────────────────────────────────────────────────────────────┘        │
│                                                                          │
└───────────────────────────────────────┬──────────────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            LOADING PHASE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────┐        │
│  │  rca_loaders.py                                              │        │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐│        │
│  │  │ load_state_    │  │ load_user_     │  │ load_cloudwatch││        │
│  │  │ changes()      │  │ actions()      │  │ _logs()        ││        │
│  │  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘│        │
│  │           │                   │                   │         │        │
│  │           └───────────────────┴───────────────────┘         │        │
│  │                               │                              │        │
│  └───────────────────────────────┼──────────────────────────────┘        │
│                                  ▼                                       │
│                     ┌─────────────────────────┐                         │
│                     │  Reporting Database     │                         │
│                     │  - Batch inserts        │                         │
│                     │  - Dimension lookups    │                         │
│                     │  - Watermark updates    │                         │
│                     └─────────────────────────┘                         │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Reporting Database Schema (Star Model)

```
                    ┌─────────────────────┐
                    │    dim_date         │
                    │ ─────────────────── │
                    │ date_key (PK)       │
                    │ full_date           │
                    │ year, quarter       │
                    └─────────────────────┘
                             ▲
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────┴─────────┐  ┌───────┴─────────┐  ┌──────┴────────┐
│  dim_user       │  │  dim_scenario   │  │  dim_model    │
│ ─────────────── │  │ ─────────────── │  │ ───────────── │
│ user_key (PK)   │  │ scenario_key(PK)│  │ model_key(PK) │
│ user_id         │  │ scenario_id     │  │ model_id      │
│ display_name    │  │ scenario_name   │  │ model_name    │
└─────────────────┘  │ status          │  │ disease_area  │
                     │ model_key (FK)  │  └───────────────┘
                     └─────────────────┘
                              ▲
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        │                     │                     │
┌───────┴───────────────┐  ┌──┴──────────────────┐  ┌────────────────────┐
│ fact_scenario_run     │  │ fact_user_action    │  │ fact_cloudwatch_log│
│ ───────────────────── │  │ ─────────────────── │  │ ──────────────────│
│ run_fact_key (PK)     │  │ action_key (PK)     │  │ log_fact_key (PK)  │
│ scenario_key (FK)────►│  │ user_key (FK)       │  │ correlation_id     │
│ run_id                │  │ scenario_key (FK)   │  │ scenario_id        │
│ run_status            │  │ action_timestamp    │  │ run_id             │
│ duration_seconds      │  │ action_type         │  │ log_timestamp      │
│ node_calc_failed      │  │ correlation_id      │  │ severity           │
│ correlation_id        │  │ success             │  │ message            │
└───────────────────────┘  └─────────────────────┘  │ error_category     │
        ▲                                            │ stack_trace        │
        │                                            └────────────────────┘
        │
        │
┌───────┴────────────────────┐  ┌──────────────────────────┐
│ fact_scenario_state_change │  │ fact_run_diagnostic      │
│ ────────────────────────── │  │ ──────────────────────── │
│ state_change_key (PK)      │  │ diagnostic_key (PK)      │
│ scenario_key (FK)          │  │ run_fact_key (FK)        │
│ previous_status            │  │ scenario_key (FK)        │
│ new_status                 │  │ diagnostic_type          │
│ transition_type            │  │ severity                 │
│ changed_by_user_key (FK)   │  │ diagnostic_message       │
│ changed_at                 │  │ error_category           │
│ correlation_id             │  │ correlation_id           │
└────────────────────────────┘  └──────────────────────────┘


        ┌──────────────────────────────────────┐
        │  view_scenario_audit_trail           │
        │  (Materialized View - UNION of all)  │
        │ ──────────────────────────────────── │
        │  audit_key (PK)                      │
        │  scenario_key                        │
        │  event_timestamp                     │
        │  event_type                          │
        │  user_id                             │
        │  correlation_id                      │
        │  event_description                   │
        │  event_metadata (JSONB)              │
        └──────────────────────────────────────┘
```

---

## 4. User Journey Reconstruction Flow

```
INPUT: Scenario ID
│
├──► Extract state changes      ──┐
│                                  │
├──► Extract user actions      ───┤
│                                  ├──► Merge & Sort by Timestamp
├──► Extract input changes     ───┤
│                                  │
└──► Extract runs              ────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ Unified Timeline     │
                        │ ──────────────────── │
                        │ Event 1: Created     │
                        │ Event 2: Edit Input  │
                        │ Event 3: Run Started │
                        │ Event 4: Run Failed  │
                        │ Event 5: Edit Input  │
                        │ Event 6: Run Success │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │ Power BI Timeline    │
                        │ Visual               │
                        └──────────────────────┘
```

---

## 5. Run Comparison Logic

```
INPUT: Scenario ID, Target Run ID (failing)
│
├──► Get all runs for scenario
│    └──► Sort by run_started_at
│
├──► Find target run
│
├──► Find last successful run BEFORE target
│    │
│    └──► Filter: status = 'success' AND run_started_at < target.run_started_at
│         └──► Order by run_started_at DESC
│              └──► LIMIT 1
│
├──► Get input changes BETWEEN the two runs
│    │
│    └──► Filter: changed_at > prev_run.started_at AND changed_at <= target_run.started_at
│         └──► Group by node_id
│
└──► Return:
     ├── Previous run metadata
     ├── Target run metadata
     ├── Time gap
     ├── Input changes count
     └── List of changed node IDs
```

---

## 6. Power BI Data Flow

```
┌────────────────────────────────────────────────────────────────┐
│                        POWER BI DESKTOP                         │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │ Get Data     │────►│ Transform    │────►│ Load Model   │  │
│  │ (Web/API)    │     │ (Power Query)│     │              │  │
│  └──────┬───────┘     └──────────────┘     └──────┬───────┘  │
│         │                                          │          │
│         ▼                                          ▼          │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │  Data Model                                             │ │
│  │  ┌────────────┐   ┌────────────┐   ┌────────────────┐ │ │
│  │  │ Audit Trail│   │ Run Details│   │ Error Summary  │ │ │
│  │  │ Table      │   │ Table      │   │ Table          │ │ │
│  │  └────────────┘   └────────────┘   └────────────────┘ │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Visualizations                                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐             │  │
│  │  │ Timeline │  │ Run Hist │  │ Error    │             │  │
│  │  │ Visual   │  │ Table    │  │ Donut    │   ...more   │  │
│  │  └──────────┘  └──────────┘  └──────────┘             │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │  Filters & Slicers                                      │  │
│  │  [ Scenario ] [ Date Range ] [ User ] [ Environment ]  │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

API Endpoint Mapping:
┌────────────────────────────────┬─────────────────────────────────┐
│ Power BI Table                 │ API Endpoint                    │
├────────────────────────────────┼─────────────────────────────────┤
│ AuditTrail                     │ /rca/scenario/{id}/audit-trail  │
│ StateChanges                   │ /rca/scenario/{id}/state-changes│
│ RunDetails                     │ /rca/run/{id}/diagnostics       │
│ RunComparison                  │ /rca/scenario/{id}/run-comp...  │
│ ErrorCategories                │ /rca/errors/top-categories      │
│ UserJourney                    │ /rca/user/{id}/journey          │
└────────────────────────────────┴─────────────────────────────────┘
```

---

## 7. Error Categorization Pipeline

```
CloudWatch Log Message
│
├─► "Timeout occurred during calculation"
│   └─► Pattern Match: r"timeout|timed out"
│       └─► Category: "timeout"
│
├─► "Validation failed: Missing required field"
│   └─► Pattern Match: r"validation|invalid|missing required"
│       └─► Category: "validation"
│
├─► "Database connection failed"
│   └─► Pattern Match: r"database|sql|connection"
│       └─► Category: "database"
│
├─► "Division by zero in node calculation"
│   └─► Pattern Match: r"calculation|compute|division"
│       └─► Category: "calculation"
│
└─► "Unknown error XYZ"
    └─► No match
        └─► Category: "uncategorized"
```

---

## 8. Security & Access Control

```
┌────────────────────────────────────────────────────────────────┐
│                        ACCESS LAYERS                            │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Layer 1: Power BI Desktop (Local Developer Access)            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ - No authentication required for localhost API           │ │
│  │ - Read-only access to reporting database                 │ │
│  │ - Cannot modify source data                              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 2: FastAPI RCA Endpoints                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ - API Key authentication (dev-api-key-change-in-prod)    │ │
│  │ - Rate limiting (future)                                 │ │
│  │ - CORS restrictions (localhost only in dev)              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 3: Reporting Database                                   │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ - Separate user: reporting_user                          │ │
│  │ - SELECT-only permissions on rpt.* tables                │ │
│  │ - No write access to source (public) schema              │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 4: Source Database                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ - Read-only user: readonly_user                          │ │
│  │ - SELECT-only permissions on fc_* tables                 │ │
│  │ - Used by ETL extractors                                 │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Layer 5: CloudWatch Logs                                      │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ - AWS IAM role with logs:FilterLogEvents permission      │ │
│  │ - Restricted to specific log groups                      │ │
│  │ - Time-based access (last N days only)                   │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                 │
└────────────────────────────────────────────────────────────────┘

Data Sensitivity Handling:
┌────────────────────────────────────────────────────────────────┐
│ - PII/sensitive data: Redacted in logs (replace with ***)     │
│ - User IDs: Internal IDs only (no email/SSO in reports)       │
│ - CloudWatch: Filter out AWS credentials, API keys            │
│ - JSONB metadata: Sanitize before loading to reporting DB     │
└────────────────────────────────────────────────────────────────┘
```

---

**Document Version**: 1.0  
**Last Updated**: February 11, 2026  
**Author**: ClearSight RCA Dashboard Team
