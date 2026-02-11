"""Read-only SQLAlchemy ORM models for the OLTP source tables.

These map directly to the ClearSight forecast service schema.
Used by the ETL pipeline for extraction only — never written to.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class SourceBase(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# fc_model
# ---------------------------------------------------------------------------
class FcModel(SourceBase):
    __tablename__ = "fc_model"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    therapeutic_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    therapeutic_area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_disease_area_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    model_disease_area_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_publish_level: Mapped[str] = mapped_column(String(50), nullable=False)
    model_country_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model_country_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model_region_display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Relationships
    forecast_inits = relationship("FcForecastInit", back_populates="model")
    scenarios = relationship("FcScenario", back_populates="model")
    node_tabs = relationship("FcModelNodeTab", back_populates="model")
    nodes = relationship("FcModelNode", back_populates="model")


# ---------------------------------------------------------------------------
# fc_forecast_init
# ---------------------------------------------------------------------------
class FcForecastInit(SourceBase):
    __tablename__ = "fc_forecast_init"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model.id"), nullable=False
    )
    forecast_cycle_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    starter_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forecast_cycle_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    forecast_cycle_start_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    forecast_cycle_end_dt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    horizon_start_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_end_limit: Mapped[int] = mapped_column(Integer, nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    initiated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    initiated_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    model = relationship("FcModel", back_populates="forecast_inits")
    scenarios = relationship("FcScenario", back_populates="forecast_init")


# ---------------------------------------------------------------------------
# fc_scenario
# ---------------------------------------------------------------------------
class FcScenario(SourceBase):
    __tablename__ = "fc_scenario"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model.id"), nullable=False
    )
    forecast_init_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_forecast_init.id"), nullable=False
    )
    core_scenario_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scenario_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_start_year: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_end_year: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_region_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scenario_region_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scenario_country_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    scenario_country_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(3), nullable=True)

    # Audit fields
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locked_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    delete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delete_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delete_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    withdraw_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdraw_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    withdraw_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    model = relationship("FcModel", back_populates="scenarios")
    forecast_init = relationship("FcForecastInit", back_populates="scenarios")
    node_data = relationship("FcScenarioNodeData", back_populates="scenario")
    runs = relationship("FcScenarioRun", back_populates="scenario")
    event_types = relationship("FcScenarioEventType", back_populates="scenario")


# ---------------------------------------------------------------------------
# fc_model_node_tab
# ---------------------------------------------------------------------------
class FcModelNodeTab(SourceBase):
    __tablename__ = "fc_model_node_tab"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    parent_tab_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node_tab.id"), nullable=True
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model.id"), nullable=False
    )
    tab_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tab_level: Mapped[int] = mapped_column(Integer, nullable=False)
    tab_seq: Mapped[int] = mapped_column(Integer, nullable=False)

    model = relationship("FcModel", back_populates="node_tabs")
    parent_tab = relationship("FcModelNodeTab", remote_side=[id])
    node_groups = relationship("FcModelNodeGroups", back_populates="node_tab")


# ---------------------------------------------------------------------------
# fc_model_node_groups
# ---------------------------------------------------------------------------
class FcModelNodeGroups(SourceBase):
    __tablename__ = "fc_model_node_groups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_node_tab_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node_tab.id"), nullable=False
    )
    group_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    group_type: Mapped[str] = mapped_column(String(255), nullable=False)
    group_seq: Mapped[int] = mapped_column(Integer, nullable=False)

    node_tab = relationship("FcModelNodeTab", back_populates="node_groups")
    nodes = relationship("FcModelNode", back_populates="node_group")


# ---------------------------------------------------------------------------
# fc_model_node
# ---------------------------------------------------------------------------
class FcModelNode(SourceBase):
    __tablename__ = "fc_model_node"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_node_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node_groups.id"), nullable=False
    )
    model_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model.id"), nullable=False
    )
    flow: Mapped[str] = mapped_column(String(255), nullable=False)
    base_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    treatment_group_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    model_config_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    node_type: Mapped[str] = mapped_column(String(255), nullable=False)
    treatment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    node_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reportable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    epi_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    multi_ip_op: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    node_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sku_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    selected_output: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_output: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    curve_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pfs_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ppc_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    inherent_event: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hierarchy_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    model = relationship("FcModel", back_populates="nodes")
    node_group = relationship("FcModelNodeGroups", back_populates="nodes")
    edges_as_source = relationship(
        "FcModelNodeEdge",
        foreign_keys="FcModelNodeEdge.source_node_id",
        back_populates="source_node",
    )
    edges_as_target = relationship(
        "FcModelNodeEdge",
        foreign_keys="FcModelNodeEdge.target_node_id",
        back_populates="target_node",
    )


# ---------------------------------------------------------------------------
# fc_model_node_edge
# ---------------------------------------------------------------------------
class FcModelNodeEdge(SourceBase):
    __tablename__ = "fc_model_node_edge"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    source_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node.id"), nullable=False
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    source_node = relationship(
        "FcModelNode", foreign_keys=[source_node_id], back_populates="edges_as_source"
    )
    target_node = relationship(
        "FcModelNode", foreign_keys=[target_node_id], back_populates="edges_as_target"
    )


# ---------------------------------------------------------------------------
# fc_model_node_treatment
# ---------------------------------------------------------------------------
class FcModelNodeTreatment(SourceBase):
    __tablename__ = "fc_model_node_treatment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node.id"), nullable=False
    )
    treatment_id: Mapped[str] = mapped_column(String(255), nullable=False)


# ---------------------------------------------------------------------------
# fc_scenario_node_data (append-only)
# ---------------------------------------------------------------------------
class FcScenarioNodeData(SourceBase):
    __tablename__ = "fc_scenario_node_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    model_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node.id"), nullable=False
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario.id"), nullable=False
    )
    input_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    comment: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    input_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_validation_message: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    end_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    scenario = relationship("FcScenario", back_populates="node_data")


# ---------------------------------------------------------------------------
# fc_scenario_run
# ---------------------------------------------------------------------------
class FcScenarioRun(SourceBase):
    __tablename__ = "fc_scenario_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario.id"), nullable=False
    )
    run_status: Mapped[str] = mapped_column(String(50), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    run_by: Mapped[str] = mapped_column(String(255), nullable=False)
    run_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    run_complete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fail_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    scenario = relationship("FcScenario", back_populates="runs")
    branches = relationship("FcScenarioRunBranch", back_populates="scenario_run")


# ---------------------------------------------------------------------------
# fc_scenario_run_branch
# ---------------------------------------------------------------------------
class FcScenarioRunBranch(SourceBase):
    __tablename__ = "fc_scenario_run_branch"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_run.id"), nullable=False
    )
    event_tag: Mapped[str] = mapped_column(String(50), nullable=False)

    scenario_run = relationship("FcScenarioRun", back_populates="branches")
    node_calcs = relationship("FcScenarioNodeCalc", back_populates="run_branch")
    event_calcs = relationship("FcScenarioEventCalc", back_populates="run_branch")


# ---------------------------------------------------------------------------
# fc_scenario_node_calc
# ---------------------------------------------------------------------------
class FcScenarioNodeCalc(SourceBase):
    __tablename__ = "fc_scenario_node_calc"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_run_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_run_branch.id"), nullable=False
    )
    model_node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_model_node.id"), nullable=False
    )
    scenario_node_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_node_data.id"), nullable=False
    )
    processing_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processing_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    processed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    fail_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    run_branch = relationship("FcScenarioRunBranch", back_populates="node_calcs")


# ---------------------------------------------------------------------------
# fc_event_type
# ---------------------------------------------------------------------------
class FcEventType(SourceBase):
    __tablename__ = "fc_event_type"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(50), nullable=False)
    inherent: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    udpated_by: Mapped[str] = mapped_column(String(255), nullable=False)  # note: typo matches source


# ---------------------------------------------------------------------------
# fc_scenario_event_type
# ---------------------------------------------------------------------------
class FcScenarioEventType(SourceBase):
    __tablename__ = "fc_scenario_event_type"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    event_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_event_type.id"), nullable=False
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario.id"), nullable=False
    )

    scenario = relationship("FcScenario", back_populates="event_types")


# ---------------------------------------------------------------------------
# fc_scenario_event_data (append-only)
# ---------------------------------------------------------------------------
class FcScenarioEventData(SourceBase):
    __tablename__ = "fc_scenario_event_data"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_event_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_event_type.id"), nullable=False
    )
    population_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    parent_product_node_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    event_data_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_overridden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    event_shares_overridden: Mapped[dict] = mapped_column(JSONB, nullable=False)
    event_override_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_validated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    input_validation_message: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False)
    created_req_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    end_req_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


# ---------------------------------------------------------------------------
# fc_scenario_event_calc
# ---------------------------------------------------------------------------
class FcScenarioEventCalc(SourceBase):
    __tablename__ = "fc_scenario_event_calc"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    scenario_run_branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_run_branch.id"), nullable=False
    )
    event_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fc_scenario_event_data.id"), nullable=False
    )
    drug_treated_patients: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sob: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    steady_state_share: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    evented_shares: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    run_branch = relationship("FcScenarioRunBranch", back_populates="event_calcs")
