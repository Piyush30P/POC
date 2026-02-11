# ClearSight 2.0 Scenario Audit & RCA Dashboard

## 📋 Overview

The **Scenario Audit & RCA Dashboard** is a developer-facing Power BI solution that reconstructs the complete audit trail of ClearSight forecast scenarios, enabling faster and more consistent root cause analysis (RCA) when debugging forecast issues.

### **Problem Solved**

- **Before**: Diagnostic data fragmented across Postgres tables and CloudWatch logs; RCA required manual SQL queries and log digging
- **After**: Centralized view of scenario lifecycle, user actions, input changes, run diagnostics, and error logs—all correlated by scenario/run/user

---

## 🎯 Key Capabilities

| Capability                       | Description                                                    | Power BI Use Case                              |
| -------------------------------- | -------------------------------------------------------------- | ---------------------------------------------- |
| **Scenario Lifecycle View**      | Complete state transition history (draft → submitted → locked) | Timeline visual showing scenario evolution     |
| **User Journey Reconstruction**  | Chronological view of all user actions per scenario            | "What did the user do before the error?"       |
| **Run Context Comparison**       | Compare last working run vs first failing run                  | Identify exactly what changed between runs     |
| **Integrated Error Diagnostics** | CloudWatch logs linked to scenarios/runs/nodes                 | Drill from error → scenario → user actions     |
| **Error Aggregation**            | Top error categories, recurring patterns, problematic nodes    | Reliability metrics and hotspot identification |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ClearSight OLTP Database                      │
│  Tables: fc_scenario, fc_scenario_node_data, fc_scenario_run   │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (ETL Extract)
┌─────────────────────────────────────────────────────────────────┐
│                   ETL Pipeline (Python/FastAPI)                  │
│  • Extract: Source DB + CloudWatch logs (boto3)                │
│  • Transform: User journey reconstruction, run comparison      │
│  • Load: Reporting DB (star schema)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (Reporting Schema)
┌─────────────────────────────────────────────────────────────────┐
│                  Reporting Database (rpt schema)                 │
│                                                                  │
│  DIMENSION TABLES:                                              │
│  • dim_scenario     • dim_user        • dim_node               │
│  • dim_model        • dim_date        • dim_event_type         │
│                                                                  │
│  FACT TABLES:                                                   │
│  • fact_scenario_run           - Run metadata & metrics        │
│  • fact_scenario_state_change  - Lifecycle transitions         │
│  • fact_user_action             - All user actions             │
│  • fact_scenario_input_change  - Input modifications           │
│  • fact_cloudwatch_log         - Integrated logs               │
│  • fact_run_diagnostic         - Run-specific diagnostics      │
│  • fact_run_comparison         - Run delta analysis            │
│                                                                  │
│  VIEW:                                                          │
│  • view_scenario_audit_trail   - Unified timeline              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (FastAPI REST)
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI RCA API Endpoints                      │
│  GET /api/v1/rca/scenario/{id}/audit-trail                     │
│  GET /api/v1/rca/scenario/{id}/state-changes                   │
│  GET /api/v1/rca/user/{id}/journey                             │
│  GET /api/v1/rca/run/{id}/diagnostics                          │
│  GET /api/v1/rca/scenario/{id}/run-comparison                  │
│  GET /api/v1/rca/errors/top-categories                         │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼ (Power BI Connector)
┌─────────────────────────────────────────────────────────────────┐
│                       Power BI Dashboard                         │
│  • Scenario Overview Page                                       │
│  • User Journey Timeline                                        │
│  • Run Diagnostics Drill-Through                                │
│  • Error Hotspot Analysis                                       │
│  • Run Comparison View                                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model

### **Star Schema Design**

#### **Dimension Tables**

