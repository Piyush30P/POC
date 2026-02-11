"""FastAPI endpoints for RCA Dashboard and Power BI integration.

Provides:
- Scenario audit trail timeline
- User journey reconstruction
- Run diagnostics and comparisons
- Error aggregation views
"""

import uuid
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.reporting_engine import get_reporting_async_session
from src.models.reporting import (
    DimScenario,
    DimUser,
    DimNode,
    FactScenarioRun,
    FactScenarioStateChange,
    FactUserAction,
    FactCloudWatchLog,
    FactRunDiagnostic,
    FactScenarioInputChange,
    ViewScenarioAuditTrail,
)

router = APIRouter(prefix="/api/v1/rca", tags=["RCA Dashboard"])


# ===================================================================
# SCENARIO AUDIT TRAIL
# ===================================================================


@router.get("/scenario/{scenario_id}/audit-trail")
async def get_scenario_audit_trail(
    scenario_id: uuid.UUID,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    event_types: Annotated[list[str] | None, Query()] = None,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get complete audit trail for a scenario.

    Returns chronological timeline of:
    - State changes (created, submitted, locked, etc.)
    - Input modifications
    - Forecast runs
    - User actions

    **Power BI Usage**: Use as main data source for timeline visual.
    """
    # Get scenario_key
    result = await session.execute(
        select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
    )
    scenario_key = result.scalar_one_or_none()

    if not scenario_key:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Build query for audit trail view
    query = select(ViewScenarioAuditTrail).where(
        ViewScenarioAuditTrail.scenario_key == scenario_key
    )

    if start_date:
        query = query.where(ViewScenarioAuditTrail.event_timestamp >= start_date)
    if end_date:
        query = query.where(ViewScenarioAuditTrail.event_timestamp <= end_date)
    if event_types:
        query = query.where(ViewScenarioAuditTrail.event_type.in_(event_types))

    query = query.order_by(ViewScenarioAuditTrail.event_timestamp)

    result = await session.execute(query)
    events = result.scalars().all()

    return {
        "scenario_id": str(scenario_id),
        "event_count": len(events),
        "events": [
            {
                "timestamp": event.event_timestamp.isoformat(),
                "event_type": event.event_type,
                "category": event.event_category,
                "user": event.user_id,
                "description": event.event_description,
                "correlation_id": str(event.correlation_id),
                "metadata": event.event_metadata,
            }
            for event in events
        ],
    }


@router.get("/scenario/{scenario_id}/state-changes")
async def get_scenario_state_changes(
    scenario_id: uuid.UUID,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get all state transitions for a scenario.

    Shows scenario lifecycle: draft → submitted → locked.

    **Power BI Usage**: Visualize state transition flow diagrams.
    """
    result = await session.execute(
        select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
    )
    scenario_key = result.scalar_one_or_none()

    if not scenario_key:
        raise HTTPException(status_code=404, detail="Scenario not found")

    query = (
        select(FactScenarioStateChange, DimUser.user_id)
        .join(DimUser, FactScenarioStateChange.changed_by_user_key == DimUser.user_key)
        .where(FactScenarioStateChange.scenario_key == scenario_key)
        .order_by(FactScenarioStateChange.changed_at)
    )

    result = await session.execute(query)
    changes = result.all()

    return {
        "scenario_id": str(scenario_id),
        "state_changes": [
            {
                "previous_status": change[0].previous_status,
                "new_status": change[0].new_status,
                "transition_type": change[0].transition_type,
                "changed_by": change[1],
                "changed_at": change[0].changed_at.isoformat(),
                "correlation_id": str(change[0].correlation_id),
                "reason": change[0].change_reason,
            }
            for change in changes
        ],
    }


# ===================================================================
# USER JOURNEY & SESSION ANALYSIS
# ===================================================================


@router.get("/user/{user_id}/journey")
async def get_user_journey(
    user_id: str,
    days: int = 30,
    scenario_id: uuid.UUID | None = None,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get chronological user action timeline.

    **Power BI Usage**: Filter by user and scenario to reconstruct debugging sessions.
    """
    # Get user_key
    result = await session.execute(
        select(DimUser.user_key).where(DimUser.user_id == user_id)
    )
    user_key = result.scalar_one_or_none()

    if not user_key:
        raise HTTPException(status_code=404, detail="User not found")

    # Build query
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = select(FactUserAction).where(
        and_(
            FactUserAction.user_key == user_key,
            FactUserAction.action_timestamp >= cutoff,
        )
    )

    if scenario_id:
        result = await session.execute(
            select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
        )
        scenario_key = result.scalar_one_or_none()
        if scenario_key:
            query = query.where(FactUserAction.scenario_key == scenario_key)

    query = query.order_by(FactUserAction.action_timestamp)

    result = await session.execute(query)
    actions = result.scalars().all()

    return {
        "user_id": user_id,
        "days_analyzed": days,
        "action_count": len(actions),
        "actions": [
            {
                "timestamp": action.action_timestamp.isoformat(),
                "action_type": action.action_type,
                "category": action.action_category,
                "target_entity": action.target_entity_type,
                "success": action.success,
                "duration_ms": float(action.request_duration_ms) if action.request_duration_ms else None,
                "error": action.error_message,
                "details": action.action_details,
            }
            for action in actions
        ],
    }


# ===================================================================
# RUN DIAGNOSTICS & COMPARISON
# ===================================================================


@router.get("/run/{run_id}/diagnostics")
async def get_run_diagnostics(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get detailed diagnostics for a forecast run.

    Includes:
    - Input snapshot at time of run
    - Error messages and categories
    - Node-level failures
    - Related CloudWatch logs

    **Power BI Usage**: Drill-through page for run-level RCA.
    """
    # Get run fact
    result = await session.execute(
        select(FactScenarioRun).where(FactScenarioRun.run_id == run_id)
    )
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get diagnostics
    diag_query = select(FactRunDiagnostic, DimNode.node_name).outerjoin(
        DimNode, FactRunDiagnostic.node_key == DimNode.node_key
    ).where(FactRunDiagnostic.run_id == run_id)

    result = await session.execute(diag_query)
    diagnostics = result.all()

    # Get related CloudWatch logs
    log_query = (
        select(FactCloudWatchLog)
        .where(FactCloudWatchLog.run_id == run_id)
        .order_by(FactCloudWatchLog.log_timestamp)
    )
    result = await session.execute(log_query)
    logs = result.scalars().all()

    return {
        "run_id": str(run_id),
        "run_status": run.run_status,
        "started_at": run.run_started_at.isoformat(),
        "ended_at": run.run_ended_at.isoformat() if run.run_ended_at else None,
        "duration_seconds": float(run.duration_seconds) if run.duration_seconds else None,
        "fail_reason": run.fail_reason,
        "diagnostics": [
            {
                "type": diag[0].diagnostic_type,
                "category": diag[0].diagnostic_category,
                "severity": diag[0].severity,
                "node_name": diag[1],
                "message": diag[0].diagnostic_message,
                "details": diag[0].diagnostic_details,
            }
            for diag in diagnostics
        ],
        "cloudwatch_logs": [
            {
                "timestamp": log.log_timestamp.isoformat(),
                "severity": log.severity,
                "message": log.message[:500],  # Truncate for API
                "error_category": log.error_category,
                "stack_trace": bool(log.stack_trace),
            }
            for log in logs
        ],
    }


@router.get("/scenario/{scenario_id}/run-comparison")
async def compare_runs(
    scenario_id: uuid.UUID,
    run_a_id: uuid.UUID,
    run_b_id: uuid.UUID,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Compare two runs to identify what changed.

    **Power BI Usage**: "Last working vs first failing" comparison view.
    """
    # Get scenario_key
    result = await session.execute(
        select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
    )
    scenario_key = result.scalar_one_or_none()

    if not scenario_key:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get both runs
    result = await session.execute(
        select(FactScenarioRun).where(FactScenarioRun.run_id.in_([run_a_id, run_b_id]))
    )
    runs = result.scalars().all()

    if len(runs) != 2:
        raise HTTPException(status_code=404, detail="One or both runs not found")

    run_a = next(r for r in runs if r.run_id == run_a_id)
    run_b = next(r for r in runs if r.run_id == run_b_id)

    # Get input changes between runs
    earlier_time = min(run_a.run_started_at, run_b.run_started_at)
    later_time = max(run_a.run_started_at, run_b.run_started_at)

    input_changes_query = (
        select(FactScenarioInputChange, DimNode.node_name)
        .join(DimNode, FactScenarioInputChange.node_key == DimNode.node_key)
        .where(
            and_(
                FactScenarioInputChange.scenario_key == scenario_key,
                FactScenarioInputChange.changed_at > earlier_time,
                FactScenarioInputChange.changed_at <= later_time,
            )
        )
    )

    result = await session.execute(input_changes_query)
    input_changes = result.all()

    return {
        "scenario_id": str(scenario_id),
        "run_a": {
            "run_id": str(run_a.run_id),
            "status": run_a.run_status,
            "started_at": run_a.run_started_at.isoformat(),
            "duration_seconds": float(run_a.duration_seconds) if run_a.duration_seconds else None,
            "node_failures": run_a.node_calc_failed,
        },
        "run_b": {
            "run_id": str(run_b.run_id),
            "status": run_b.run_status,
            "started_at": run_b.run_started_at.isoformat(),
            "duration_seconds": float(run_b.duration_seconds) if run_b.duration_seconds else None,
            "node_failures": run_b.node_calc_failed,
        },
        "time_gap_seconds": (later_time - earlier_time).total_seconds(),
        "input_changes_between": len(input_changes),
        "changed_nodes": [
            {
                "node_name": change[1],
                "changed_at": change[0].changed_at.isoformat(),
                "input_hash": change[0].new_input_hash,
            }
            for change in input_changes
        ],
    }


# ===================================================================
# ERROR AGGREGATION & RELIABILITY
# ===================================================================


@router.get("/errors/top-categories")
async def get_top_error_categories(
    days: int = 30,
    limit: int = 10,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get most common error categories across all runs.

    **Power BI Usage**: Error category distribution pie chart.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            FactCloudWatchLog.error_category,
            func.count(FactCloudWatchLog.log_fact_key).label("count"),
        )
        .where(
            and_(
                FactCloudWatchLog.severity == "ERROR",
                FactCloudWatchLog.error_category.isnot(None),
                FactCloudWatchLog.log_timestamp >= cutoff,
            )
        )
        .group_by(FactCloudWatchLog.error_category)
        .order_by(desc("count"))
        .limit(limit)
    )

    result = await session.execute(query)
    categories = result.all()

    return {
        "days_analyzed": days,
        "top_categories": [
            {"category": cat[0], "count": cat[1]}
            for cat in categories
        ],
    }


@router.get("/scenario/{scenario_id}/error-summary")
async def get_scenario_error_summary(
    scenario_id: uuid.UUID,
    session: AsyncSession = Depends(get_reporting_async_session),
):
    """Get aggregated error summary for a scenario.

    **Power BI Usage**: Scenario-level error overview card.
    """
    result = await session.execute(
        select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
    )
    scenario_key = result.scalar_one_or_none()

    if not scenario_key:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get all runs for this scenario
    runs_query = select(FactScenarioRun).where(
        FactScenarioRun.scenario_key == scenario_key
    )
    result = await session.execute(runs_query)
    runs = result.scalars().all()

    total_runs = len(runs)
    failed_runs = sum(1 for r in runs if r.run_status == "failed")
    total_node_failures = sum(r.node_calc_failed for r in runs)

    # Get error logs for this scenario
    error_logs_query = (
        select(
            FactCloudWatchLog.error_category,
            func.count(FactCloudWatchLog.log_fact_key).label("count"),
        )
        .where(
            and_(
                FactCloudWatchLog.scenario_id == scenario_id,
                FactCloudWatchLog.severity == "ERROR",
            )
        )
        .group_by(FactCloudWatchLog.error_category)
        .order_by(desc("count"))
    )

    result = await session.execute(error_logs_query)
    error_categories = result.all()

    return {
        "scenario_id": str(scenario_id),
        "total_runs": total_runs,
        "failed_runs": failed_runs,
        "success_rate": round((total_runs - failed_runs) / total_runs * 100, 2) if total_runs > 0 else 0,
        "total_node_failures": total_node_failures,
        "error_categories": [
            {"category": cat[0] or "uncategorized", "count": cat[1]}
            for cat in error_categories
        ],
    }
