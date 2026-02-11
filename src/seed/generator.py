"""CLI entry-point for generating mock seed data into source OLTP tables.

Usage:
    python -m src.seed.generator --profile=standard --seed=42
    python -m src.seed.generator --profile=flaky_runs --seed=42 --reset
"""

import argparse
import random
import sys
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from src.config import settings
from src.db.source_engine import source_engine, SourceSessionLocal
from src.models.source import SourceBase
from src.seed.profiles import get_profile, SeedProfile
from src.seed.factories.models import generate_models
from src.seed.factories.scenarios import (
    generate_forecast_inits,
    generate_scenarios,
    generate_scenario_node_data,
)
from src.seed.factories.runs import generate_runs_for_scenario
from src.seed.factories.events import generate_event_types, generate_scenario_event_types


def _bulk_insert(session: Session, table_name: str, rows: list[dict]) -> int:
    """Insert rows into a source table using raw SQL for performance."""
    if not rows:
        return 0

    columns = list(rows[0].keys())
    col_str = ", ".join(columns)
    val_placeholders = ", ".join([f":{c}" for c in columns])
    sql = text(f"INSERT INTO {table_name} ({col_str}) VALUES ({val_placeholders})")

    # Convert UUIDs and datetimes for pg
    clean_rows = []
    for row in rows:
        clean = {}
        for k, v in row.items():
            if isinstance(v, uuid.UUID):
                clean[k] = str(v)
            elif isinstance(v, dict) or isinstance(v, list):
                import json
                clean[k] = json.dumps(v, default=str)
            else:
                clean[k] = v
        clean_rows.append(clean)

    session.execute(sql, clean_rows)
    return len(clean_rows)


def _reset_tables(session: Session) -> None:
    """Truncate all source tables in correct order."""
    tables_in_order = [
        "fc_scenario_event_calc",
        "fc_scenario_node_calc",
        "fc_scenario_run_branch",
        "fc_scenario_run",
        "fc_scenario_event_data",
        "fc_scenario_event_type",
        "fc_scenario_node_data",
        "fc_model_node_edge",
        "fc_model_node_treatment",
        "fc_model_node",
        "fc_model_node_groups",
        "fc_model_node_tab",
        "fc_scenario",
        "fc_forecast_init",
        "fc_event_type",
        "fc_model",
    ]
    for table in tables_in_order:
        try:
            session.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
        except Exception:
            pass  # Table might not exist yet
    session.commit()
    print("  All source tables truncated.")


def _create_source_tables(engine) -> None:
    """Create source tables if they don't exist."""
    SourceBase.metadata.create_all(engine)
    print("  Source tables created/verified.")