| Table            | Purpose                    | Key Attributes                               |
| ---------------- | -------------------------- | -------------------------------------------- |
| `dim_scenario`   | Scenario master data       | scenario_id, name, status, created_by, model |
| `dim_user`       | User master data           | user_id, display_name                        |
| `dim_model`      | Forecast model definitions | model_id, therapeutic_area, disease_area     |
| `dim_node`       | Node definitions           | node_id, node_name, node_type, flow          |
| `dim_date`       | Time dimension             | date_key, year, quarter, month, week         |
| `dim_event_type` | Event type lookup          | Fair Share, Explicit, Derived, LoE           |

#### **Fact Tables (Core)**

**1. fact_scenario_run**

```sql
-- Stores each forecast run with metrics
run_fact_key (PK)
scenario_key (FK → dim_scenario)
run_id (UUID from source)
run_status (success/failed/timeout)
run_started_at, run_ended_at
duration_seconds
node_calc_success, node_calc_failed
fail_reason
correlation_id (for log linking)
```

**2. fact_scenario_state_change**

```sql
-- Tracks scenario lifecycle transitions
state_change_key (PK)
scenario_key (FK)
previous_status, new_status
transition_type (created/submitted/locked/withdrawn)
changed_by_user_key (FK → dim_user)
changed_at
correlation_id
```

**3. fact_user_action**

```sql
-- All user actions chronologically
action_key (PK)
user_key (FK → dim_user)
scenario_key (FK → dim_scenario)
action_timestamp
action_type (create_scenario, edit_input, run_forecast, submit)
action_category (scenario_mgmt, input_data, forecast_run)
target_entity_type, target_entity_id
correlation_id
success (boolean)
error_message
action_details (JSONB - before/after snapshots)
```

**4. fact_scenario_input_change**

```sql
-- Input data modifications
input_change_key (PK)
scenario_key (FK), node_key (FK)
changed_by_user_key (FK)
changed_at
previous_input_hash, new_input_hash
change_sequence (per-node counter)
run_id_before, run_id_after
input_diff_summary (JSONB)
```

**5. fact_cloudwatch_log**

```sql
-- CloudWatch logs integrated with correlation IDs
log_fact_key (PK)
log_timestamp
severity (INFO/WARN/ERROR)
message, stack_trace
correlation_id, scenario_id, run_id
user_id
environment (dev/sit/uat/prod)
error_category (validation/calculation/timeout/database)
metadata (JSONB)
```

**6. fact_run_diagnostic**

```sql
-- Detailed run diagnostics
diagnostic_key (PK)
run_fact_key (FK → fact_scenario_run)
run_id, scenario_key, node_key
diagnostic_type (input_snapshot/error_summary/perf_metric)
severity (critical/major/minor/info)
diagnostic_category (data_validation/calculation_error/timeout)
diagnostic_message
diagnostic_details (JSONB)
input_hash_at_run
cloudwatch_log_references (array of log_fact_keys)
```

#### **Materialized View**

**view_scenario_audit_trail**

```sql
-- Unified chronological timeline for a scenario
SELECT
    scenario_key,
    event_timestamp,
    event_type, -- state_change, input_change, run_started, run_completed
    event_category,
    user_id,
    correlation_id,
    event_description,
    event_metadata (JSONB)
FROM (
    UNION of state_changes, input_changes, runs, user_actions
)
ORDER BY event_timestamp
```

---

## 🔧 ETL Pipeline

### **Extraction**

#### **Source Database Extractors**

| Extractor                          | Source Tables                                                  | Key Filters                                                 |
| ---------------------------------- | -------------------------------------------------------------- | ----------------------------------------------------------- |
| `extract_scenario_state_changes()` | fc_scenario                                                    | created_at, submitted_at, locked_at, withdraw_at, delete_at |
| `extract_user_actions()`           | fc_scenario, fc_scenario_node_data, fc_scenario_run            | user_id, scenario_id, timestamp                             |
| `extract_input_change_sequence()`  | fc_scenario_node_data                                          | scenario_id, created_at (ordered)                           |
| `extract_runs()`                   | fc_scenario_run, fc_scenario_run_branch, fc_scenario_node_calc | run_id, scenario_id                                         |

#### **CloudWatch Extractor**

**`CloudWatchExtractor` class** (`src/etl/extractors/cloudwatch.py`)

