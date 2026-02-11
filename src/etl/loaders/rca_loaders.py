"""Load audit trail and RCA data into reporting database."""

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.reporting import (
    DimUser,
    DimScenario,
    FactScenarioStateChange,
    FactUserAction,
    FactCloudWatchLog,
    FactRunDiagnostic,
)


def load_cloudwatch_logs(
    reporting_session: Session,
    logs: Iterable[dict],
    log_group: str,
    environment: str,
    service_name: str = "forecast-service",
) -> int:
    """Load CloudWatch logs into fact table.

    Args:
        reporting_session: Reporting database session
        logs: Iterable of normalized log records
        log_group: CloudWatch log group name
        environment: Environment (dev, sit, uat, prod)
        service_name: Service name

    Returns:
        Number of records loaded
    """
    loaded_count = 0
    now = datetime.now(timezone.utc)

    for log in logs:
        record = FactCloudWatchLog(
            log_timestamp=log["log_timestamp"],
            log_stream=log["log_stream"],
            log_group=log_group,
            severity=log["severity"],
            message=log["message"],
            correlation_id=log.get("correlation_id"),
            scenario_id=log.get("scenario_id"),
            run_id=log.get("run_id"),
            user_id=log.get("user_id"),
            environment=environment,
            service_name=service_name,
            stack_trace=log.get("stack_trace"),
            error_category=log.get("error_category"),
            metadata=log.get("metadata", {}),
            loaded_at=now,
        )

        reporting_session.add(record)
        loaded_count += 1

        # Commit in batches
        if loaded_count % 1000 == 0:
            reporting_session.commit()

    reporting_session.commit()
    return loaded_count


def load_state_changes(
    reporting_session: Session,
    state_changes: Iterable[dict],
) -> int:
    """Load scenario state changes into fact table.

    Args:
        reporting_session: Reporting database session
        state_changes: Iterable of state change records

    Returns:
        Number of records loaded
    """
    loaded_count = 0
    now = datetime.now(timezone.utc)

    # Cache for scenario_key lookups
    scenario_key_cache = {}

    # Cache for user_key lookups
    user_key_cache = {}

    for change in state_changes:
        # Get or cache scenario_key
        scenario_id = change["scenario_id"]
        if scenario_id not in scenario_key_cache:
            result = reporting_session.execute(
                select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
            ).scalar_one_or_none()
            if not result:
                continue  # Skip if scenario not in dim table
            scenario_key_cache[scenario_id] = result
        scenario_key = scenario_key_cache[scenario_id]

        # Get or cache user_key
        user_id = change["changed_by"]
        if user_id not in user_key_cache:
            result = reporting_session.execute(
                select(DimUser.user_key).where(DimUser.user_id == user_id)
            ).scalar_one_or_none()
            if not result:
                # Create user if not exists
                new_user = DimUser(
                    user_id=user_id,
                    display_name=user_id,
                    loaded_at=now,
                )
                reporting_session.add(new_user)
                reporting_session.flush()
                result = new_user.user_key
            user_key_cache[user_id] = result
        user_key = user_key_cache[user_id]

        # Insert state change
        record = FactScenarioStateChange(
            scenario_key=scenario_key,
            scenario_id=scenario_id,
            previous_status=change.get("previous_status"),
            new_status=change["new_status"],
            transition_type=change["transition_type"],
            changed_by_user_key=user_key,
            changed_at=change["changed_at"],
            correlation_id=change["correlation_id"],
            change_reason=change.get("change_reason"),
            metadata=change.get("metadata"),
            loaded_at=now,
        )

        reporting_session.add(record)
        loaded_count += 1

        if loaded_count % 500 == 0:
            reporting_session.commit()

    reporting_session.commit()
    return loaded_count


def load_user_actions(
    reporting_session: Session,
    user_actions: Iterable[dict],
) -> int:
    """Load user actions into fact table.

    Args:
        reporting_session: Reporting database session
        user_actions: Iterable of user action records

    Returns:
        Number of records loaded
    """
    loaded_count = 0
    now = datetime.now(timezone.utc)

    scenario_key_cache = {}
    user_key_cache = {}

    for action in user_actions:
        # Get user_key
        user_id = action["user_id"]
        if user_id not in user_key_cache:
            result = reporting_session.execute(
                select(DimUser.user_key).where(DimUser.user_id == user_id)
            ).scalar_one_or_none()
            if not result:
                new_user = DimUser(user_id=user_id, display_name=user_id, loaded_at=now)
                reporting_session.add(new_user)
                reporting_session.flush()
                result = new_user.user_key
            user_key_cache[user_id] = result
        user_key = user_key_cache[user_id]

        # Get scenario_key (optional)
        scenario_key = None
        if action.get("scenario_id"):
            scenario_id = action["scenario_id"]
            if scenario_id not in scenario_key_cache:
                result = reporting_session.execute(
                    select(DimScenario.scenario_key).where(DimScenario.scenario_id == scenario_id)
                ).scalar_one_or_none()
                if result:
                    scenario_key_cache[scenario_id] = result
            scenario_key = scenario_key_cache.get(scenario_id)

        # Insert action
        record = FactUserAction(
            user_key=user_key,
            scenario_key=scenario_key,
            action_timestamp=action["action_timestamp"],
            action_type=action["action_type"],
            action_category=action["action_category"],
            target_entity_type=action.get("target_entity_type"),
            target_entity_id=action.get("target_entity_id"),
            correlation_id=action["correlation_id"],
            request_endpoint=action.get("request_endpoint"),
            http_method=action.get("http_method"),
            request_duration_ms=action.get("request_duration_ms"),
            success=action.get("success", True),
            error_message=action.get("error_message"),
            action_details=action.get("action_details"),
            loaded_at=now,
        )

        reporting_session.add(record)
        loaded_count += 1

        if loaded_count % 500 == 0:
            reporting_session.commit()

    reporting_session.commit()
    return loaded_count


def load_run_diagnostics(
    reporting_session: Session,
    diagnostics: Iterable[dict],
) -> int:
    """Load run diagnostic records into fact table.

    Args:
        reporting_session: Reporting database session
        diagnostics: Iterable of diagnostic records

    Returns:
        Number of records loaded
    """
    loaded_count = 0
    now = datetime.now(timezone.utc)

    for diag in diagnostics:
        record = FactRunDiagnostic(
            run_fact_key=diag["run_fact_key"],
            run_id=diag["run_id"],
            scenario_key=diag["scenario_key"],
            diagnostic_type=diag["diagnostic_type"],
            node_key=diag.get("node_key"),
            severity=diag["severity"],
            diagnostic_category=diag["diagnostic_category"],
            diagnostic_message=diag["diagnostic_message"],
            diagnostic_details=diag.get("diagnostic_details"),
            input_hash_at_run=diag.get("input_hash_at_run"),
            correlation_id=diag["correlation_id"],
            cloudwatch_log_references=diag.get("cloudwatch_log_references"),
            loaded_at=now,
        )

        reporting_session.add(record)
        loaded_count += 1

        if loaded_count % 500 == 0:
            reporting_session.commit()

    reporting_session.commit()
    return loaded_count
