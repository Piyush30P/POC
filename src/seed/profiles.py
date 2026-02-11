"""Data generation profiles defining volume and behavioral shapes."""

from dataclasses import dataclass, field


@dataclass
class SeedProfile:
    name: str
    num_models: int = 3
    tabs_per_model: int = 4
    groups_per_tab: int = 3
    nodes_per_group: int = 5
    forecast_cycles_per_model: int = 2
    scenarios_per_cycle: int = 8
    edits_per_scenario_min: int = 5
    edits_per_scenario_max: int = 15
    runs_per_scenario_min: int = 3
    runs_per_scenario_max: int = 10
    run_success_rate: float = 0.80
    run_timeout_rate: float = 0.05
    node_calc_failure_rate: float = 0.05
    scenario_lifecycle_days: int = 14
    event_types_count: int = 4
    events_per_scenario_min: int = 0
    events_per_scenario_max: int = 3


PROFILES: dict[str, SeedProfile] = {
    "standard": SeedProfile(
        name="standard",
    ),
    "heavy_editor": SeedProfile(
        name="heavy_editor",
        edits_per_scenario_min=50,
        edits_per_scenario_max=100,
        runs_per_scenario_min=5,
        runs_per_scenario_max=15,
    ),
    "flaky_runs": SeedProfile(
        name="flaky_runs",
        run_success_rate=0.40,
        run_timeout_rate=0.15,
        node_calc_failure_rate=0.20,
    ),
    "clean": SeedProfile(
        name="clean",
        run_success_rate=1.0,
        run_timeout_rate=0.0,
        node_calc_failure_rate=0.0,
        edits_per_scenario_min=2,
        edits_per_scenario_max=5,
    ),
    "scale_test": SeedProfile(
        name="scale_test",
        num_models=10,
        scenarios_per_cycle=25,
        runs_per_scenario_min=5,
        runs_per_scenario_max=20,
    ),
}


def get_profile(name: str) -> SeedProfile:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile '{name}'. Available: {list(PROFILES.keys())}")
    return PROFILES[name]