```python
extractor = CloudWatchExtractor(
    log_group="/aws/lambda/forecast-service",
    region="us-east-1",
    profile="clearsight-dev"
)

logs = extractor.extract_logs(
    start_time=datetime(2026, 2, 1),
    end_time=datetime(2026, 2, 11),
    correlation_ids=["abc-123", "def-456"],
    severity_levels=["ERROR", "WARN"],
    limit=10000
)
```

**Features**:

- Uses CloudWatch Insights queries
- Filters by correlation_id, scenario_id, run_id
- Automatic error categorization (validation, timeout, database, calculation)
- Normalizes logs to reporting schema

### **Transformation**

**User Journey Reconstruction** (`src/etl/transformers/user_journey.py`)

```python
# Merge all audit events into chronological timeline
timeline = reconstruct_user_journey(
    state_changes=state_changes,
    user_actions=user_actions,
    input_changes=input_changes,
    runs=runs
)

# Identify what changed between runs
context = identify_run_context_changes(
    scenario_id=scenario_id,
    target_run_id=failing_run_id,
    all_runs=runs,
    input_changes=input_changes
)
# Returns: previous_successful_run, input_changes_between, changed_node_ids
```

**Key Functions**:

- `reconstruct_user_journey()` - Unified timeline
- `identify_run_context_changes()` - Run delta analysis
- `group_actions_by_session()` - Logical session grouping
- `calculate_user_velocity_metrics()` - User activity patterns

### **Loading**

**RCA Loaders** (`src/etl/loaders/rca_loaders.py`)

```python
from src.etl.loaders.rca_loaders import (
    load_cloudwatch_logs,
    load_state_changes,
    load_user_actions,
    load_run_diagnostics,
)

# Load CloudWatch logs
count = load_cloudwatch_logs(
    reporting_session=session,
    logs=extracted_logs,
    log_group="/aws/lambda/forecast-service",
    environment="prod",
)

# Load state changes
count = load_state_changes(
    reporting_session=session,
    state_changes=extracted_changes,
)
```

**Features**:

- Batch inserts (1000 records per commit)
- Automatic dimension key lookups with caching
- Creates missing users on-the-fly

---

## 🔌 API Endpoints

### **Base URL**: `/api/v1/rca`

#### **1. Scenario Audit Trail**

```http
GET /api/v1/rca/scenario/{scenario_id}/audit-trail
Query Params:
  - start_date: datetime (optional)
  - end_date: datetime (optional)
  - event_types: list[str] (optional) - Filter by event type

Response:
{
  "scenario_id": "uuid",
  "event_count": 45,
  "events": [
    {
      "timestamp": "2026-02-11T10:30:00Z",
      "event_type": "state_change",
      "category": "scenario_mgmt",
      "user": "john.doe",
      "description": "Scenario status changed from draft to submitted",
      "correlation_id": "uuid",
      "metadata": {...}
    },
    ...
  ]
}
```

**Power BI Usage**: Main data source for timeline visual.

---

#### **2. State Changes**

```http
GET /api/v1/rca/scenario/{scenario_id}/state-changes

Response:
{
  "scenario_id": "uuid",
  "state_changes": [
    {
      "previous_status": null,
      "new_status": "draft",
      "transition_type": "created",
      "changed_by": "jane.smith",
      "changed_at": "2026-02-05T14:00:00Z",
      "correlation_id": "uuid"
    }
  ]
}
```

---

#### **3. User Journey**

```http
GET /api/v1/rca/user/{user_id}/journey?days=30&scenario_id=uuid

Response:
{
  "user_id": "john.doe",
  "days_analyzed": 30,
  "action_count": 127,
  "actions": [
    {
      "timestamp": "2026-02-11T09:15:00Z",
      "action_type": "edit_input_data",
      "category": "input_data",
      "target_entity": "node_data",
      "success": true,
      "duration_ms": 245.5,
      "details": {...}
    }
  ]
}
```

---

#### **4. Run Diagnostics**

