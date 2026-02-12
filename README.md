# Scenario Audit & RCA Dashboard

> **Developer-facing Power BI dashboard for faster, more consistent forecast debugging**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-336791.svg)](https://www.postgresql.org/)
[![Power BI](https://img.shields.io/badge/Power%20BI-Desktop-F2C811.svg)](https://powerbi.microsoft.com/)

---

## 📋 Overview

The **RCA Dashboard** reconstructs the complete audit trail of forecast scenarios by integrating:

- PostgreSQL database tables (scenarios, runs, inputs)
- AWS CloudWatch logs (errors, diagnostics)
- User actions and state transitions

**Before:** RCA required 60+ minutes of manual SQL queries and log digging  
**After:** Complete diagnostic view in <10 minutes via Power BI dashboard

---

## 🏗️ Architecture Diagrams

### High Level Overview
![High Level Overview](high%20level%20overview.png)

### Overall Overview
![Overall Overview](overall%20overview.png)

---

## ✨ Key Features

| Feature                        | Description                                                       |
| ------------------------------ | ----------------------------------------------------------------- |
| 🔍 **Scenario Lifecycle View** | Track scenario from creation → submission → run → success/failure |
| 👤 **User Journey Timeline**   | Chronological view of all user actions per scenario               |
| 🔄 **Run Comparison**          | Compare last working vs first failing run with input diffs        |
| 🚨 **Integrated Diagnostics**  | CloudWatch logs linked to scenarios/runs via correlation IDs      |
| 📊 **Error Aggregation**       | Top error categories, failing nodes, reliability metrics          |

---

## 🏗️ Architecture

```
Source DB + CloudWatch → ETL Pipeline → Reporting DB → FastAPI → Power BI
```

**Data Flow:**

1. **Extract** - Pull data from fc_* tables + CloudWatch logs
2. **Transform** - Reconstruct user journeys, run comparisons, error categorization
3. **Load** - Populate rpt.* fact/dimension tables
4. **Serve** - FastAPI endpoints for Power BI consumption

**Tech Stack:**

- Python (FastAPI, SQLAlchemy, boto3)
- PostgreSQL (star schema, materialized views)
- AWS CloudWatch (log aggregation)
- Power BI Desktop (visualization)

---

## 🚀 Quick Start

### 1. Install

```bash
pip install -e .
pip install boto3
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with database credentials
```

### 3. Migrate

```bash
alembic upgrade head
```

### 4. Load Data

```bash
# Load last 7 days (with mock CloudWatch)
python scripts/run_rca_etl.py --incremental --cloudwatch-days 7 --mock-cloudwatch
```

### 5. Start API

```bash
python -m uvicorn src.api.main:app --reload --port 8000
```

### 6. Connect Power BI

1. Open Power BI Desktop
2. Get Data → Web
3. URL: `http://localhost:8000/api/v1/rca/scenario/{id}/audit-trail`

**Full setup guide:** [docs/QUICK_START.md](docs/QUICK_START.md)

---

## 📚 Documentation

| Document                                                        | Purpose                                     |
| --------------------------------------------------------------- | ------------------------------------------- |
| **[QUICK_START.md](docs/QUICK_START.md)**                       | 5-minute setup guide                        |
| **[RCA_DASHBOARD_README.md](docs/RCA_DASHBOARD_README.md)**     | Complete feature documentation (500+ lines) |
| **[ARCHITECTURE_DIAGRAMS.md](docs/ARCHITECTURE_DIAGRAMS.md)**   | System architecture diagrams (8 diagrams)   |
| **[IMPLEMENTATION_SUMMARY.md](docs/IMPLEMENTATION_SUMMARY.md)** | Project summary and deliverables            |

---

## 🎯 Use Cases

### ❌ **Before RCA Dashboard**

**User reports:** "My forecast run failed but I don't know why."

**Developer investigation:**

1. ❌ Query fc_scenario table for scenario details (5 min)
2. ❌ Query fc_scenario_run for run status (3 min)
3. ❌ Query fc_scenario_node_data for input state (10 min)
4. ❌ Dig through CloudWatch logs for error messages (20 min)
5. ❌ Compare with previous successful run (15 min)
6. ❌ Manually correlate logs with correlation IDs (10 min)

**Total time:** 60+ minutes

---

### ✅ **With RCA Dashboard**

**User reports:** "My forecast run failed but I don't know why."

**Developer investigation:**

1. ✅ Open Power BI → Select scenario (30 sec)
2. ✅ View timeline → See run failed at 11:05 AM (10 sec)
3. ✅ Click run → Drill-through to diagnostics page (5 sec)
4. ✅ See error logs: "Timeout in Treatment Share node" (20 sec)
5. ✅ Switch to Run Comparison page (10 sec)
6. ✅ Compare to last successful run → See input changed from 10% to 90% (30 sec)

**Diagnosis:** User entered invalid market share value causing calculation overflow

**Total time:** <2 minutes

---

## 🔌 API Endpoints

**Base URL:** `http://localhost:8000/api/v1/rca`

| Endpoint                            | Purpose                       |
| ----------------------------------- | ----------------------------- |
| `GET /scenario/{id}/audit-trail`    | Complete event timeline       |
| `GET /scenario/{id}/state-changes`  | Lifecycle transitions         |
| `GET /user/{id}/journey`            | User action history           |
| `GET /run/{id}/diagnostics`         | Run details + CloudWatch logs |
| `GET /scenario/{id}/run-comparison` | Compare 2 runs                |
| `GET /errors/top-categories`        | Error aggregation             |

**Interactive docs:** http://localhost:8000/docs

---

## 📊 Database Schema

**Reporting Schema (rpt.*):**

**Dimension Tables:**

- `dim_scenario` - Scenario master data
- `dim_user` - User master data
- `dim_model` - Forecast model definitions
- `dim_node` - Node definitions
- `dim_date` - Time dimension

**Fact Tables:**

- `fact_scenario_run` - Run metadata & metrics
- `fact_scenario_state_change` - Lifecycle transitions
- `fact_user_action` - User actions chronologically
- `fact_scenario_input_change` - Input modifications
- `fact_cloudwatch_log` - CloudWatch logs with correlation IDs
- `fact_run_diagnostic` - Run-specific diagnostics

**Materialized View:**

- `view_scenario_audit_trail` - Unified timeline (UNION of all events)

---

## 🗂️ Project Structure

```
POC/
├── src/
│   ├── models/
│   │   ├── source.py          # Source DB models (read-only)
│   │   └── reporting.py       # Reporting DB models (RCA tables)
│   ├── db/
│   │   ├── source_engine.py   # Source DB connection
│   │   └── reporting_engine.py # Reporting DB connection
│   ├── etl/
│   │   ├── extractors/
│   │   │   ├── audit_trail.py  # State changes, user actions
│   │   │   └── cloudwatch.py   # CloudWatch log extractor
│   │   ├── transformers/
│   │   │   └── user_journey.py # Journey reconstruction
│   │   └── loaders/
│   │       └── rca_loaders.py  # Reporting DB loaders
│   ├── api/
│   │   └── v1/
│   │       └── rca.py          # Power BI API endpoints
│   └── config.py
├── alembic/
│   └── versions/
│       └── rca_001_add_rca_tables.py  # Migration
├── scripts/
│   └── run_rca_etl.py          # ETL orchestration
├── docs/
│   ├── RCA_DASHBOARD_README.md  # Main documentation
│   ├── ARCHITECTURE_DIAGRAMS.md # System diagrams
│   ├── QUICK_START.md           # Setup guide
│   └── IMPLEMENTATION_SUMMARY.md # Project summary
└── pyproject.toml
```

---

## 🧪 Example ETL Commands

```bash
# Full load (all historical data)
python scripts/run_rca_etl.py --full

# Incremental load (last 24 hours)
python scripts/run_rca_etl.py --incremental

# Load specific scenario
python scripts/run_rca_etl.py --scenario-id <uuid>

# Load CloudWatch logs (last 7 days)
python scripts/run_rca_etl.py --cloudwatch-days 7

# Use mock CloudWatch (no AWS credentials)
python scripts/run_rca_etl.py --cloudwatch-days 7 --mock-cloudwatch
```

---

## 🔒 Security

**Development:**

- Read-only database user for source DB
- API key authentication (`dev-api-key-change-in-production`)
- Localhost CORS only

**Production Recommendations:**

- OAuth 2.0 authentication
- Row-level security (user sees only their scenarios)
- PII redaction in logs
- Rate limiting
- HTTPS/TLS encryption

---

## 🎯 OKRs

### **Objective 1:** Build working RCA dashboard prototype

- ✅ KR1: Extract data from Postgres + CloudWatch → Reporting DB
- 🎯 KR2: Create Power BI dashboard (5 pages)

### **Objective 2:** Enable basic debugging for developers

- 🎯 KR1: Reconstruct user journey for 3 sample issues
- 🎯 KR2: Reduce RCA time to <10 minutes

### **Objective 3:** Ensure maintainability

- ✅ KR1: Deliver clear documentation (1,200+ lines)
- 📅 KR2: Conduct demo and handover session

---

## 🤝 Contributing

For questions or contributions:

- **Documentation:** See [docs/](docs/)
- **Issues:** Contact project team

---

## 📄 License

Internal project. For internal use only.

---

## 🙏 Acknowledgments

**Built with:**

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) - AWS SDK for Python
- [Power BI](https://powerbi.microsoft.com/) - Business intelligence platform

**Inspired by:**

- Forecasting Platform best practices
- Microsoft DevOps best practices

---

**Version:** 1.0.0  
**Status:** ✅ Implementation Complete  
**Last Updated:** 2026-02-12