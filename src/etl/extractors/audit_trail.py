"""Extract scenario audit trail data from source database.

Tracks:
- State changes (draft → submitted → locked, etc.)
- Input data modifications
- Event data modifications
- User actions
"""

import uuid
from datetime import datetime
from typing import Iterator

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from src.models.source import (
    FcScenario,
    FcScenarioNodeData,
    FcScenarioRun,
)


def extract_scenario_state_changes(
    session: Session,
    since: datetime | None = None,
    scenario_ids: list[uuid.UUID] | None = None,
) -> Iterator[dict]:
    """Extract scenario lifecycle state transitions.

    Analyzes created_at, submitted_at, locked_at, withdraw_at, delete_at timestamps
    to reconstruct state transition history.

    Args:
        session: Source database session
        since: Extract only changes after this timestamp (for incremental loads)
        scenario_ids: Filter specific scenarios (optional)

    Yields:
        State change records with:
        - scenario_id
        - previous_status
        - new_status
        - transition_type
        - changed_by
        - changed_at
        - correlation_id
    """
    query = select(FcScenario)

    if since:
        query = query.where(
            or_(
                FcScenario.created_at >= since,
                FcScenario.submitted_at >= since,
                FcScenario.locked_at >= since,
                FcScenario.withdraw_at >= since,
                FcScenario.delete_at >= since,
                FcScenario.updated_at >= since,
            )
        )

    if scenario_ids:
        query = query.where(FcScenario.id.in_(scenario_ids))

    scenarios = session.execute(query).scalars().all()

    for scenario in scenarios:
        # Collect all state transitions for this scenario
        transitions = []

        # Created event
        if scenario.created_at:
            transitions.append({
                "scenario_id": scenario.id,
                "previous_status": None,
                "new_status": "draft",
                "transition_type": "created",
                "changed_by": scenario.created_by,
                "changed_at": scenario.created_at,
                "correlation_id": scenario.created_req_id,
                "change_reason": None,
            })

        # Submitted event
        if scenario.submitted_at:
            transitions.append({
                "scenario_id": scenario.id,
                "previous_status": "draft",
                "new_status": "submitted",
                "transition_type": "submitted",
                "changed_by": scenario.submitted_by,
                "changed_at": scenario.submitted_at,
                "correlation_id": scenario.submitted_req_id,
                "change_reason": None,
            })

        # Locked event
        if scenario.locked_at:
            transitions.append({
                "scenario_id": scenario.id,
                "previous_status": "submitted",
                "new_status": "locked",
                "transition_type": "locked",
                "changed_by": scenario.locked_by,
                "changed_at": scenario.locked_at,
                "correlation_id": scenario.locked_req_id,
                "change_reason": None,
            })

        # Withdrawn event
        if scenario.withdraw_at:
            transitions.append({
                "scenario_id": scenario.id,
                "previous_status": scenario.status if scenario.status != "withdrawn" else "submitted",
                "new_status": "withdrawn",
                "transition_type": "withdrawn",
                "changed_by": scenario.withdraw_by,
                "changed_at": scenario.withdraw_at,
                "correlation_id": scenario.withdraw_req_id,
                "change_reason": None,
            })

        # Deleted event
        if scenario.delete_at:
            transitions.append({
                "scenario_id": scenario.id,
                "previous_status": scenario.status if scenario.status != "deleted" else "draft",
                "new_status": "deleted",
                "transition_type": "deleted",
                "changed_by": scenario.delete_by,
                "changed_at": scenario.delete_at,
                "correlation_id": scenario.delete_req_id,
                "change_reason": None,
            })

        # Sort by timestamp and yield
        transitions.sort(key=lambda x: x["changed_at"])
        for transition in transitions:
            yield transition