```http
GET /api/v1/rca/run/{run_id}/diagnostics

Response:
{
  "run_id": "uuid",
  "run_status": "failed",
  "started_at": "2026-02-11T11:00:00Z",
  "ended_at": "2026-02-11T11:05:30Z",
  "duration_seconds": 330,
  "fail_reason": "Node calculation timeout",
  "diagnostics": [
    {
      "type": "error_summary",
      "category": "timeout",
      "severity": "critical",
      "node_name": "Treatment Share - Drug A",
      "message": "Calculation exceeded 60s timeout",
      "details": {...}
    }
  ],
  "cloudwatch_logs": [
    {
      "timestamp": "2026-02-11T11:05:00Z",
      "severity": "ERROR",
      "message": "Calculation timeout in treatment node...",
      "error_category": "timeout",
      "stack_trace": true
    }
  ]
}
```

---

#### **5. Run Comparison**

```http
GET /api/v1/rca/scenario/{scenario_id}/run-comparison?run_a_id=uuid&run_b_id=uuid

Response:
{
  "scenario_id": "uuid",
  "run_a": {
    "run_id": "uuid",
    "status": "success",
    "started_at": "2026-02-10T14:00:00Z",
    "duration_seconds": 180,
    "node_failures": 0
  },
  "run_b": {
    "run_id": "uuid",
    "status": "failed",
    "started_at": "2026-02-11T11:00:00Z",
    "duration_seconds": 330,
    "node_failures": 3
  },
  "time_gap_seconds": 75600,
  "input_changes_between": 5,
  "changed_nodes": [
    {
      "node_name": "Market Share Input",
      "changed_at": "2026-02-11T10:30:00Z",
      "input_hash": "abc123..."
    }
  ]
}
```

**Power BI Usage**: "Last working vs first failing" comparison.

---

#### **6. Error Aggregation**

```http
GET /api/v1/rca/errors/top-categories?days=30&limit=10

Response:
{
  "days_analyzed": 30,
  "top_categories": [
    {"category": "calculation", "count": 45},
    {"category": "timeout", "count": 32},
    {"category": "validation", "count": 18}
  ]
}
```

---

## 📈 Power BI Dashboard Design

### **Page 1: Scenario Overview**

**Visuals**:

1. **Scenario Card** - Name, status, created by, created date
2. **Run History Table** - All runs (status, duration, failures, timestamp)
3. **Error Summary Donut Chart** - Error category distribution
4. **Timeline Visual** - All audit events chronologically

**Filters**:

- Scenario selector (dropdown)
- Date range
- Environment (dev/sit/uat/prod)

**Drill-Through**: Click run → Run Diagnostics page

---

### **Page 2: User Journey Timeline**

**Visuals**:

1. **Timeline (Gantt/Scatter)** - User actions over time
   - X-axis: Timestamp
   - Y-axis: Action type
   - Color: Success/failure
   - Tooltip: Action details, correlation ID
2. **User Activity Metrics** - Actions/day, scenarios touched, most common action
3. **Session Summary Table** - Logical sessions (start, end, action count)

**Filters**:

- User selector
- Scenario selector
- Action category

**Data Source**: `/api/v1/rca/user/{user_id}/journey`

---

### **Page 3: Run Diagnostics (Drill-Through)**

**Triggered From**: Run History table (click run row)

**Visuals**:

1. **Run Metadata Card** - Status, duration, start/end time
2. **Input Snapshot** - State of inputs at run time (table)
3. **Error Logs Table** - CloudWatch logs for this run
   - Columns: Timestamp, Severity, Message, Category, Stack Trace
4. **Node Failures** - Which nodes failed (bar chart)
5. **Diagnostic Details** - Expandable diagnostic messages

**Data Source**: `/api/v1/rca/run/{run_id}/diagnostics`

---

### **Page 4: Run Comparison**

**Purpose**: Compare last working vs first failing run

**Visuals**:

1. **Side-by-Side Run Cards** - Run A vs Run B metadata
2. **Input Diff Table** - Changed nodes between runs
   - Columns: Node name, Previous hash, New hash, Changed at, Changed by
