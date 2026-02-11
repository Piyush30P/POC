"""Factory for generating fc_scenario_run, fc_scenario_run_branch,
fc_scenario_node_calc, and fc_scenario_event_calc records."""

import uuid
from datetime import datetime, timedelta, timezone

from src.seed.profiles import SeedProfile

ERROR_MESSAGES = [
    "Division by zero in column 'market_share'",
    "Missing required input: 'treatment_uptake_curve'",
    "Value out of bounds: growth_rate=-0.5 (min: 0.0)",
    "Timeout after 300s: node dependency cycle detected",
    "Data type mismatch: expected float, got string 'N/A'",
    "Null value in non-nullable field 'base_share'",
    "Invalid date range: start_year > end_year",
    "Circular dependency detected between nodes",
    "Memory limit exceeded during calculation",
    "API timeout: forecast engine did not respond within 60s",
    "Input validation failed: negative patient count",
    "Schema mismatch: unexpected key 'extra_param'",
    "Calculation overflow: result exceeds float64 range",
    "Missing upstream dependency: node 'epi_1.3' has no output",
    "Concurrency conflict: data was modified by another process",
]

ERROR_CATEGORIES = [
    "calculation_error",
    "missing_input",
    "data_validation",
    "timeout",
    "dependency_error",
    "data_validation",
    "data_validation",
    "dependency_error",
    "calculation_error",
    "timeout",
    "data_validation",
    "data_validation",
    "calculation_error",
    "dependency_error",
    "concurrency_error",
]

EVENT_TAGS = ["with events", "without events", "inherent events"]

USERS = [
    "jdoe", "asmith", "mwilson", "kbrown", "ljohnson",
    "rgarcia", "tlee", "pchen", "nkumar", "hzhang",
]


def generate_runs_for_scenario(
    scenario: dict,
    node_data_by_scenario: dict[uuid.UUID, list[dict]],
    profile: SeedProfile,
    rng,
) -> dict:
    """Generate run records for a single scenario.

    Returns dict with keys: runs, branches, node_calcs
    """
    runs = []
    branches = []
    node_calcs = []

    scenario_id = scenario["id"]
    node_data_rows = node_data_by_scenario.get(scenario_id, [])
    if not node_data_rows:
        return {"runs": runs, "branches": branches, "node_calcs": node_calcs}

    num_runs = rng.randint(profile.runs_per_scenario_min, profile.runs_per_scenario_max)
    scenario_created = scenario["created_at"]

    for run_idx in range(num_runs):
        run_id = uuid.uuid4()
        run_at = scenario_created + timedelta(
            hours=rng.randint(2, 48) * (run_idx + 1)
        )
        user = rng.choice(USERS)

        # Determine run status
        roll = rng.random()
        if roll < profile.run_success_rate:
            run_status = "success"
        elif roll < profile.run_success_rate + profile.run_timeout_rate:
            run_status = "timeout"
        else:
            run_status = "failed"

        # Duration
        if run_status == "timeout":
            duration_seconds = rng.uniform(280, 320)
        elif run_status == "success":
            duration_seconds = rng.uniform(10, 120)
        else:
            duration_seconds = rng.uniform(5, 200)

        run_complete_at = run_at + timedelta(seconds=duration_seconds)

        fail_reason = None
        if run_status in ("failed", "timeout"):
            err_idx = rng.randint(0, len(ERROR_MESSAGES) - 1)
            fail_reason = ERROR_MESSAGES[err_idx]

        run = {
            "id": run_id,
            "scenario_id": scenario_id,
            "run_status": run_status,
            "run_at": run_at,
            "run_by": user,
            "run_req_id": uuid.uuid4(),
            "run_complete_at": run_complete_at,
            "fail_reason": fail_reason,
        }
        runs.append(run)

        # Generate branches (1-3 per run)
        num_branches = rng.randint(1, min(3, len(EVENT_TAGS)))
        branch_tags = rng.sample(EVENT_TAGS, num_branches)

        for tag in branch_tags:
            branch_id = uuid.uuid4()
            branches.append({
                "id": branch_id,
                "scenario_run_id": run_id,
                "event_tag": tag,
            })

            # Generate node calcs for this branch
            # Use the latest node data row per node at time of run
            latest_data = _get_latest_node_data_at(node_data_rows, run_at)

            for nd in latest_data:
                calc_status = "success"
                calc_fail_reason = None
                processing_ms = rng.uniform(50, 5000)

                if run_status == "failed" and rng.random() < profile.node_calc_failure_rate * 3:
                    calc_status = "failed"
                    err_idx = rng.randint(0, len(ERROR_MESSAGES) - 1)
                    calc_fail_reason = ERROR_MESSAGES[err_idx]
                elif run_status == "timeout" and rng.random() < 0.3:
                    calc_status = "timeout"
                    processing_ms = rng.uniform(290000, 310000)
                elif rng.random() < profile.node_calc_failure_rate:
                    calc_status = "failed"
                    err_idx = rng.randint(0, len(ERROR_MESSAGES) - 1)
                    calc_fail_reason = ERROR_MESSAGES[err_idx]

                proc_start = run_at + timedelta(milliseconds=rng.uniform(100, 2000))
                proc_end = proc_start + timedelta(milliseconds=processing_ms)

                output_data = None
                if calc_status == "success":
                    output_data = _generate_output_data(rng)

                node_calcs.append({
                    "id": uuid.uuid4(),
                    "scenario_run_branch_id": branch_id,
                    "model_node_id": nd["model_node_id"],
                    "scenario_node_data_id": nd["id"],
                    "processing_start_at": proc_start,
                    "processing_end_at": proc_end,
                    "output_data": output_data,
                    "processed": calc_status == "success",
                    "status": calc_status,
                    "fail_reason": calc_fail_reason,
                    "created_at": proc_end,
                    "updated_at": proc_end,
                })

    return {"runs": runs, "branches": branches, "node_calcs": node_calcs}


def _get_latest_node_data_at(
    node_data_rows: list[dict],
    as_of: datetime,
) -> list[dict]:
    """Get the latest node_data row per model_node_id that existed at a given time."""
    latest: dict[uuid.UUID, dict] = {}
    for row in node_data_rows:
        if row["created_at"] <= as_of:
            node_id = row["model_node_id"]
            if node_id not in latest or row["created_at"] > latest[node_id]["created_at"]:
                latest[node_id] = row
    return list(latest.values())


def _generate_output_data(rng) -> dict:
    """Generate realistic output JSONB for a successful node calc."""
    years = list(range(2025, 2031))
    return {
        "forecast_years": years,
        "patients": [rng.randint(100, 50000) for _ in years],
        "revenue_usd": [round(rng.uniform(1e5, 1e8), 2) for _ in years],
        "market_share": [round(rng.uniform(0.01, 0.60), 4) for _ in years],
        "units": [rng.randint(1000, 500000) for _ in years],
    }
