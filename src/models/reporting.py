"""SQLAlchemy ORM models for the reporting star schema.

All tables live in the 'rpt' Postgres schema. These are written by the ETL
pipeline and read by the FastAPI layer serving Power BI.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

RPT_SCHEMA = "rpt"


class ReportingBase(DeclarativeBase):
    metadata = DeclarativeBase.metadata
    __table_args__ = {"schema": RPT_SCHEMA}


# ===================================================================
# DIMENSION TABLES
# ===================================================================


class DimDate(ReportingBase):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)  # YYYYMMDD
    full_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    quarter: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    week_of_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon, 6=Sun
    is_weekday: Mapped[bool] = mapped_column(Boolean, nullable=False)


class DimModel(ReportingBase):
    __tablename__ = "dim_model"

    model_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    therapeutic_area: Mapped[str] = mapped_column(String(255), nullable=False)
    disease_area: Mapped[str] = mapped_column(String(255), nullable=False)
    publish_level: Mapped[str] = mapped_column(String(50), nullable=False)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    country_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    region_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimForecastCycle(ReportingBase):
    __tablename__ = "dim_forecast_cycle"

    forecast_cycle_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_init_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    model_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_model.model_key"), nullable=False
    )
    cycle_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cycle_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cycle_end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_start: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_end: Mapped[int] = mapped_column(Integer, nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimUser(ReportingBase):
    __tablename__ = "dim_user"

    user_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimScenario(ReportingBase):
    __tablename__ = "dim_scenario"

    scenario_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    model_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_model.model_key"), nullable=False
    )
    forecast_cycle_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_forecast_cycle.forecast_cycle_key"), nullable=False
    )
    scenario_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False)
    current_status: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    region_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    created_by_user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimNode(ReportingBase):
    __tablename__ = "dim_node"

    node_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    model_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_model.model_key"), nullable=False
    )
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(255), nullable=False)
    flow: Mapped[str] = mapped_column(String(255), nullable=False)
    tab_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    is_output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DimEventType(ReportingBase):
    __tablename__ = "dim_event_type"

    event_type_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    event_type_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_inherent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ===================================================================
# FACT TABLES
# ===================================================================


class FactScenarioRun(ReportingBase):
    __tablename__ = "fact_scenario_run"

    run_fact_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    model_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_model.model_key"), nullable=False
    )
    forecast_cycle_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_forecast_cycle.forecast_cycle_key"), nullable=False
    )
    run_by_user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False
    )
    run_date_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_date.date_key"), nullable=False
    )
    run_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    run_status: Mapped[str] = mapped_column(String(50), nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    branch_count: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    node_calc_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_calc_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_calc_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    node_calc_timeout: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    has_event_calcs: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fail_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_snapshot_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactNodeCalcDetail(ReportingBase):
    __tablename__ = "fact_node_calc_detail"

    node_calc_fact_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    calc_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_fact_key: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{RPT_SCHEMA}.fact_scenario_run.run_fact_key"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_tag: Mapped[str] = mapped_column(String(50), nullable=False)
    node_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_node.node_key"), nullable=False
    )
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    calc_status: Mapped[str] = mapped_column(String(50), nullable=False)
    processing_time_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    output_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactScenarioInputChange(ReportingBase):
    __tablename__ = "fact_scenario_input_change"

    input_change_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    node_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_node.node_key"), nullable=False
    )
    changed_by_user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False
    )
    change_date_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_date.date_key"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_input_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_input_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    change_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id_before: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    run_id_after: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    input_diff_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactEventInputChange(ReportingBase):
    __tablename__ = "fact_event_input_change"

    event_input_change_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    event_type_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_event_type.event_type_key"), nullable=False
    )
    changed_by_user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False
    )
    change_date_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_date.date_key"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    previous_input_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    new_input_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    change_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    input_diff_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactRunComparison(ReportingBase):
    __tablename__ = "fact_run_comparison"

    comparison_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    run_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_a_status: Mapped[str] = mapped_column(String(50), nullable=False)
    run_a_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_b_status: Mapped[str] = mapped_column(String(50), nullable=False)
    run_b_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status_transition: Mapped[str] = mapped_column(String(100), nullable=False)
    input_changes_between: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    changed_node_keys: Mapped[list | None] = mapped_column(ARRAY(Integer), nullable=True)
    duration_delta_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    node_failures_delta: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactReliabilityDaily(ReportingBase):
    __tablename__ = "fact_reliability_daily"

    reliability_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    date_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_date.date_key"), nullable=False
    )
    model_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_model.model_key"), nullable=False
    )
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    successful_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timeout_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    avg_duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    p95_duration_seconds: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    total_node_failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_error_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    top_failing_node_key: Mapped[int | None] = mapped_column(Integer, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


# ===================================================================
# ETL TRACKING
# ===================================================================


class EtlWatermark(ReportingBase):
    __tablename__ = "etl_watermark"

    table_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    last_loaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_started: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_completed: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    row_count_loaded: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")


# ===================================================================
# RCA & AUDIT TRAIL TABLES (For Scenario Audit & RCA Dashboard)
# ===================================================================


class FactCloudWatchLog(ReportingBase):
    """CloudWatch logs integrated with correlation IDs for RCA."""
    __tablename__ = "fact_cloudwatch_log"

    log_fact_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    log_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    log_stream: Mapped[str] = mapped_column(String(500), nullable=False)
    log_group: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)  # INFO, WARN, ERROR
    message: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    environment: Mapped[str] = mapped_column(String(20), nullable=False)  # dev, sit, uat, prod
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    stack_trace: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactScenarioStateChange(ReportingBase):
    """Tracks all scenario lifecycle state transitions (draft→submitted→locked, etc.)."""
    __tablename__ = "fact_scenario_state_change"

    state_change_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False, index=True
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    previous_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    new_status: Mapped[str] = mapped_column(String(50), nullable=False)
    transition_type: Mapped[str] = mapped_column(String(100), nullable=False)  # created, submitted, locked, withdrawn, deleted
    changed_by_user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False
    )
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactUserAction(ReportingBase):
    """Chronological log of all user actions (create, edit, run, delete, submit)."""
    __tablename__ = "fact_user_action"

    action_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_user.user_key"), nullable=False, index=True
    )
    scenario_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=True, index=True
    )
    action_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # create_scenario, edit_input, run_forecast, submit, lock, delete
    action_category: Mapped[str] = mapped_column(String(50), nullable=False)  # scenario_mgmt, input_data, forecast_run, config_change
    target_entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # scenario, node, event, model
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    request_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    http_method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    request_duration_ms: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Stores before/after snapshots
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class FactRunDiagnostic(ReportingBase):
    """Detailed diagnostic information linking runs to inputs, outputs, and errors."""
    __tablename__ = "fact_run_diagnostic"

    diagnostic_key: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_fact_key: Mapped[int] = mapped_column(
        BigInteger, ForeignKey(f"{RPT_SCHEMA}.fact_scenario_run.run_fact_key"), nullable=False, index=True
    )
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    scenario_key: Mapped[int] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_scenario.scenario_key"), nullable=False
    )
    diagnostic_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # input_snapshot, error_summary, perf_metric, validation_issue
    node_key: Mapped[int | None] = mapped_column(
        Integer, ForeignKey(f"{RPT_SCHEMA}.dim_node.node_key"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, major, minor, info
    diagnostic_category: Mapped[str] = mapped_column(String(100), nullable=False)  # data_validation, calculation_error, timeout, config_issue
    diagnostic_message: Mapped[str] = mapped_column(Text, nullable=False)
    diagnostic_details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    input_hash_at_run: Mapped[str | None] = mapped_column(String(255), nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    cloudwatch_log_references: Mapped[list | None] = mapped_column(ARRAY(BigInteger), nullable=True)  # FK to fact_cloudwatch_log
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ViewScenarioAuditTrail(ReportingBase):
    """Materialized view: Complete audit trail for a scenario (all events chronologically)."""
    __tablename__ = "view_scenario_audit_trail"
    __table_args__ = {"schema": RPT_SCHEMA, "info": {"is_view": True}}

    audit_key: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scenario_key: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # state_change, input_change, event_change, run_started, run_completed
    event_category: Mapped[str] = mapped_column(String(50), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_description: Mapped[str] = mapped_column(Text, nullable=False)
    event_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
