# ClearSight 2.0 - Scenario Audit & RCA Dashboard
## Solution Documentation

**Version:** 1.0  
**Date:** February 2026  
**Project:** Internship Assignment - DevOps/DataOps Analytics Dashboard  
**Author:** Jarvis  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Architecture Design](#4-architecture-design)
5. [Technical Components](#5-technical-components)
6. [Data Model](#6-data-model)
7. [ETL Implementation](#7-etl-implementation)
8. [Power BI Dashboard](#8-power-bi-dashboard)
9. [Implementation Plan](#9-implementation-plan)
10. [Operations & Maintenance](#10-operations--maintenance)
11. [Success Metrics](#11-success-metrics)
12. [Risks & Mitigation](#12-risks--mitigation)
13. [Appendices](#13-appendices)

---

## 1. Executive Summary

### 1.1 Project Overview
The ClearSight 2.0 Scenario Audit & RCA Dashboard is a developer-facing analytics solution designed to accelerate root cause analysis (RCA) and debugging of forecasting scenarios. The dashboard consolidates fragmented diagnostic data from PostgreSQL tables into a unified, interactive Power BI interface.

### 1.2 Business Value
- **Reduced RCA Time:** From hours to <10 minutes per incident
- **Developer Efficiency:** Eliminates manual SQL queries and log searching
- **Improved Reliability:** Identifies recurring error patterns and problematic configurations
- **Better User Support:** Enables data-backed feedback to users and product teams

### 1.3 Key Features
- Complete scenario lifecycle reconstruction (create → modify → run → error/success)
- User journey timeline with chronological action tracking
- Input state snapshots at any point in time
- Side-by-side run comparison with input diff analysis
- Node-level error diagnostics

### 1.4 Technical Approach
- **Read-only access** to production database (no schema changes)
- **Python ETL** extracts events every 15 minutes
- **Star schema** reporting layer optimized for Power BI
- **4 interactive dashboards** for comprehensive analysis

---

## 2. Problem Statement

### 2.1 Current Challenges

#### Fragmented Data
- Scenario metadata in `fc_scenario` table
- Run history in `fc_scenario_run` table  
- Input changes across multiple versions in `fc_scenario_node_data`
- Calculation results in `fc_scenario_node_calc`
- Error messages scattered in `fail_reason` columns

#### Manual Debugging Process
1. Developer receives bug report: "Scenario ABC failed"
2. Write ad-hoc SQL to find scenario ID
3. Query run history to find failed run
4. Manually reconstruct input state at time of failure
5. Compare with last successful run (more queries)
6. Search for error patterns across similar scenarios
7. **Total time: 30-60 minutes per issue**

#### No Standardized View
- Different developers use different SQL queries
- Inconsistent approaches to RCA
- Knowledge not shared across team
- Difficult to identify recurring issues

### 2.2 Impact on Development Team
- **Time Waste:** ~20% of developer time spent on debugging
- **Context Switching:** Interruptions for user support issues
- **Missed Patterns:** No aggregated view to spot systemic problems
- **Slow Iteration:** Cannot quickly validate fixes

---

## 3. Solution Overview

### 3.1 High-Level Approach

The solution implements a **reporting layer** that sits alongside the production database, extracting and transforming diagnostic data into an analytics-friendly format.

```
Production DB (READ-ONLY) → Python ETL → Reporting Schema → Power BI
```

### 3.2 Core Principles

1. **Non-Invasive:** Zero changes to production database schema
2. **Automated:** Scheduled ETL eliminates manual data gathering
3. **Performant:** Star schema enables sub-second Power BI queries
4. **Maintainable:** Clear separation of concerns, well-documented

### 3.3 Data Flow

```
1. Every 15 minutes (or hourly):
   - Python ETL script wakes up
   - Queries production tables for new/updated records
   - Transforms data into event stream
   - Loads into reporting schema

2. Power BI refreshes on schedule:
   - Imports from reporting schema
   - Users see updated data within 15 minutes

3. Developer workflow:
   - Opens Power BI dashboard
   - Filters by scenario ID or time range
   - Views complete audit trail in seconds
   - Identifies root cause without SQL
```

### 3.4 User Experience

**Before:**
```
User: "My scenario failed, can you help?"
Dev: "Let me check... [writes 5 SQL queries]... 
      [30 minutes later]... I found the issue"
```

**After:**
```
User: "My scenario failed, can you help?"
Dev: [Opens Power BI, filters by scenario]
     "I can see the problem - you changed the growth rate 
      which made the validation fail. Here's the exact error."
     [Total time: 2 minutes]
```

---

## 4. Architecture Design

### 4.1 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL (Production Database)                │
│  Tables: fc_scenario, fc_scenario_run,                  │
│          fc_scenario_node_data, fc_scenario_node_calc   │
│  Access: READ-ONLY                                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ SQL Queries
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Python ETL Script                          │
│  - FastAPI framework                                    │
│  - SQLAlchemy for database access                       │
│  - EXTRACT: Query production tables                     │
│  - TRANSFORM: Normalize events, detect changes          │
│  - LOAD: Upsert to reporting schema                     │
│                                                         │
│  Scheduler: APScheduler (every 15 min)                 │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ INSERT/UPSERT
                     ▼
┌─────────────────────────────────────────────────────────┐
│         PostgreSQL - Reporting Schema                   │
│  Star Schema:                                           │
│    Dimensions: dim_scenario, dim_user, dim_node,       │
│                dim_run                                  │
│    Facts: fact_scenario_events,                        │
│           fact_input_changes,                          │
│           fact_node_calculations                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ DirectQuery / Import Mode
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Power BI Dashboard                         │
│  Page 1: Scenario Overview                             │
│  Page 2: Event Timeline & User Journey                 │
│  Page 3: Run History & Comparison                      │
│  Page 4: Error Analysis & RCA                          │
│                                                         │
│  Refresh Schedule: Hourly                              │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **Production DB** | Source of truth for all ClearSight data | PostgreSQL |
| **ETL Script** | Extract, transform, and load diagnostic events | Python 3.11+, FastAPI, SQLAlchemy |
| **Reporting Schema** | Analytics-optimized storage with star schema | PostgreSQL (same instance) |
| **Scheduler** | Trigger ETL at regular intervals | APScheduler / Cron |
| **Power BI** | Interactive visualization and exploration | Power BI Desktop + Service |

### 4.3 Network & Security

- **Database Access:** Read-only credentials for ETL
- **Reporting Schema:** Separate schema (`reporting`) in same database
- **Power BI Gateway:** On-premises gateway for scheduled refresh
- **Data Sensitivity:** No PII in reporting layer; audit fields only

---

## 5. Technical Components

### 5.1 Source Database (PostgreSQL)

#### Core Tables Used

**fc_scenario**
- Purpose: Scenario lifecycle tracking
- Key Fields: `id`, `status`, `created_at`, `created_by`, `submitted_at`, `locked_at`, `updated_at`
- Audit Trail: Complete history of status changes with timestamps and users

**fc_scenario_run**
- Purpose: Forecast run execution tracking
- Key Fields: `id`, `scenario_id`, `run_status`, `run_at`, `run_complete_at`, `fail_reason`
- Provides: Success/failure status and error messages

**fc_scenario_node_data**
- Purpose: Input data with version history (append-only)
- Key Fields: `id`, `scenario_id`, `model_node_id`, `input_data`, `input_hash`, `created_at`, `end_at`
- Change Detection: Hash-based comparison for identifying modifications

**fc_scenario_node_calc**
- Purpose: Node-level calculation results
- Key Fields: `id`, `run_id`, `model_node_id`, `status`, `fail_reason`, `processing_duration`
- Diagnostics: Pinpoints which nodes failed in a run

**fc_model_node**
- Purpose: Node definitions and metadata
- Key Fields: `id`, `node_display_name`, `node_type`, `model_id`
- Usage: Translate node IDs to human-readable names

### 5.2 ETL Layer (Python)

#### Technology Stack
```
Python 3.11+
├── FastAPI (Web framework)
├── SQLAlchemy (ORM)
├── psycopg2-binary (PostgreSQL driver)
├── APScheduler (Job scheduling)
└── pydantic (Data validation)
```

#### Key Functions

**1. Event Extraction**
```python
def extract_scenario_events(since_date):
    """Extract all scenario lifecycle events"""
    # Query fc_scenario for created, submitted, locked events
    # Return list of event dictionaries
```

**2. Input Change Detection**
```python
def extract_input_changes(since_date):
    """Detect changes using hash comparison"""
    # Query fc_scenario_node_data with LAG window function
    # Compare input_hash values
    # Return only changed records
```

**3. Run Event Extraction**
```python
def extract_run_events(since_date):
    """Extract run start/complete/failure events"""
    # Query fc_scenario_run
    # Calculate duration
    # Return structured events
```

**4. Data Loading**
```python
def load_events(events, target_table):
    """Upsert events into reporting tables"""
    # Use INSERT ... ON CONFLICT DO UPDATE
    # Handle idempotency
```

#### Scheduling Strategy

**Incremental ETL (Every 15 minutes)**
```python
# Extract only records modified in last 15 minutes
since_time = datetime.now() - timedelta(minutes=15)
events = extract_events_since(since_time)
load_events(events)
```

**Full Refresh (Daily)**
```python
# Reload entire dataset for consistency
# Run at 2 AM when system load is low
since_date = datetime.now() - timedelta(days=30)
events = extract_events_since(since_date)
truncate_and_reload(events)
```

### 5.3 Reporting Layer (PostgreSQL Schema)

#### Star Schema Design

**Dimension Tables (Descriptive Context)**
```
dim_scenario → Scenario metadata
dim_user → User information
dim_node → Node definitions
dim_run → Run summary with aggregates
```

**Fact Tables (Events & Metrics)**
```
fact_scenario_events → All events chronologically
fact_input_changes → Input modification history
fact_node_calculations → Node-level results
```

#### Benefits of Star Schema
1. **Fast Aggregations:** Dimension filtering → Fact scanning
2. **Easy Joins:** Single-level relationships (no snowflaking)
3. **Power BI Optimized:** Natural fit for DAX measures
4. **Query Performance:** Pre-aggregated dimensions reduce compute

---

## 6. Data Model

### 6.1 Reporting Schema DDL

```sql
-- ============================================
-- DIMENSION TABLES
-- ============================================

CREATE TABLE reporting.dim_scenario (
    scenario_id UUID PRIMARY KEY,
    scenario_name VARCHAR(255),
    scenario_status VARCHAR(50),
    model_id UUID,
    model_name VARCHAR(255),
    model_disease_area VARCHAR(255),
    therapeutic_area VARCHAR(255),
    forecast_init_id UUID,
    scenario_region VARCHAR(255),
    scenario_country VARCHAR(255),
    created_at TIMESTAMP,
    created_by VARCHAR(255),
    submitted_at TIMESTAMP,
    locked_at TIMESTAMP,
    is_starter BOOLEAN,
    etl_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reporting.dim_user (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255),
    first_seen_at TIMESTAMP,
    last_seen_at TIMESTAMP,
    etl_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reporting.dim_node (
    node_id UUID PRIMARY KEY,
    node_name VARCHAR(255),
    node_type VARCHAR(255),
    model_id UUID,
    node_group_name VARCHAR(255),
    node_seq INTEGER,
    etl_loaded_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE reporting.dim_run (
    run_id UUID PRIMARY KEY,
    scenario_id UUID,
    run_status VARCHAR(50),
    run_at TIMESTAMP,
    run_complete_at TIMESTAMP,
    duration_seconds NUMERIC,
    run_by VARCHAR(255),
    fail_reason TEXT,
    total_nodes INTEGER,
    nodes_succeeded INTEGER,
    nodes_failed INTEGER,
    etl_loaded_at TIMESTAMP DEFAULT NOW()
);

-- ============================================
-- FACT TABLES
-- ============================================

CREATE TABLE reporting.fact_scenario_events (
    event_id BIGSERIAL PRIMARY KEY,
    scenario_id UUID NOT NULL,
    event_user VARCHAR(255),
    node_id UUID,
    run_id UUID,
    event_type VARCHAR(50) NOT NULL,
    event_timestamp TIMESTAMP NOT NULL,
    event_description TEXT,
    request_id UUID,
    event_details JSONB,
    etl_loaded_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_scenario FOREIGN KEY (scenario_id) 
        REFERENCES reporting.dim_scenario(scenario_id),
    CONSTRAINT fk_user FOREIGN KEY (event_user) 
        REFERENCES reporting.dim_user(user_id),
    CONSTRAINT fk_node FOREIGN KEY (node_id) 
        REFERENCES reporting.dim_node(node_id),
    CONSTRAINT fk_run FOREIGN KEY (run_id) 
        REFERENCES reporting.dim_run(run_id)
);

CREATE TABLE reporting.fact_input_changes (
    change_id BIGSERIAL PRIMARY KEY,
    scenario_id UUID NOT NULL,
    node_id UUID NOT NULL,
    changed_at TIMESTAMP NOT NULL,
    changed_by VARCHAR(255),
    previous_hash VARCHAR(255),
    current_hash VARCHAR(255),
    change_type VARCHAR(50),
    input_data JSONB,
    is_validated BOOLEAN,
    validation_errors JSONB,
    etl_loaded_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_scenario FOREIGN KEY (scenario_id) 
        REFERENCES reporting.dim_scenario(scenario_id),
    CONSTRAINT fk_node FOREIGN KEY (node_id) 
        REFERENCES reporting.dim_node(node_id)
);

CREATE TABLE reporting.fact_node_calculations (
    calc_id BIGSERIAL PRIMARY KEY,
    run_id UUID NOT NULL,
    scenario_id UUID NOT NULL,
    node_id UUID NOT NULL,
    processing_start_at TIMESTAMP,
    processing_end_at TIMESTAMP,
    processing_duration_sec NUMERIC,
    calc_status VARCHAR(50),
    fail_reason TEXT,
    etl_loaded_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT fk_run FOREIGN KEY (run_id) 
        REFERENCES reporting.dim_run(run_id),
    CONSTRAINT fk_scenario FOREIGN KEY (scenario_id) 
        REFERENCES reporting.dim_scenario(scenario_id),
    CONSTRAINT fk_node FOREIGN KEY (node_id) 
        REFERENCES reporting.dim_node(node_id)
);

-- ============================================
-- INDEXES FOR PERFORMANCE
-- ============================================

-- Fact: Scenario Events
CREATE INDEX idx_events_scenario_id ON reporting.fact_scenario_events(scenario_id);
CREATE INDEX idx_events_timestamp ON reporting.fact_scenario_events(event_timestamp);
CREATE INDEX idx_events_type ON reporting.fact_scenario_events(event_type);
CREATE INDEX idx_events_user ON reporting.fact_scenario_events(event_user);
CREATE INDEX idx_events_run_id ON reporting.fact_scenario_events(run_id);

-- Fact: Input Changes
CREATE INDEX idx_input_changes_scenario ON reporting.fact_input_changes(scenario_id);
CREATE INDEX idx_input_changes_node ON reporting.fact_input_changes(node_id);
CREATE INDEX idx_input_changes_timestamp ON reporting.fact_input_changes(changed_at);

-- Fact: Node Calculations
CREATE INDEX idx_node_calc_run ON reporting.fact_node_calculations(run_id);
CREATE INDEX idx_node_calc_scenario ON reporting.fact_node_calculations(scenario_id);
CREATE INDEX idx_node_calc_status ON reporting.fact_node_calculations(calc_status);

-- Dimension: Runs
CREATE INDEX idx_dim_run_scenario ON reporting.dim_run(scenario_id);
CREATE INDEX idx_dim_run_status ON reporting.dim_run(run_status);
CREATE INDEX idx_dim_run_timestamp ON reporting.dim_run(run_at);
```

### 6.2 Event Types

| Event Type | Source | Description |
|------------|--------|-------------|
| `SCENARIO_CREATED` | fc_scenario.created_at | Scenario initialization |
| `SCENARIO_UPDATED` | fc_scenario.updated_at | Scenario modification |
| `SCENARIO_SUBMITTED` | fc_scenario.submitted_at | User submits for review |
| `SCENARIO_LOCKED` | fc_scenario.locked_at | Locked for editing |
| `INPUT_CHANGED` | fc_scenario_node_data.created_at | Input value modified |
| `RUN_STARTED` | fc_scenario_run.run_at | Forecast execution begins |
| `RUN_COMPLETED` | fc_scenario_run.run_complete_at + status=success | Run succeeded |
| `RUN_FAILED` | fc_scenario_run.run_complete_at + status=failed | Run failed |
| `RUN_TIMEOUT` | fc_scenario_run.run_complete_at + status=timeout | Run timed out |
| `NODE_CALC_FAILED` | fc_scenario_node_calc.status=failed | Specific node failed |

---

## 7. ETL Implementation

### 7.1 Project Structure

```
clearsight-etl/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connections
│   ├── models/                 # SQLAlchemy models
│   │   ├── source_models.py    # Production DB models
│   │   └── reporting_models.py # Reporting schema models
│   ├── extractors/             # Data extraction logic
│   │   ├── scenario_extractor.py
│   │   ├── run_extractor.py
│   │   └── input_extractor.py
│   ├── transformers/           # Data transformation
│   │   └── event_transformer.py
│   └── loaders/                # Data loading
│       └── reporting_loader.py
├── scheduler/
│   ├── __init__.py
│   └── jobs.py                 # APScheduler job definitions
├── tests/
│   ├── test_extractors.py
│   └── test_transformers.py
├── requirements.txt
├── .env.example
└── README.md
```

### 7.2 Configuration

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Source Database (Production)
    SOURCE_DB_HOST: str
    SOURCE_DB_PORT: int = 5432
    SOURCE_DB_NAME: str
    SOURCE_DB_USER: str
    SOURCE_DB_PASSWORD: str
    
    # Target Database (Reporting)
    TARGET_DB_HOST: str
    TARGET_DB_PORT: int = 5432
    TARGET_DB_NAME: str
    TARGET_DB_USER: str
    TARGET_DB_PASSWORD: str
    
    # ETL Configuration
    INCREMENTAL_INTERVAL_MINUTES: int = 15
    FULL_REFRESH_CRON: str = "0 2 * * *"  # 2 AM daily
    LOOKBACK_DAYS: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()
```

### 7.3 Core ETL Logic

```python
# app/extractors/scenario_extractor.py
from sqlalchemy import text
from datetime import datetime, timedelta

class ScenarioExtractor:
    def __init__(self, source_engine):
        self.engine = source_engine
    
    def extract_events_since(self, since_time: datetime):
        """Extract all scenario lifecycle events"""
        query = text("""
            SELECT 
                s.id as scenario_id,
                'SCENARIO_CREATED' as event_type,
                s.created_at as event_timestamp,
                s.created_by as event_user,
                s.created_req_id as request_id,
                s.scenario_display_name as scenario_name,
                s.status as scenario_status,
                m.model_display_name as model_name,
                jsonb_build_object(
                    'action', 'created',
                    'is_starter', s.is_starter,
                    'start_year', s.scenario_start_year,
                    'end_year', s.scenario_end_year
                ) as event_details
            FROM fc_scenario s
            JOIN fc_model m ON s.model_id = m.id
            WHERE s.created_at >= :since_time
            
            UNION ALL
            
            SELECT 
                s.id,
                'SCENARIO_SUBMITTED',
                s.submitted_at,
                s.submitted_by,
                s.submitted_req_id,
                s.scenario_display_name,
                s.status,
                m.model_display_name,
                jsonb_build_object('action', 'submitted')
            FROM fc_scenario s
            JOIN fc_model m ON s.model_id = m.id
            WHERE s.submitted_at >= :since_time 
              AND s.submitted_at IS NOT NULL
            
            -- Additional UNION ALL clauses for other events...
        """)
        
        with self.engine.connect() as conn:
            result = conn.execute(query, {"since_time": since_time})
            return [dict(row) for row in result]
```

```python
# app/loaders/reporting_loader.py
from sqlalchemy import text

class ReportingLoader:
    def __init__(self, target_engine):
        self.engine = target_engine
    
    def load_scenario_events(self, events: list):
        """Load events with upsert logic"""
        if not events:
            return
        
        # Delete existing events in time range
        delete_query = text("""
            DELETE FROM reporting.fact_scenario_events 
            WHERE event_timestamp >= :min_time 
              AND event_timestamp <= :max_time
        """)
        
        # Insert new events
        insert_query = text("""
            INSERT INTO reporting.fact_scenario_events (
                scenario_id, event_type, event_timestamp, event_user,
                event_description, request_id, node_id, run_id, event_details
            ) VALUES (
                :scenario_id, :event_type, :event_timestamp, :event_user,
                :event_description, :request_id, :node_id, :run_id, 
                :event_details::jsonb
            )
        """)
        
        with self.engine.connect() as conn:
            # Determine time range
            timestamps = [e['event_timestamp'] for e in events]
            min_time = min(timestamps)
            max_time = max(timestamps)
            
            # Delete old records
            conn.execute(delete_query, {
                "min_time": min_time, 
                "max_time": max_time
            })
            
            # Insert new records
            conn.execute(insert_query, events)
            conn.commit()
```

### 7.4 Scheduler Configuration

```python
# scheduler/jobs.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from app.config import settings
from app.etl import run_incremental_etl, run_full_etl

scheduler = BlockingScheduler()

@scheduler.scheduled_job(
    'interval', 
    minutes=settings.INCREMENTAL_INTERVAL_MINUTES,
    id='incremental_etl',
    name='Incremental ETL Job'
)
def incremental_job():
    """Run incremental ETL every 15 minutes"""
    try:
        since_time = datetime.now() - timedelta(
            minutes=settings.INCREMENTAL_INTERVAL_MINUTES
        )
        run_incremental_etl(since_time)
        print(f"Incremental ETL completed at {datetime.now()}")
    except Exception as e:
        print(f"Incremental ETL failed: {str(e)}")
        # Add monitoring/alerting here

@scheduler.scheduled_job(
    CronTrigger.from_crontab(settings.FULL_REFRESH_CRON),
    id='full_refresh_etl',
    name='Full Refresh ETL Job'
)
def full_refresh_job():
    """Run full refresh daily at 2 AM"""
    try:
        since_date = datetime.now() - timedelta(
            days=settings.LOOKBACK_DAYS
        )
        run_full_etl(since_date)
        print(f"Full refresh ETL completed at {datetime.now()}")
    except Exception as e:
        print(f"Full refresh ETL failed: {str(e)}")
        # Add monitoring/alerting here

if __name__ == '__main__':
    print("Starting ClearSight ETL Scheduler...")
    scheduler.start()
```

---

## 8. Power BI Dashboard

### 8.1 Dashboard Structure

#### Page 1: Scenario Overview
**Purpose:** High-level metrics and KPIs

**Visuals:**
1. **KPI Cards** (Top row)
   - Total Scenarios
   - Total Runs
   - Success Rate %
   - Avg Run Duration

2. **Scenario List Table**
   - Columns: Scenario Name, Status, Last Run, Success Rate
   - Sorting: By last run time (descending)
   - Click-through: Navigate to other pages

3. **Run Status Chart** (Stacked Bar)
   - X-axis: Date
   - Y-axis: Count of runs
   - Legend: Success / Failed / Timeout

4. **Top Failing Scenarios** (Bar Chart)
   - X-axis: Scenario name
   - Y-axis: Failure count

**Filters:**
- Date Range (Slicer)
- Scenario Status (Dropdown)
- Model / Disease Area (Dropdown)

#### Page 2: Event Timeline & User Journey
**Purpose:** Reconstruct what happened when

**Visuals:**
1. **Timeline Visual**
   - X-axis: Time
   - Y-axis: Event type (categorical)
   - Data labels: Event description
   - Color: Event type

2. **Event Log Table**
   - Columns: Timestamp, Event Type, User, Description, Node Name
   - Sorting: Chronological
   - Conditional formatting: Red for errors

3. **Activity by User** (Donut Chart)
   - Values: Count of events
   - Legend: User names

4. **Event Type Distribution** (Bar Chart)
   - X-axis: Event type
   - Y-axis: Count

**Filters:**
- Scenario Selector (Dropdown) - **Primary filter**
- Event Type (Multi-select)
- Date Range
- User (Multi-select)

#### Page 3: Run History & Comparison
**Purpose:** Compare runs and identify what changed

**Visuals:**
1. **Run History Table**
   - Columns: Run ID, Started At, Duration, Status, Error Message
   - Conditional formatting: Green for success, red for failure
   - Row click: Updates comparison visuals

2. **Run Duration Trend** (Line Chart)
   - X-axis: Run timestamp
   - Y-axis: Duration in seconds
   - Tooltip: Run status

3. **Input Comparison Matrix**
   - Rows: Node names
   - Columns: Run 1 Value | Run 2 Value | Difference
   - Conditional formatting: Highlight differences
   - Requires: Two runs selected

4. **Last Successful vs First Failed** (Side-by-side)
   - Automatic comparison of last working and first failing run
   - Shows: Input differences, timing, error messages

**Filters:**
- Scenario Selector
- Run Status
- Date Range

**Interactions:**
- Click run in table → Updates comparison section
- Button: "Compare Selected Runs"

#### Page 4: Error Analysis & RCA
**Purpose:** Deep dive into failures

**Visuals:**
1. **Failed Runs Table**
   - Columns: Scenario, Run Time, Error Message, Failed Nodes
   - Expandable: Click to see node-level details
   - Export: Allow CSV export

2. **Top Error Messages** (Tree Map)
   - Size: Frequency of error
   - Label: Error message (truncated)
   - Tooltip: Full error + count

3. **Failed Nodes Frequency** (Bar Chart)
   - X-axis: Node name
   - Y-axis: Failure count
   - Insight: Which nodes fail most often

4. **Node Processing Time Distribution** (Scatter Plot)
   - X-axis: Node type
   - Y-axis: Processing time
   - Color: Success/Failed
   - Insight: Correlation between long processing and failures

**Filters:**
- Date Range
- Model / Disease Area
- Node Type
- Error Message (Search box)

**Drill-through:**
- Right-click failed run → Navigate to Timeline page with context

### 8.2 Power BI Data Model

```
Relationships:
- dim_scenario[scenario_id] → fact_scenario_events[scenario_id]
- dim_user[user_id] → fact_scenario_events[event_user]
- dim_node[node_id] → fact_scenario_events[node_id]
- dim_run[run_id] → fact_scenario_events[run_id]
- dim_run[run_id] → fact_node_calculations[run_id]
- dim_node[node_id] → fact_input_changes[node_id]

Relationship Type: One-to-Many (Dimension → Fact)
Cardinality: Single
Filter Direction: Single (from Dimension to Fact)
```

### 8.3 DAX Measures

```dax
// Success Rate
Success Rate = 
DIVIDE(
    CALCULATE(COUNT(dim_run[run_id]), dim_run[run_status] = "success"),
    COUNT(dim_run[run_id]),
    0
)

// Average Run Duration (seconds)
Avg Run Duration = 
AVERAGE(dim_run[duration_seconds])

// Total Failures
Total Failures = 
CALCULATE(
    COUNT(dim_run[run_id]),
    dim_run[run_status] IN {"failed", "timeout"}
)

// Last Run Time
Last Run Time = 
MAX(dim_run[run_at])

// Failed Node Count
Failed Nodes = 
CALCULATE(
    DISTINCTCOUNT(fact_node_calculations[node_id]),
    fact_node_calculations[calc_status] = "failed"
)

// Change Frequency (per scenario)
Input Change Count = 
CALCULATE(
    COUNT(fact_input_changes[change_id]),
    fact_input_changes[change_type] = "CHANGED"
)
```

### 8.4 Refresh Configuration

**Import Mode (Recommended)**
- Data imported into Power BI memory
- Fast query performance
- Refresh schedule: Hourly during business hours

**Power BI Service Configuration:**
```
1. Publish report to Power BI Service
2. Configure On-premises Data Gateway
   - Install gateway on server with database access
   - Configure credentials
3. Set refresh schedule:
   - Monday-Friday: Every hour (8 AM - 6 PM)
   - Saturday-Sunday: Every 4 hours
   - Maximum: 8 refreshes per day (Pro license)
```

**Alternative: DirectQuery Mode**
- Real-time data (no refresh needed)
- Queries hit database directly
- Slower performance (acceptable for dev team size)
- Use if: Data must be absolutely current

---

## 9. Implementation Plan

### 9.1 Phase 1: Foundation (Week 1-2)

#### Week 1: Database & ETL Setup
**Tasks:**
- [ ] Set up reporting schema in PostgreSQL
- [ ] Create all dimension and fact tables
- [ ] Add indexes for performance
- [ ] Set up Python project structure
- [ ] Implement database connection pooling
- [ ] Write schema inspection queries

**Deliverables:**
- `reporting` schema with all tables
- Python project skeleton
- Connection test script

**Success Criteria:**
- All tables created successfully
- Can query production DB (read-only)
- Can insert test data into reporting schema

#### Week 2: Core ETL Development
**Tasks:**
- [ ] Implement scenario event extractor
- [ ] Implement run event extractor
- [ ] Implement input change detector
- [ ] Write transformation logic
- [ ] Implement reporting loader (with upsert)
- [ ] Write unit tests for each component

**Deliverables:**
- Working ETL script (manual execution)
- Test suite with >80% coverage

**Success Criteria:**
- ETL runs successfully on sample data
- All event types captured correctly
- Input changes detected accurately

### 9.2 Phase 2: Scheduling & Power BI (Week 3-4)

#### Week 3: Scheduler & Data Quality
**Tasks:**
- [ ] Implement APScheduler configuration
- [ ] Set up incremental ETL (15-minute intervals)
- [ ] Set up full refresh ETL (daily)
- [ ] Add error handling and logging
- [ ] Implement data quality checks
- [ ] Load historical data (30 days)

**Deliverables:**
- Scheduled ETL running automatically
- Monitoring logs
- 30 days of historical data loaded

**Success Criteria:**
- ETL runs without manual intervention
- Data refreshes every 15 minutes
- No data loss or duplication

#### Week 4: Power BI Development
**Tasks:**
- [ ] Connect Power BI to reporting schema
- [ ] Build data model (relationships)
- [ ] Create Page 1: Scenario Overview
- [ ] Create Page 2: Event Timeline
- [ ] Create Page 3: Run Comparison
- [ ] Create Page 4: Error Analysis
- [ ] Implement DAX measures
- [ ] Configure filters and interactions

**Deliverables:**
- Power BI report file (.pbix)
- Documentation for each page

**Success Criteria:**
- All 4 pages functional
- Data loads within 10 seconds
- Filters work correctly

### 9.3 Phase 3: Testing & Refinement (Week 5-6)

#### Week 5: Integration Testing
**Tasks:**
- [ ] Test with 3 real debugging scenarios
- [ ] Measure time to RCA (<10 min target)
- [ ] Identify missing data or visuals
- [ ] Performance optimization (slow queries)
- [ ] Add missing event types if needed

**Test Scenarios:**
1. **Scenario A:** Find why scenario XYZ failed yesterday
2. **Scenario B:** Compare two runs of same scenario
3. **Scenario C:** Identify all scenarios failing with error "validation failed"

**Success Criteria:**
- All test scenarios completed in <10 minutes
- Developers can self-serve (no SQL needed)
- Accurate data representation

#### Week 6: User Acceptance & Polish
**Tasks:**
- [ ] UAT with 2-3 developers
- [ ] Collect feedback
- [ ] Make adjustments to visuals
- [ ] Add tooltips and help text
- [ ] Optimize dashboard performance
- [ ] Create user guide

**Deliverables:**
- Polished Power BI dashboard
- User guide (PDF)
- Feedback summary

**Success Criteria:**
- Positive feedback from dev team
- Zero critical bugs
- Dashboard loads in <5 seconds

### 9.4 Phase 4: Documentation & Handover (Week 7-8)

#### Week 7: Documentation
**Tasks:**
- [ ] Complete architecture documentation
- [ ] Write ETL maintenance guide
- [ ] Document Power BI report structure
- [ ] Create troubleshooting guide
- [ ] Write runbook for common issues

**Deliverables:**
- Solution documentation (this document)
- Technical maintenance guide
- Troubleshooting runbook

#### Week 8: Handover & Training
**Tasks:**
- [ ] Conduct training session with dev team
- [ ] Record demo video
- [ ] Set up monitoring alerts
- [ ] Transfer knowledge to maintainer
- [ ] Final presentation to stakeholders

**Deliverables:**
- Training session (recorded)
- Demo video (10-15 minutes)
- Handover checklist
- Final presentation slides

**Success Criteria:**
- Team trained on dashboard usage
- Maintainer can run ETL manually
- Stakeholders approve solution

---

## 10. Operations & Maintenance

### 10.1 Monitoring

#### ETL Health Checks

**Metrics to Monitor:**
1. **ETL Execution Success Rate**
   - Target: >99%
   - Alert: If 2+ consecutive failures

2. **Data Freshness**
   - Target: <30 minutes behind production
   - Check: `MAX(etl_loaded_at)` in reporting tables

3. **Row Count Growth**
   - Track: Daily growth in fact tables
   - Alert: If growth deviates >50% from average

4. **ETL Duration**
   - Incremental: <2 minutes
   - Full refresh: <30 minutes

**Monitoring Script:**
```python
# monitor/health_check.py
from datetime import datetime, timedelta

def check_etl_health():
    """Run health checks and send alerts if needed"""
    
    # Check 1: Data freshness
    query = "SELECT MAX(etl_loaded_at) FROM reporting.fact_scenario_events"
    last_load = execute_query(query)
    age_minutes = (datetime.now() - last_load).total_seconds() / 60
    
    if age_minutes > 30:
        send_alert(f"Data is {age_minutes} minutes old")
    
    # Check 2: Recent errors
    query = """
        SELECT COUNT(*) FROM etl_logs 
        WHERE status = 'error' AND created_at > NOW() - INTERVAL '1 hour'
    """
    error_count = execute_query(query)
    
    if error_count > 0:
        send_alert(f"{error_count} ETL errors in last hour")
    
    # Check 3: Row counts
    # ... additional checks
```

#### Power BI Monitoring

**Metrics:**
1. Refresh success rate
2. Query performance (avg time)
3. Dataset size growth
4. Active users

**Power BI Admin Portal:**
- Monitor refresh history
- Check for failed refreshes
- Review performance metrics

### 10.2 Backup & Recovery

#### Database Backup
```sql
-- Backup reporting schema
pg_dump -h localhost -U postgres -n reporting clearsight > reporting_backup.sql

-- Schedule daily backups via cron
0 3 * * * pg_dump -h localhost -U postgres -n reporting clearsight > /backups/reporting_$(date +\%Y\%m\%d).sql
```

#### ETL Code Backup
- Store in Git repository
- Tag releases: `v1.0`, `v1.1`, etc.
- Document deployment process

#### Recovery Procedures

**Scenario 1: ETL Failure**
```
1. Check ETL logs: /var/log/clearsight-etl/
2. Identify error type:
   - Database connection → Check credentials
   - SQL error → Review recent schema changes
   - Timeout → Increase interval or optimize query
3. Fix issue
4. Run manual ETL: python app/main.py --manual --since "2024-01-01"
5. Verify data loaded correctly
```

**Scenario 2: Data Corruption**
```
1. Stop scheduler
2. Restore from backup: psql -U postgres clearsight < reporting_backup.sql
3. Run full refresh ETL
4. Verify data integrity
5. Resume scheduler
```

**Scenario 3: Power BI Report Issues**
```
1. Check data gateway status
2. Test database connection
3. Refresh dataset manually
4. If still failing, restore .pbix from version control
5. Republish to Power BI Service
```

### 10.3 Maintenance Tasks

#### Weekly
- [ ] Review ETL logs for warnings
- [ ] Check disk space on database server
- [ ] Monitor Power BI refresh times

#### Monthly
- [ ] Review dashboard usage metrics
- [ ] Optimize slow-running queries
- [ ] Update documentation if needed
- [ ] Prune old data (>90 days)

#### Quarterly
- [ ] Review and update DAX measures
- [ ] Add new event types if needed
- [ ] Conduct user feedback session
- [ ] Performance tuning

### 10.4 Scaling Considerations

**Current Capacity:**
- 100 scenarios/day
- 500 runs/day
- 10,000 input changes/day
- Reporting DB size: ~5 GB (30 days)

**Scaling Triggers:**
- ETL duration >5 minutes (incremental)
- Database size >50 GB
- Power BI refresh >10 minutes
- Query performance >5 seconds

**Scaling Strategies:**
1. **Partition fact tables by month**
   ```sql
   CREATE TABLE reporting.fact_scenario_events_2024_02 
   PARTITION OF reporting.fact_scenario_events
   FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
   ```

2. **Implement parallel ETL**
   - Run extractors concurrently
   - Use multiprocessing for large datasets

3. **Optimize Power BI**
   - Use aggregation tables
   - Implement incremental refresh
   - Consider premium capacity

4. **Archive old data**
   - Move data >90 days to archive tables
   - Keep aggregates only

---

## 11. Success Metrics

### 11.1 Objectives and Key Results (OKRs)

#### Objective 1: Build a Working Prototype
**KR1:** Extract core data (scenarios, runs, input changes) from Postgres into reporting layer
- **Target:** 100% of critical tables
- **Measurement:** All 5 dimension tables + 3 fact tables populated

**KR2:** Create a Power BI dashboard with scenario overview, run history, and basic user journey view
- **Target:** 4 functional dashboard pages
- **Measurement:** All pages load without errors, filters work

#### Objective 2: Make the Dashboard Useful for Basic Debugging
**KR1:** Enable reconstruction of user journey and run context for at least 3 sample issues using only the dashboard
- **Target:** 100% success rate on test scenarios
- **Measurement:** 3 real bugs debugged start-to-finish in dashboard

**KR2:** Reduce time for developers to understand a reported scenario issue to under 10 minutes for those samples
- **Target:** <10 minutes average
- **Measurement:** Time tracking on 3 test scenarios
  - Baseline (manual SQL): 30-45 minutes
  - Target (dashboard): <10 minutes

#### Objective 3: Ensure Maintainability After Internship
**KR1:** Deliver clear documentation for architecture, data flows, and dashboard usage
- **Target:** Complete documentation package
- **Measurement:** 
  - Architecture doc (this document)
  - ETL maintenance guide
  - Dashboard user guide
  - Troubleshooting runbook

**KR2:** Conduct a final demo and handover session with the development team
- **Target:** Successful knowledge transfer
- **Measurement:**
  - Demo presented to team
  - Handover session completed
  - Team can use dashboard independently

### 11.2 Performance Metrics

| Metric | Baseline (Before) | Target (After) | Measurement Method |
|--------|-------------------|----------------|-------------------|
| **Time to RCA** | 30-45 min | <10 min | Timed test scenarios |
| **Developer Productivity** | 20% time on debugging | 5% time on debugging | Time tracking (estimated) |
| **Manual SQL Queries** | 5-10 per issue | 0 per issue | Query log analysis |
| **Bug Resolution Time** | 2-4 hours | 1-2 hours | Ticket tracking |
| **Data Freshness** | N/A (manual) | <15 min | ETL monitoring |
| **Dashboard Load Time** | N/A | <5 sec | Power BI analytics |

### 11.3 Adoption Metrics

**Target (3 months post-launch):**
- 100% of dev team trained
- 80% of debugging sessions use dashboard
- 5+ active users weekly
- <3 support requests per month

**Tracking:**
- Power BI usage analytics
- User surveys
- Support ticket analysis

---

## 12. Risks & Mitigation

### 12.1 Technical Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **Production DB Performance Impact** | Low | High | Read-only access, off-peak ETL, query optimization |
| **ETL Job Failures** | Medium | Medium | Retry logic, error alerts, manual fallback |
| **Data Quality Issues** | Medium | High | Validation checks, data quality tests, reconciliation |
| **Power BI Refresh Failures** | Medium | Medium | Alternative data gateway, manual refresh option |
| **Schema Changes Breaking ETL** | Low | High | Version control, automated tests, schema monitoring |

### 12.2 Operational Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **Knowledge Loss After Internship** | High | High | Comprehensive documentation, handover session, training |
| **Lack of Adoption by Team** | Medium | High | User training, demo sessions, collect feedback early |
| **Maintenance Neglect** | Medium | Medium | Assign owner, schedule reviews, monitoring alerts |
| **Security/Access Issues** | Low | High | Read-only DB credentials, role-based Power BI access |

### 12.3 Project Risks

| Risk | Probability | Impact | Mitigation Strategy |
|------|-------------|--------|---------------------|
| **Scope Creep** | Medium | Medium | Clear requirements, prioritize MVP, defer enhancements |
| **Timeline Delays** | Medium | Medium | Buffer weeks, weekly progress reviews, cut low-priority features |
| **Resource Unavailability** | Low | Medium | Document dependencies, have backup plan |
| **Stakeholder Misalignment** | Low | High | Regular check-ins, demos, feedback loops |

### 12.4 Mitigation Actions

**Priority 1 (Critical):**
1. Set up read-only database user for ETL
2. Implement comprehensive error handling in ETL
3. Create complete documentation before internship end
4. Schedule formal handover session

**Priority 2 (Important):**
1. Add data quality validation to ETL pipeline
2. Set up monitoring alerts for ETL failures
3. Create troubleshooting runbook
4. Conduct user training sessions

**Priority 3 (Nice-to-have):**
1. Build automated testing for ETL
2. Set up CI/CD pipeline
3. Create video tutorials
4. Implement advanced error recovery

---

## 13. Appendices

### 13.1 Glossary

| Term | Definition |
|------|------------|
| **RCA** | Root Cause Analysis - process of identifying underlying cause of errors |
| **ETL** | Extract, Transform, Load - data integration process |
| **Star Schema** | Database schema with central fact table and dimension tables |
| **Fact Table** | Table storing measurements and metrics |
| **Dimension Table** | Table storing descriptive attributes |
| **DAX** | Data Analysis Expressions - formula language for Power BI |
| **Incremental ETL** | Extracting only changed/new data since last run |
| **DirectQuery** | Power BI mode that queries database in real-time |
| **Import Mode** | Power BI mode that caches data in memory |

### 13.2 Reference SQL Queries

#### Query 1: Get Complete Event Timeline for a Scenario
```sql
WITH scenario_events AS (
    SELECT 
        'SCENARIO_CREATED' AS event_type,
        s.created_at AS event_time,
        s.created_by AS event_user,
        NULL AS details
    FROM fc_scenario s
    WHERE s.id = :scenario_id
    
    UNION ALL
    
    SELECT 
        'INPUT_CHANGED',
        snd.created_at,
        snd.created_by,
        json_build_object('node_name', mn.node_display_name, 'node_id', snd.model_node_id)::text
    FROM fc_scenario_node_data snd
    JOIN fc_model_node mn ON snd.model_node_id = mn.id
    WHERE snd.scenario_id = :scenario_id
    
    UNION ALL
    
    SELECT 
        CASE sr.run_status
            WHEN 'success' THEN 'RUN_COMPLETED'
            WHEN 'failed' THEN 'RUN_FAILED'
            ELSE 'RUN_STARTED'
        END,
        sr.run_at,
        sr.run_by,
        json_build_object('run_id', sr.id, 'status', sr.run_status, 'fail_reason', sr.fail_reason)::text
    FROM fc_scenario_run sr
    WHERE sr.scenario_id = :scenario_id
)
SELECT * FROM scenario_events
WHERE event_time IS NOT NULL
ORDER BY event_time;
```

#### Query 2: Detect Input Changes with Hash Comparison
```sql
WITH input_history AS (
    SELECT 
        snd.scenario_id,
        snd.model_node_id,
        mn.node_display_name,
        snd.input_hash,
        snd.created_at,
        LAG(snd.input_hash) OVER (
            PARTITION BY snd.scenario_id, snd.model_node_id 
            ORDER BY snd.created_at
        ) AS prev_hash
    FROM fc_scenario_node_data snd
    JOIN fc_model_node mn ON snd.model_node_id = mn.id
    WHERE snd.scenario_id = :scenario_id
)
SELECT 
    scenario_id,
    model_node_id,
    node_display_name,
    created_at,
    prev_hash,
    input_hash,
    CASE 
        WHEN prev_hash IS NULL THEN 'INITIAL_VALUE'
        WHEN prev_hash != input_hash THEN 'VALUE_CHANGED'
        ELSE 'NO_CHANGE'
    END AS change_type
FROM input_history
WHERE prev_hash IS NULL OR prev_hash != input_hash
ORDER BY created_at;
```

#### Query 3: Get Input Snapshot at Time of Run
```sql
WITH run_info AS (
    SELECT id, scenario_id, run_at 
    FROM fc_scenario_run 
    WHERE id = :run_id
)
SELECT 
    ri.id AS run_id,
    ri.run_at,
    mn.node_display_name,
    snd.input_data,
    snd.input_hash
FROM run_info ri
CROSS JOIN fc_model_node mn
LEFT JOIN LATERAL (
    SELECT *
    FROM fc_scenario_node_data snd
    WHERE snd.scenario_id = ri.scenario_id
      AND snd.model_node_id = mn.id
      AND snd.created_at <= ri.run_at
      AND (snd.end_at IS NULL OR snd.end_at > ri.run_at)
    ORDER BY snd.created_at DESC
    LIMIT 1
) snd ON true
WHERE mn.model_id = (SELECT model_id FROM fc_scenario WHERE id = ri.scenario_id)
ORDER BY mn.node_display_name;
```

### 13.3 Environment Setup Checklist

**Development Environment:**
- [ ] Python 3.11+ installed
- [ ] PostgreSQL 14+ installed
- [ ] Power BI Desktop installed
- [ ] Git installed
- [ ] Code editor (VS Code recommended)

**Python Dependencies:**
```
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
apscheduler==3.10.4
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
pytest==7.4.3
```

**Database Access:**
- [ ] Read-only credentials for production DB
- [ ] Write access to reporting schema
- [ ] VPN/network access configured

**Power BI:**
- [ ] Power BI Pro license
- [ ] On-premises data gateway installed
- [ ] Access to Power BI Service workspace

### 13.4 Contact Information

**Project Team:**
- **Intern Developer:** Jarvis
- **Project Mentor:** [Name]
- **Database Admin:** [Name]
- **DevOps Lead:** [Name]

**Support Channels:**
- Slack: #clearsight-dashboard
- Email: clearsight-support@company.com
- Documentation: Confluence page link

### 13.5 Related Documentation

- ClearSight 2.0 Application Documentation
- Database Schema Documentation
- Forecast Engine API Documentation
- Power BI Best Practices Guide
- PostgreSQL Performance Tuning Guide

---

## Conclusion

The ClearSight 2.0 Scenario Audit & RCA Dashboard represents a significant improvement in developer productivity and system reliability. By consolidating fragmented diagnostic data into an intuitive Power BI interface, the solution reduces root cause analysis time from 30+ minutes to under 10 minutes.

The non-invasive architecture ensures zero impact on production systems while providing comprehensive visibility into scenario lifecycles. With automated ETL and scheduled refreshes, the dashboard remains current without manual intervention.

This documentation provides a complete blueprint for implementation, operation, and maintenance of the solution. Following the 8-week implementation plan will deliver a production-ready dashboard that serves the development team long after the internship concludes.

### Key Takeaways

1. **Read-only approach** ensures safety for production database
2. **Star schema** optimizes for analytical queries in Power BI
3. **Event stream architecture** provides complete audit trail
4. **Automated ETL** eliminates manual data gathering
5. **Comprehensive documentation** ensures maintainability

### Next Steps

1. Review and approve architecture
2. Set up development environment
3. Begin Phase 1 implementation
4. Schedule weekly progress reviews
5. Prepare for final handover

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Feb 2026 | Jarvis | Initial comprehensive documentation |

**Approval:**

- [ ] Project Mentor
- [ ] DevOps Lead
- [ ] Database Admin
- [ ] Product Owner

---

*End of Document*