3. **Metrics Delta** - Duration delta, failure delta
4. **Timeline Gap Visual** - Show time between runs with input changes annotated

**Data Source**: `/api/v1/rca/scenario/{scenario_id}/run-comparison`

---

### **Page 5: Reliability Insights**

**Visuals**:

1. **Error Category Distribution** - Pie chart (calculation, timeout, validation, etc.)
2. **Top Failing Nodes** - Bar chart (node name, failure count)
3. **Daily Run Success Rate** - Line chart over time
4. **Recurring Error Patterns** - Table (error message, occurrence count, affected scenarios)

**Filters**:

- Therapeutic area
- Disease area
- Time range
- Severity (critical/major/minor)

**Data Source**: `/api/v1/rca/errors/top-categories`

---

## 🚀 Setup & Deployment

### **Prerequisites**

- Python 3.11+
- PostgreSQL 14+
- AWS CLI configured (for CloudWatch access)
- Power BI Desktop

### **Installation**

```bash
# 1. Clone repository
git clone <repo-url>
cd POC

# 2. Install dependencies
pip install -e .
pip install boto3  # For CloudWatch integration

# 3. Configure environment
cp .env.example .env
# Edit .env with database credentials and AWS settings

# 4. Run migrations
alembic upgrade head

# 5. Start API server
python -m uvicorn src.api.main:app --reload --port 8000
```

### **ETL Pipeline Execution**

```bash
# Run full ETL load
python scripts/run_rca_etl.py --full

# Run incremental load (last 24 hours)
python scripts/run_rca_etl.py --incremental

# Load CloudWatch logs only
python scripts/load_cloudwatch_logs.py --days 7 --environment prod
```

### **Power BI Connection**

1. Open Power BI Desktop
2. Get Data → Web
3. Enter API endpoint: `http://localhost:8000/api/v1/rca/scenario/{scenario_id}/audit-trail`
4. Authentication: None (or add API key header)
5. Transform data as needed
6. Create visuals

---

## 📚 Usage Examples

### **Example 1: Debug a Failed Run**

**Scenario**: Run failed with "timeout" error. Need to understand why.

**Steps**:

1. **Power BI**: Open "Scenario Overview" page, select scenario
2. **Identify**: See run history, click failing run
3. **Drill-Through**: Automatically opens "Run Diagnostics" page
4. **Analyze**:
   - Check CloudWatch logs for timeout errors
   - Review node failures (which node timed out?)
   - Check diagnostic details (input values causing timeout?)
5. **Compare**: Switch to "Run Comparison" page
   - Select last successful run vs this failing run
   - See input diff table → identify changed node inputs
6. **Conclusion**: User changed market share input from 10% to 90%, causing calculation overflow

**Time Saved**: 10 minutes vs 1+ hour of manual SQL/log searching

---

### **Example 2: Track User Session**

**Scenario**: User reports "submitted scenario but it disappeared."

**Steps**:

1. **Power BI**: "User Journey Timeline" page
2. **Filter**: Select user, date range
3. **Review Timeline**: See all actions chronologically
   - 10:00 - Created scenario
   - 10:15 - Edited input data (5 nodes)
   - 10:30 - Submitted scenario
   - 10:35 - **Withdrew scenario** (aha!)
4. **Conclusion**: User accidentally withdrew instead of locking

---

### **Example 3: Recurring Error Pattern**

**Scenario**: Multiple scenarios failing with "validation" errors.

**Steps**:

1. **Power BI**: "Reliability Insights" page
2. **Filter**: Error category = "validation", Last 30 days
3. **Visuals**:
   - See "validation" is #2 most common error (32 occurrences)
   - Top failing node: "Treatment Duration" (18 failures)
   - Error message: "Duration must be between 1-120 months"
4. **Drill**: Click error row → See affected scenarios
5. **Conclusion**: Input constraint not clear in UI, users entering 0 or 999

**Action**: Update UI validation and user documentation

---

## 🎯 Success Metrics (OKRs)

### **Objective 1**: Build working RCA dashboard prototype

