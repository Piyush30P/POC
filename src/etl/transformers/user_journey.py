"""Transform audit trail data into user journey timelines.

Reconstructs:
- Chronological view of user actions
- Input state at time of run
- Comparison between working vs failing runs
- User session patterns
"""

import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterator


def reconstruct_user_journey(
    state_changes: list[dict],
    user_actions: list[dict],
    input_changes: list[dict],
    runs: list[dict],
) -> list[dict]:
    """Merge and sort all audit events into chronological user journey.

    Args:
        state_changes: Scenario state transition events
        user_actions: User action events
        input_changes: Input data modification events
        runs: Forecast run events

    Returns:
        Sorted timeline of all events with unified schema:
        - event_timestamp
        - event_type
        - event_category
        - user_id
        - scenario_id
        - correlation_id
        - event_description
        - event_metadata
    """
    timeline = []

    # Add state changes
    for change in state_changes:
        timeline.append({
            "event_timestamp": change["changed_at"],
            "event_type": "state_change",
            "event_category": "scenario_mgmt",
            "user_id": change["changed_by"],
            "scenario_id": change["scenario_id"],
            "correlation_id": change["correlation_id"],
            "event_description": f"Scenario status changed from {change['previous_status']} to {change['new_status']}",
            "event_metadata": {
                "transition_type": change["transition_type"],
                "previous_status": change["previous_status"],
                "new_status": change["new_status"],
            },
        })

    # Add user actions
    for action in user_actions:
        timeline.append({
            "event_timestamp": action["action_timestamp"],
            "event_type": "user_action",
            "event_category": action["action_category"],
            "user_id": action["user_id"],
            "scenario_id": action.get("scenario_id"),
            "correlation_id": action["correlation_id"],
            "event_description": f"User performed: {action['action_type']}",
            "event_metadata": {
                "action_type": action["action_type"],
                "target_entity_type": action.get("target_entity_type"),
                "target_entity_id": str(action.get("target_entity_id")) if action.get("target_entity_id") else None,
                "success": action.get("success", True),
                **action.get("action_details", {}),
            },
        })

    # Add input changes
    for change in input_changes:
        timeline.append({
            "event_timestamp": change["changed_at"],
            "event_type": "input_change",
            "event_category": "input_data",
            "user_id": change["changed_by"],
            "scenario_id": change["scenario_id"],
            "correlation_id": change["correlation_id"],
            "event_description": f"Modified input for node (sequence {change['change_sequence']})",
            "event_metadata": {
                "node_id": str(change["model_node_id"]),
                "input_hash": change["input_hash"],
                "change_sequence": change["change_sequence"],
                "is_duplicate": change.get("is_duplicate", False),
            },
        })

    # Add runs
    for run in runs:
        timeline.append({
            "event_timestamp": run["run_started_at"],
            "event_type": "run_started",
            "event_category": "forecast_run",
            "user_id": run["run_by"],
            "scenario_id": run["scenario_id"],
            "correlation_id": run.get("correlation_id", run["run_id"]),
            "event_description": f"Forecast run started",
            "event_metadata": {
                "run_id": str(run["run_id"]),
                "run_status": run["run_status"],
            },
        })

        if run.get("run_ended_at"):
            timeline.append({
                "event_timestamp": run["run_ended_at"],
                "event_type": "run_completed",
                "event_category": "forecast_run",
                "user_id": run["run_by"],
                "scenario_id": run["scenario_id"],
                "correlation_id": run.get("correlation_id", run["run_id"]),
                "event_description": f"Forecast run completed: {run['run_status']}",
                "event_metadata": {
                    "run_id": str(run["run_id"]),
                    "run_status": run["run_status"],
                    "duration_seconds": run.get("duration_seconds"),
                    "fail_reason": run.get("fail_reason"),
                },
            })

    # Sort chronologically
    timeline.sort(key=lambda x: x["event_timestamp"])

    return timeline


def identify_run_context_changes(
    scenario_id: uuid.UUID,
    target_run_id: uuid.UUID,
    all_runs: list[dict],
    input_changes: list[dict],
) -> dict:
    """Find what changed between the last successful run and target run.

    Critical for RCA: "What was different this time?"

    Args:
        scenario_id: Scenario UUID
        target_run_id: Run to analyze
        all_runs: All runs for this scenario (sorted by time)
        input_changes: All input changes for this scenario

    Returns:
        Context diff with:
        - previous_successful_run
        - target_run
        - input_changes_between (list of changes)
        - time_gap (seconds between runs)
        - changed_node_ids
    """
    # Filter runs for this scenario
    scenario_runs = [r for r in all_runs if r["scenario_id"] == scenario_id]
    scenario_runs.sort(key=lambda x: x["run_started_at"])

    # Find target run
    target_run = next((r for r in scenario_runs if r["run_id"] == target_run_id), None)
    if not target_run:
        return {"error": "Target run not found"}

    # Find last successful run before target
    previous_successful = None
    for run in reversed(scenario_runs):
        if run["run_started_at"] < target_run["run_started_at"] and run["run_status"] == "success":
            previous_successful = run
            break

    if not previous_successful:
        return {
            "target_run": target_run,
            "previous_successful_run": None,
            "input_changes_between": [],
            "message": "No previous successful run found",
        }

    # Find input changes between the two runs
    changes_between = [
        change for change in input_changes
        if previous_successful["run_started_at"] < change["changed_at"] <= target_run["run_started_at"]
    ]

    changed_node_ids = list({str(change["model_node_id"]) for change in changes_between})

    time_gap = (target_run["run_started_at"] - previous_successful["run_started_at"]).total_seconds()

    return {
        "target_run": {
            "run_id": str(target_run["run_id"]),
            "status": target_run["run_status"],
            "started_at": target_run["run_started_at"].isoformat(),
            "fail_reason": target_run.get("fail_reason"),
        },
        "previous_successful_run": {
            "run_id": str(previous_successful["run_id"]),
            "status": previous_successful["run_status"],
            "started_at": previous_successful["run_started_at"].isoformat(),
        },
        "input_changes_between": len(changes_between),
        "changed_node_ids": changed_node_ids,
        "time_gap_seconds": time_gap,
        "changes_detail": [
            {
                "node_id": str(c["model_node_id"]),
                "changed_at": c["changed_at"].isoformat(),
                "changed_by": c["changed_by"],
                "input_hash": c["input_hash"],
            }
            for c in changes_between
        ],
    }


