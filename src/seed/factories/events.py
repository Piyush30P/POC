"""Factory for generating fc_event_type and fc_scenario_event_type records."""

import uuid
from datetime import datetime, timezone

from src.seed.profiles import SeedProfile

EVENT_TYPES = [
    {"name": "Fair Share", "inherent": False},
    {"name": "Explicit", "inherent": False},
    {"name": "Derived", "inherent": False},
    {"name": "LoE", "inherent": True},
]


def generate_event_types(profile: SeedProfile) -> list[dict]:
    """Generate fc_event_type records."""
    now = datetime.now(timezone.utc)
    event_types = []
    for et in EVENT_TYPES[: profile.event_types_count]:
        event_types.append({
            "id": uuid.uuid4(),
            "display_name": et["name"],
            "inherent": et["inherent"],
            "created_at": now,
            "created_by": "system",
            "updated_at": now,
            "udpated_by": "system",
        })
    return event_types


def generate_scenario_event_types(
    scenario_id: uuid.UUID,
    event_types: list[dict],
    rng,
    min_events: int = 0,
    max_events: int = 3,
) -> list[dict]:
    """Generate fc_scenario_event_type records linking a scenario to event types."""
    count = rng.randint(min_events, min(max_events, len(event_types)))
    selected = rng.sample(event_types, count) if count > 0 else []
    return [
        {
            "id": uuid.uuid4(),
            "event_type_id": et["id"],
            "scenario_id": scenario_id,
        }
        for et in selected
    ]