**KR1**: Extract core data from Postgres and CloudWatch into reporting layer

- ✅ Implemented: Source extractors, CloudWatch extractor, transformers, loaders

**KR2**: Create Power BI dashboard with scenario overview, run history, user journey

- 📋 Deliverable: 5 dashboard pages with documented visuals and filters

---

### **Objective 2**: Enable basic debugging for developers

**KR1**: Reconstruct user journey for 3 sample issues using only dashboard

- 🎯 Target: Successfully debug failed run, missing scenario, recurring error

**KR2**: Reduce RCA time to <10 minutes for sample issues

- 🎯 Baseline: 60+ minutes (manual SQL + log searching)
- 🎯 Target: <10 minutes (dashboard-driven)

---

### **Objective 3**: Ensure maintainability

**KR1**: Deliver clear documentation for architecture, data flows, usage

- ✅ This document

**KR2**: Conduct demo and handover session with dev team

- 📅 Scheduled: End of internship

---

## 📖 Developer Guide

### **Adding a New Fact Table**

1. **Define model** in `src/models/reporting.py`:

```python
class FactNewMetric(ReportingBase):
    __tablename__ = "fact_new_metric"

    metric_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_key: Mapped[int] = mapped_column(Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"))
    metric_value: Mapped[float] = mapped_column(Numeric(10, 2))
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

2. **Create extractor** in `src/etl/extractors/`:

```python
def extract_new_metric(session: Session) -> Iterator[dict]:
    # Query source database
    ...
    yield {"scenario_id": ..., "metric_value": ...}
```

3. **Create loader** in `src/etl/loaders/`:

```python
def load_new_metric(reporting_session: Session, metrics: Iterable[dict]) -> int:
    # Insert into fact table
    ...
```

4. **Add Alembic migration**:

```bash
alembic revision --autogenerate -m "Add fact_new_metric table"
alembic upgrade head
```

5. **Add API endpoint** in `src/api/v1/rca.py`:

```python
@router.get("/metrics/new")
async def get_new_metrics(...):
    ...
```

---

### **Extending CloudWatch Extraction**

**Add custom log parsing**:

```python
# src/etl/extractors/cloudwatch.py

@staticmethod
def _categorize_error(message: str) -> str | None:
    # Add new pattern
    if re.search(r"custom pattern", message.lower()):
        return "custom_category"
    ...
```

**Add new filter**:

```python
def extract_logs(
    self,
    ...,
    custom_filter: str | None = None,  # New parameter
):
    query = self._build_query(..., custom_filter=custom_filter)
    ...
```

---

## 🐛 Troubleshooting

### **Issue**: CloudWatch logs not loading

**Symptoms**: `fact_cloudwatch_log` table empty

**Solutions**:

1. Check AWS credentials: `aws sts get-caller-identity`
2. Verify log group exists: `aws logs describe-log-groups`
3. Check time range (CloudWatch has retention limits)
4. Enable debug logging in extractor

---

### **Issue**: Scenario not appearing in dashboard

**Symptoms**: Scenario exists in source DB but not in `dim_scenario`

**Solutions**:

1. Run full ETL: `python scripts/run_rca_etl.py --full`
2. Check `etl_watermark` table for errors
3. Verify scenario was created after last ETL run
4. Check scenario status (deleted scenarios excluded)

---

### **Issue**: Slow API response times

**Symptoms**: Power BI refresh takes >5 minutes

**Solutions**:

1. Add indexes to fact tables (correlation_id, scenario_id, run_id)
2. Reduce date range in Power BI filter
3. Use incremental refresh in Power BI
4. Check `pg_stat_statements` for slow queries

---

## 📞 Support & Contact

**Project Owner**: [Your Name]  
**Team**: ClearSight Development Team  
**Slack Channel**: `#clearsight-rca-dashboard`  
**Documentation**: This file + inline code comments

---

## 📄 License

Internal Merck/MSD project. For internal use only.

---

**Last Updated**: February 11, 2026  
**Version**: 0.1.0 (Prototype)