def run_seed(profile_name: str, seed: int, reset: bool = False) -> None:
    """Main seed generation function."""
    print(f"\n{'='*60}")
    print(f"ClearSight Dashboard — Seed Data Generator")
    print(f"Profile: {profile_name} | Seed: {seed} | Reset: {reset}")
    print(f"{'='*60}\n")

    profile = get_profile(profile_name)
    rng = random.Random(seed)
    start_time = time.time()

    # Ensure source tables exist
    print("[1/7] Creating source tables...")
    _create_source_tables(source_engine)

    session = SourceSessionLocal()
    try:
        if reset:
            print("[1.5/7] Resetting existing data...")
            _reset_tables(session)

        # Step 2: Generate models
        print("[2/7] Generating models, tabs, groups, nodes, edges...")
        model_data = generate_models(profile, rng)
        count = _bulk_insert(session, "fc_model", model_data["models"])
        print(f"  fc_model: {count} rows")
        count = _bulk_insert(session, "fc_model_node_tab", model_data["tabs"])
        print(f"  fc_model_node_tab: {count} rows")
        count = _bulk_insert(session, "fc_model_node_groups", model_data["groups"])
        print(f"  fc_model_node_groups: {count} rows")
        count = _bulk_insert(session, "fc_model_node", model_data["nodes"])
        print(f"  fc_model_node: {count} rows")
        count = _bulk_insert(session, "fc_model_node_edge", model_data["edges"])
        print(f"  fc_model_node_edge: {count} rows")
        session.commit()

        # Step 3: Generate event types
        print("[3/7] Generating event types...")
        event_types = generate_event_types(profile)
        count = _bulk_insert(session, "fc_event_type", event_types)
        print(f"  fc_event_type: {count} rows")
        session.commit()

        # Step 4: Generate forecast inits
        print("[4/7] Generating forecast initiations...")
        forecast_inits = generate_forecast_inits(model_data["models"], profile, rng)
        count = _bulk_insert(session, "fc_forecast_init", forecast_inits)
        print(f"  fc_forecast_init: {count} rows")
        session.commit()

        # Step 5: Generate scenarios
        print("[5/7] Generating scenarios...")
        scenarios = generate_scenarios(forecast_inits, profile, rng)
        count = _bulk_insert(session, "fc_scenario", scenarios)
        print(f"  fc_scenario: {count} rows")
        session.commit()

        # Step 5.5: Generate scenario event types
        all_scenario_event_types = []
        for scenario in scenarios:
            set_records = generate_scenario_event_types(
                scenario["id"], event_types, rng,
                profile.events_per_scenario_min,
                profile.events_per_scenario_max,
            )
            all_scenario_event_types.extend(set_records)
        if all_scenario_event_types:
            count = _bulk_insert(session, "fc_scenario_event_type", all_scenario_event_types)
            print(f"  fc_scenario_event_type: {count} rows")
        session.commit()

        # Step 6: Generate node data (append-only edit histories)
        print("[6/7] Generating scenario node data (edit histories)...")
        all_node_data = []
        node_data_by_scenario: dict[uuid.UUID, list[dict]] = {}
        for idx, scenario in enumerate(scenarios):
            nd = generate_scenario_node_data(scenario, model_data["nodes"], profile, rng)
            all_node_data.extend(nd)
            node_data_by_scenario[scenario["id"]] = nd
            if (idx + 1) % 10 == 0:
                print(f"  ... processed {idx + 1}/{len(scenarios)} scenarios")

        # Insert in batches
        batch_size = 5000
        total_nd = 0
        for i in range(0, len(all_node_data), batch_size):
            batch = all_node_data[i : i + batch_size]
            total_nd += _bulk_insert(session, "fc_scenario_node_data", batch)
            session.commit()
        print(f"  fc_scenario_node_data: {total_nd} rows")

        # Step 7: Generate runs
        print("[7/7] Generating runs, branches, and node calculations...")
        all_runs = []
        all_branches = []
        all_node_calcs = []

        for idx, scenario in enumerate(scenarios):
            run_data = generate_runs_for_scenario(
                scenario, node_data_by_scenario, profile, rng
            )
            all_runs.extend(run_data["runs"])
            all_branches.extend(run_data["branches"])
            all_node_calcs.extend(run_data["node_calcs"])
            if (idx + 1) % 10 == 0:
                print(f"  ... processed {idx + 1}/{len(scenarios)} scenarios")

        count = _bulk_insert(session, "fc_scenario_run", all_runs)
        print(f"  fc_scenario_run: {count} rows")
        session.commit()

        count = _bulk_insert(session, "fc_scenario_run_branch", all_branches)
        print(f"  fc_scenario_run_branch: {count} rows")
        session.commit()

        # Insert node calcs in batches
        total_nc = 0
        for i in range(0, len(all_node_calcs), batch_size):
            batch = all_node_calcs[i : i + batch_size]
            total_nc += _bulk_insert(session, "fc_scenario_node_calc", batch)
            session.commit()
        print(f"  fc_scenario_node_calc: {total_nc} rows")

        elapsed = time.time() - start_time
        print(f"\n{'='*60}")
        print(f"Seed generation complete in {elapsed:.1f}s")
        print(f"Summary:")
        print(f"  Models:     {len(model_data['models'])}")
        print(f"  Nodes:      {len(model_data['nodes'])}")
        print(f"  Scenarios:  {len(scenarios)}")
        print(f"  Node Data:  {total_nd}")
        print(f"  Runs:       {len(all_runs)}")
        print(f"  Node Calcs: {total_nc}")
        print(f"{'='*60}\n")

    except Exception as e:
        session.rollback()
        print(f"\nERROR: Seed generation failed: {e}")
        raise
    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(description="ClearSight Dashboard Seed Data Generator")
    parser.add_argument(
        "--profile",
        type=str,
        default="standard",
        help="Seed profile (standard, heavy_editor, flaky_runs, clean, scale_test)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible data",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate all source tables before generating",
    )
    args = parser.parse_args()
    run_seed(args.profile, args.seed, args.reset)


if __name__ == "__main__":
    main()