def extract_user_actions(
    session: Session,
    since: datetime | None = None,
    user_ids: list[str] | None = None,
    scenario_ids: list[uuid.UUID] | None = None,
) -> Iterator[dict]:
    """Extract user actions from multiple source tables.

    Combines:
    - Scenario CRUD operations
    - Input data changes (fc_scenario_node_data)
    - Forecast runs (fc_scenario_run)

    Args:
        session: Source database session
        since: Extract only actions after this timestamp
        user_ids: Filter specific users
        scenario_ids: Filter specific scenarios

    Yields:
        User action records with:
        - user_id
        - scenario_id
        - action_timestamp
        - action_type
        - action_category
        - target_entity_type
        - target_entity_id
        - correlation_id
        - success
        - action_details
    """
    # 1. Scenario management actions
    scenario_query = select(FcScenario)
    if since:
        scenario_query = scenario_query.where(
            or_(
                FcScenario.created_at >= since,
                FcScenario.updated_at >= since,
                FcScenario.submitted_at >= since,
                FcScenario.locked_at >= since,
            )
        )
    if scenario_ids:
        scenario_query = scenario_query.where(FcScenario.id.in_(scenario_ids))

    scenarios = session.execute(scenario_query).scalars().all()

    for scenario in scenarios:
        # Create action
        if scenario.created_at and (not since or scenario.created_at >= since):
            yield {
                "user_id": scenario.created_by,
                "scenario_id": scenario.id,
                "action_timestamp": scenario.created_at,
                "action_type": "create_scenario",
                "action_category": "scenario_mgmt",
                "target_entity_type": "scenario",
                "target_entity_id": scenario.id,
                "correlation_id": scenario.created_req_id,
                "success": True,
                "action_details": {
                    "scenario_name": scenario.scenario_display_name,
                    "is_starter": scenario.is_starter,
                    "start_year": scenario.scenario_start_year,
                    "end_year": scenario.scenario_end_year,
                },
            }

        # Update action
        if scenario.updated_at and scenario.updated_at != scenario.created_at:
            if not since or scenario.updated_at >= since:
                yield {
                    "user_id": scenario.updated_by,
                    "scenario_id": scenario.id,
                    "action_timestamp": scenario.updated_at,
                    "action_type": "update_scenario",
                    "action_category": "scenario_mgmt",
                    "target_entity_type": "scenario",
                    "target_entity_id": scenario.id,
                    "correlation_id": scenario.updated_req_id,
                    "success": True,
                    "action_details": {"status": scenario.status},
                }

        # Submit action
        if scenario.submitted_at and (not since or scenario.submitted_at >= since):
            yield {
                "user_id": scenario.submitted_by,
                "scenario_id": scenario.id,
                "action_timestamp": scenario.submitted_at,
                "action_type": "submit_scenario",
                "action_category": "scenario_mgmt",
                "target_entity_type": "scenario",
                "target_entity_id": scenario.id,
                "correlation_id": scenario.submitted_req_id,
                "success": True,
                "action_details": {},
            }

    # 2. Input data change actions
    input_query = select(FcScenarioNodeData)
    if since:
        input_query = input_query.where(FcScenarioNodeData.created_at >= since)
    if scenario_ids:
        input_query = input_query.where(FcScenarioNodeData.scenario_id.in_(scenario_ids))

    input_changes = session.execute(input_query).scalars().all()

    for input_data in input_changes:
        yield {
            "user_id": input_data.created_by,
            "scenario_id": input_data.scenario_id,
            "action_timestamp": input_data.created_at,
            "action_type": "edit_input_data",
            "action_category": "input_data",
            "target_entity_type": "node_data",
            "target_entity_id": input_data.id,
            "correlation_id": input_data.created_req_id,
            "success": True,
            "action_details": {
                "node_id": str(input_data.model_node_id),
                "input_hash": input_data.input_hash,
                "validated": input_data.input_validated,
            },
        }

    # 3. Forecast run actions
    run_query = select(FcScenarioRun)
    if since:
        run_query = run_query.where(FcScenarioRun.run_at >= since)
    if scenario_ids:
        run_query = run_query.where(FcScenarioRun.scenario_id.in_(scenario_ids))

    runs = session.execute(run_query).scalars().all()

    for run in runs:
        yield {
            "user_id": run.run_by,
            "scenario_id": run.scenario_id,
            "action_timestamp": run.run_at,
            "action_type": "run_forecast",
            "action_category": "forecast_run",
            "target_entity_type": "run",
            "target_entity_id": run.id,
            "correlation_id": run.run_req_id,
            "success": run.run_status == "success",
            "action_details": {
                "run_status": run.run_status,
                "fail_reason": run.fail_reason if run.run_status == "failed" else None,
                "duration_seconds": (
                    (run.run_complete_at - run.run_at).total_seconds()
                    if run.run_complete_at else None
                ),
            },
        }


def extract_input_change_sequence(
    session: Session,
    scenario_id: uuid.UUID,
) -> list[dict]:
    """Extract chronological sequence of input changes for a scenario.

    Useful for reconstructing "what changed between runs" for RCA.

    Args:
        session: Source database session
        scenario_id: Scenario to analyze

    Returns:
        List of input changes with sequence numbers, ordered by timestamp
    """
    query = (
        select(FcScenarioNodeData)
        .where(FcScenarioNodeData.scenario_id == scenario_id)
        .order_by(FcScenarioNodeData.created_at)
    )

    node_data_records = session.execute(query).scalars().all()

    changes = []
    node_sequences = {}  # Track sequence per node

    for record in node_data_records:
        node_id = str(record.model_node_id)

        # Increment sequence for this node
        node_sequences[node_id] = node_sequences.get(node_id, 0) + 1

        changes.append({
            "scenario_id": scenario_id,
            "node_data_id": record.id,
            "model_node_id": record.model_node_id,
            "changed_at": record.created_at,
            "changed_by": record.created_by,
            "input_hash": record.input_hash,
            "is_duplicate": False,  # TODO: Implement hash comparison
            "change_sequence": node_sequences[node_id],
            "correlation_id": record.created_req_id,
        })

    return changes