def group_actions_by_session(
    user_actions: list[dict],
    session_gap_minutes: int = 30,
) -> list[dict]:
    """Group user actions into logical sessions.

    A session ends when gap between actions exceeds threshold.

    Args:
        user_actions: User action events
        session_gap_minutes: Minutes of inactivity to end session

    Returns:
        List of sessions with:
        - session_id
        - user_id
        - scenario_id
        - started_at
        - ended_at
        - action_count
        - action_types (summary)
    """
    if not user_actions:
        return []

    # Sort by user and timestamp
    actions = sorted(user_actions, key=lambda x: (x["user_id"], x["action_timestamp"]))

    sessions = []
    current_session = None
    session_gap = timedelta(minutes=session_gap_minutes)

    for action in actions:
        # Start new session if:
        # - First action
        # - Different user
        # - Time gap exceeds threshold
        if (
            current_session is None
            or current_session["user_id"] != action["user_id"]
            or (action["action_timestamp"] - current_session["last_action_at"]) > session_gap
        ):
            if current_session:
                # Finalize previous session
                sessions.append({
                    "session_id": str(uuid.uuid4()),
                    "user_id": current_session["user_id"],
                    "scenario_ids": list(current_session["scenario_ids"]),
                    "started_at": current_session["started_at"],
                    "ended_at": current_session["last_action_at"],
                    "duration_minutes": (
                        (current_session["last_action_at"] - current_session["started_at"]).total_seconds() / 60
                    ),
                    "action_count": current_session["action_count"],
                    "action_types": dict(current_session["action_types"]),
                })

            # Start new session
            current_session = {
                "user_id": action["user_id"],
                "scenario_ids": {action.get("scenario_id")} if action.get("scenario_id") else set(),
                "started_at": action["action_timestamp"],
                "last_action_at": action["action_timestamp"],
                "action_count": 0,
                "action_types": defaultdict(int),
            }

        # Add action to current session
        current_session["action_count"] += 1
        current_session["last_action_at"] = action["action_timestamp"]
        current_session["action_types"][action["action_type"]] += 1
        if action.get("scenario_id"):
            current_session["scenario_ids"].add(action["scenario_id"])

    # Finalize last session
    if current_session:
        sessions.append({
            "session_id": str(uuid.uuid4()),
            "user_id": current_session["user_id"],
            "scenario_ids": list(current_session["scenario_ids"]),
            "started_at": current_session["started_at"],
            "ended_at": current_session["last_action_at"],
            "duration_minutes": (
                (current_session["last_action_at"] - current_session["started_at"]).total_seconds() / 60
            ),
            "action_count": current_session["action_count"],
            "action_types": dict(current_session["action_types"]),
        })

    return sessions


def calculate_user_velocity_metrics(
    user_actions: list[dict],
    user_id: str,
    time_window_days: int = 30,
) -> dict:
    """Calculate user activity velocity metrics.

    Useful for identifying power users vs occasional users.

    Args:
        user_actions: All user actions
        user_id: User to analyze
        time_window_days: Rolling window for metrics

    Returns:
        Metrics dict with:
        - total_actions
        - actions_per_day
        - scenarios_touched
        - most_common_action
        - avg_session_duration_minutes
    """
    user_actions_filtered = [a for a in user_actions if a["user_id"] == user_id]

    if not user_actions_filtered:
        return {"user_id": user_id, "total_actions": 0}

    # Time window filter
    cutoff = datetime.now() - timedelta(days=time_window_days)
    recent_actions = [a for a in user_actions_filtered if a["action_timestamp"] >= cutoff]

    # Count action types
    action_types = defaultdict(int)
    scenario_ids = set()

    for action in recent_actions:
        action_types[action["action_type"]] += 1
        if action.get("scenario_id"):
            scenario_ids.add(action["scenario_id"])

    most_common_action = max(action_types.items(), key=lambda x: x[1])[0] if action_types else None

    # Session metrics
    sessions = group_actions_by_session(recent_actions)
    avg_session_duration = (
        sum(s["duration_minutes"] for s in sessions) / len(sessions)
        if sessions else 0
    )

    return {
        "user_id": user_id,
        "time_window_days": time_window_days,
        "total_actions": len(recent_actions),
        "actions_per_day": len(recent_actions) / max(time_window_days, 1),
        "scenarios_touched": len(scenario_ids),
        "most_common_action": most_common_action,
        "action_type_distribution": dict(action_types),
        "session_count": len(sessions),
        "avg_session_duration_minutes": round(avg_session_duration, 2),
    }
