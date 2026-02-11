"""Factory for generating fc_forecast_init, fc_scenario, and
fc_scenario_node_data (append-only edit histories)."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone

from faker import Faker

from src.seed.profiles import SeedProfile

fake = Faker()

SCENARIO_STATUSES = ["draft", "submitted", "locked", "withdrawn", "deleted"]
CURRENCIES = ["USD", "LC"]

USERS = [
    "jdoe", "asmith", "mwilson", "kbrown", "ljohnson",
    "rgarcia", "tlee", "pchen", "nkumar", "hzhang",
]

INPUT_KEYS = [
    "base_share", "growth_rate", "peak_share", "time_to_peak",
    "decline_rate", "market_size", "treatment_uptake", "compliance_rate",
    "price_per_unit", "units_per_patient", "patients_per_year",
    "switch_rate", "discontinuation_rate", "line_of_therapy",
    "dosing_frequency", "treatment_duration",
]


def _compute_hash(data: dict) -> str:
    return hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()


def _generate_input_data(rng, keys: list[str] | None = None) -> dict:
    """Generate realistic JSONB input data for a node."""
    if keys is None:
        num_keys = rng.randint(5, 12)
        keys = rng.sample(INPUT_KEYS, min(num_keys, len(INPUT_KEYS)))

    data = {}
    for key in keys:
        if "rate" in key or "share" in key:
            data[key] = round(rng.uniform(0.01, 0.99), 4)
        elif "size" in key or "patients" in key:
            data[key] = rng.randint(1000, 1000000)
        elif "price" in key:
            data[key] = round(rng.uniform(100, 50000), 2)
        elif "time" in key or "duration" in key or "frequency" in key:
            data[key] = rng.randint(1, 52)
        elif "line" in key:
            data[key] = rng.choice(["1L", "2L", "3L", "4L+"])
        else:
            data[key] = round(rng.uniform(0.1, 100.0), 3)

    return data


def _mutate_input_data(data: dict, rng) -> dict:
    """Slightly modify existing input data to simulate a user edit."""
    new_data = data.copy()
    keys = list(new_data.keys())
    if not keys:
        return new_data

    # Change 1-3 keys
    num_changes = rng.randint(1, min(3, len(keys)))
    changed_keys = rng.sample(keys, num_changes)

    for key in changed_keys:
        val = new_data[key]
        if isinstance(val, (int, float)):
            # Adjust by -20% to +20%
            factor = rng.uniform(0.8, 1.2)
            if isinstance(val, int):
                new_data[key] = max(1, int(val * factor))
            else:
                new_data[key] = round(val * factor, 4)
        elif isinstance(val, str) and val in ("1L", "2L", "3L", "4L+"):
            new_data[key] = rng.choice(["1L", "2L", "3L", "4L+"])

    # Occasionally add a new key
    if rng.random() < 0.1:
        unused_keys = [k for k in INPUT_KEYS if k not in new_data]
        if unused_keys:
            new_key = rng.choice(unused_keys)
            new_data[new_key] = round(rng.uniform(0.01, 100.0), 3)

    return new_data


def generate_forecast_inits(
    models: list[dict],
    profile: SeedProfile,
    rng,
) -> list[dict]:
    """Generate fc_forecast_init records for each model."""
    forecast_inits = []
    cycle_names = ["May 5YP", "August Review", "November Budget", "Q1 Demand", "Q3 Update"]

    for model in models:
        for c in range(profile.forecast_cycles_per_model):
            base_date = datetime(2025, 1 + c * 4, 1, tzinfo=timezone.utc)
            user = rng.choice(USERS)
            forecast_inits.append({
                "id": uuid.uuid4(),
                "model_id": model["id"],
                "forecast_cycle_id": uuid.uuid4(),
                "starter_created": False,
                "forecast_cycle_display_name": cycle_names[c % len(cycle_names)],
                "forecast_cycle_start_dt": base_date,
                "forecast_cycle_end_dt": base_date + timedelta(days=90),
                "horizon_start_limit": 2025,
                "horizon_end_limit": 2030,
                "initiated_at": base_date + timedelta(hours=rng.randint(1, 48)),
                "initiated_by": user,
                "initiated_req_id": uuid.uuid4(),
            })

    return forecast_inits


def generate_scenarios(
    forecast_inits: list[dict],
    profile: SeedProfile,
    rng,
) -> list[dict]:
    """Generate fc_scenario records for each forecast init."""
    scenarios = []
    core_scenario_names = ["Base", "Upside", "Downside", "Custom"]

    for fi in forecast_inits:
        for s in range(profile.scenarios_per_cycle):
            scenario_id = uuid.uuid4()
            user = rng.choice(USERS)
            is_starter = s == 0
            base_time = fi["initiated_at"] + timedelta(hours=rng.randint(1, 24))

            # Assign status based on lifecycle
            status_weights = [0.35, 0.25, 0.20, 0.10, 0.10]
            status = rng.choices(SCENARIO_STATUSES, weights=status_weights, k=1)[0]

            lifecycle_days = rng.randint(1, profile.scenario_lifecycle_days)
            created_at = base_time + timedelta(days=rng.randint(0, 3))
            updated_at = created_at + timedelta(days=lifecycle_days)

            scenario = {
                "id": scenario_id,
                "model_id": fi["model_id"],
                "forecast_init_id": fi["id"],
                "core_scenario_id": uuid.uuid4() if not is_starter and s < 4 else None,
                "scenario_display_name": f"{core_scenario_names[s % len(core_scenario_names)]} Scenario {s + 1}",
                "is_starter": is_starter,
                "status": status,
                "scenario_start_year": 2025,
                "scenario_end_year": rng.choice([2028, 2029, 2030]),
                "scenario_region_id": uuid.uuid4() if rng.random() > 0.3 else None,
                "scenario_region_name": rng.choice(["North America", "Europe", "Asia Pacific"]) if rng.random() > 0.3 else None,
                "scenario_country_id": uuid.uuid4() if rng.random() > 0.5 else None,
                "scenario_country_name": rng.choice(["US", "UK", "Germany", "Japan"]) if rng.random() > 0.5 else None,
                "currency": rng.choice(CURRENCIES),
                "currency_code": rng.choice(["USD", "GBP", "EUR", "JPY", None]),
                "created_at": created_at,
                "created_by": user,
                "created_req_id": uuid.uuid4(),
                "updated_at": updated_at,
                "updated_by": user,
                "updated_req_id": uuid.uuid4(),
                "submitted_at": updated_at if status in ("submitted", "locked") else None,
                "submitted_by": user if status in ("submitted", "locked") else None,
                "submitted_req_id": uuid.uuid4() if status in ("submitted", "locked") else None,
                "locked_at": updated_at + timedelta(hours=2) if status == "locked" else None,
                "locked_by": rng.choice(USERS) if status == "locked" else None,
                "locked_req_id": uuid.uuid4() if status == "locked" else None,
                "delete_at": updated_at if status == "deleted" else None,
                "delete_by": user if status == "deleted" else None,
                "delete_req_id": uuid.uuid4() if status == "deleted" else None,
                "withdraw_at": updated_at if status == "withdrawn" else None,
                "withdraw_by": user if status == "withdrawn" else None,
                "withdraw_req_id": uuid.uuid4() if status == "withdrawn" else None,
            }
            scenarios.append(scenario)

    return scenarios


def generate_scenario_node_data(
    scenario: dict,
    nodes: list[dict],
    profile: SeedProfile,
    rng,
) -> list[dict]:
    """Generate append-only fc_scenario_node_data records with realistic edit histories.

    For each node in the scenario:
    1. Create the initial data row (created_at = scenario.created_at)
    2. Simulate N edits (each one appends a new row, ends the previous)
    """
    all_node_data = []
    scenario_id = scenario["id"]
    base_time = scenario["created_at"]
    num_edits = rng.randint(profile.edits_per_scenario_min, profile.edits_per_scenario_max)

    # Select a subset of nodes to edit (not all nodes get edited every time)
    model_nodes = [n for n in nodes if n["model_id"] == scenario["model_id"]]
    if not model_nodes:
        return all_node_data

    for node in model_nodes:
        user = scenario["created_by"]
        current_time = base_time + timedelta(minutes=rng.randint(1, 60))

        # Initial data row
        input_data = _generate_input_data(rng)
        input_hash = _compute_hash(input_data)
        initial_id = uuid.uuid4()
        initial_row = {
            "id": initial_id,
            "model_node_id": node["id"],
            "scenario_id": scenario_id,
            "input_data": input_data,
            "comment": None,
            "source": "create_scenario",
            "input_hash": input_hash,
            "input_validated": False,
            "input_validation_message": None,
            "created_by": user,
            "created_at": current_time,
            "created_req_id": uuid.uuid4(),
            "end_by": None,
            "end_at": None,
            "end_req_id": None,
        }
        all_node_data.append(initial_row)

        # Random number of edits for this specific node
        node_edits = rng.randint(0, max(1, num_edits // len(model_nodes) * 2))
        prev_row = initial_row
        prev_data = input_data

        for edit_num in range(node_edits):
            edit_time = current_time + timedelta(
                minutes=rng.randint(30, 480) * (edit_num + 1)
            )
            edit_user = rng.choice(USERS)

            # Mutate data
            new_data = _mutate_input_data(prev_data, rng)
            new_hash = _compute_hash(new_data)

            # End the previous row
            end_req_id = uuid.uuid4()
            prev_row["end_by"] = edit_user
            prev_row["end_at"] = edit_time
            prev_row["end_req_id"] = end_req_id

            # Create new row
            new_id = uuid.uuid4()
            new_row = {
                "id": new_id,
                "model_node_id": node["id"],
                "scenario_id": scenario_id,
                "input_data": new_data,
                "comment": None,
                "source": "edit_scenario",
                "input_hash": new_hash,
                "input_validated": False,
                "input_validation_message": None,
                "created_by": edit_user,
                "created_at": edit_time,
                "created_req_id": uuid.uuid4(),
                "end_by": None,
                "end_at": None,
                "end_req_id": None,
            }
            all_node_data.append(new_row)
            prev_row = new_row
            prev_data = new_data

    return all_node_data
