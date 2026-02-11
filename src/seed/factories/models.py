"""Factory for generating fc_model, fc_model_node_tab, fc_model_node_groups,
fc_model_node, and fc_model_node_edge records."""

import uuid
from datetime import datetime, timezone

from faker import Faker

from src.seed.profiles import SeedProfile

fake = Faker()

THERAPEUTIC_AREAS = [
    ("Oncology", "Lung Cancer", "NSCLC"),
    ("Oncology", "Breast Cancer", "HER2+"),
    ("Vaccines", "HPV", "HPV Prevention"),
    ("Immunology", "Rheumatoid Arthritis", "RA"),
    ("Cardiovascular", "Heart Failure", "HFrEF"),
    ("Neuroscience", "Alzheimers", "AD"),
    ("Infectious Disease", "HIV", "HIV-1"),
    ("Respiratory", "Asthma", "Severe Asthma"),
    ("Endocrinology", "Diabetes", "T2D"),
    ("Hematology", "Multiple Myeloma", "MM"),
]

PUBLISH_LEVELS = ["global", "region", "country"]

REGIONS = [
    ("North America", "US"),
    ("Europe", "UK"),
    ("Europe", "Germany"),
    ("Asia Pacific", "Japan"),
    ("Latin America", "Brazil"),
]

NODE_TYPES = [
    "epiNode", "segmentNode", "treatmentGroupNode", "treatmentNode",
    "marketShareNode", "marketAccessNode", "pricingNode", "volumeNode",
    "revenueNode", "complianceNode",
]

FLOW_TYPES = ["patient_flow", "patients_adjustment_flow"]

TAB_NAMES_L2 = ["Patient Flow", "Events", "Patient Adjustment Flow"]
TAB_NAMES_L3 = ["Market Access", "Market Share", "Pricing", "Volume"]
TAB_NAMES_L4 = ["Inputs", "Assumptions", "Overrides", "Calculations"]


def generate_models(profile: SeedProfile, rng) -> dict:
    """Generate model hierarchy and return all records as dict of lists."""
    models = []
    tabs = []
    groups = []
    nodes = []
    edges = []

    for i in range(profile.num_models):
        ta_name, da_name, display_suffix = THERAPEUTIC_AREAS[i % len(THERAPEUTIC_AREAS)]
        region_name, country_name = REGIONS[i % len(REGIONS)]
        publish_level = PUBLISH_LEVELS[i % len(PUBLISH_LEVELS)]

        model_id = uuid.uuid4()
        model = {
            "id": model_id,
            "therapeutic_area_id": uuid.uuid4(),
            "therapeutic_area_name": ta_name,
            "model_display_name": f"{display_suffix} Forecast Model v{i + 1}",
            "model_disease_area_id": uuid.uuid4(),
            "model_disease_area_name": da_name,
            "model_publish_level": publish_level,
            "model_country_id": uuid.uuid4() if publish_level == "country" else None,
            "model_country_display_name": country_name if publish_level == "country" else None,
            "model_region_id": uuid.uuid4() if publish_level in ("region", "country") else None,
            "model_region_display_name": region_name if publish_level in ("region", "country") else None,
            "model_type": rng.choice(["incidence", "prevalence"]),
            "created_at": datetime.now(timezone.utc),
            "created_req_id": uuid.uuid4(),
        }
        models.append(model)

        # Generate tab hierarchy
        model_tabs = _generate_tabs(model_id, profile, rng)
        tabs.extend(model_tabs)

        # Generate groups and nodes per level-4 tab
        l4_tabs = [t for t in model_tabs if t["tab_level"] == 4]
        all_model_nodes = []
        for tab in l4_tabs:
            tab_groups, tab_nodes = _generate_groups_and_nodes(
                model_id, tab["id"], profile, rng
            )
            groups.extend(tab_groups)
            nodes.extend(tab_nodes)
            all_model_nodes.extend(tab_nodes)

        # Generate edges (simple sequential DAG within the model)
        model_edges = _generate_edges(all_model_nodes, rng)
        edges.extend(model_edges)

    return {
        "models": models,
        "tabs": tabs,
        "groups": groups,
        "nodes": nodes,
        "edges": edges,
    }


def _generate_tabs(model_id: uuid.UUID, profile: SeedProfile, rng) -> list[dict]:
    tabs = []

    # L2 tabs (top-level)
    l2_tabs = []
    for seq, name in enumerate(TAB_NAMES_L2, start=1):
        tab_id = uuid.uuid4()
        tabs.append({
            "id": tab_id,
            "parent_tab_id": None,
            "model_id": model_id,
            "tab_display_name": name,
            "tab_level": 2,
            "tab_seq": seq,
        })
        l2_tabs.append(tab_id)

    # L3 tabs under first L2
    l3_tabs = []
    for seq, name in enumerate(TAB_NAMES_L3, start=1):
        tab_id = uuid.uuid4()
        parent = l2_tabs[0]  # under Patient Flow
        tabs.append({
            "id": tab_id,
            "parent_tab_id": parent,
            "model_id": model_id,
            "tab_display_name": name,
            "tab_level": 3,
            "tab_seq": seq,
        })
        l3_tabs.append(tab_id)

    # L4 tabs under each L3
    for l3_id in l3_tabs:
        num_l4 = min(profile.tabs_per_model, len(TAB_NAMES_L4))
        for seq in range(1, num_l4 + 1):
            tab_id = uuid.uuid4()
            tabs.append({
                "id": tab_id,
                "parent_tab_id": l3_id,
                "model_id": model_id,
                "tab_display_name": f"{TAB_NAMES_L4[(seq - 1) % len(TAB_NAMES_L4)]}",
                "tab_level": 4,
                "tab_seq": seq,
            })

    return tabs


def _generate_groups_and_nodes(
    model_id: uuid.UUID,
    tab_id: uuid.UUID,
    profile: SeedProfile,
    rng,
) -> tuple[list[dict], list[dict]]:
    groups = []
    nodes = []

    for g_seq in range(1, profile.groups_per_tab + 1):
        group_id = uuid.uuid4()
        group_type = rng.choice(["epi", "treatment", "market", "pricing", "volume"])
        groups.append({
            "id": group_id,
            "model_node_tab_id": tab_id,
            "group_display_name": f"{group_type.title()} Group {g_seq}",
            "group_type": group_type,
            "group_seq": g_seq,
        })

        for n_seq in range(1, profile.nodes_per_group + 1):
            node_type = rng.choice(NODE_TYPES)
            node_id = uuid.uuid4()
            nodes.append({
                "id": node_id,
                "model_node_group_id": group_id,
                "model_id": model_id,
                "flow": rng.choice(FLOW_TYPES),
                "base_node_id": uuid.uuid4(),
                "node_display_name": f"{node_type.replace('Node', '')} {g_seq}.{n_seq}",
                "treatment_group_node_id": None,
                "model_config_id": uuid.uuid4(),
                "node_type": node_type,
                "treatment_id": uuid.uuid4() if "treatment" in node_type.lower() else None,
                "node_seq": n_seq,
                "disabled": False,
                "reportable": True,
                "epi_type": rng.choice(["Incidence", "Prevalence", None]),
                "multi_ip_op": rng.choice([True, False]),
                "node_order": (g_seq - 1) * profile.nodes_per_group + n_seq,
                "sku_id": None,
                "selected_output": rng.choice(["New", "Continuing", "Total", None]),
                "is_output": n_seq == profile.nodes_per_group,  # last node in group
                "curve_type": rng.choice(["OS", "PFS", "RFS", "Persistency", None]),
                "pfs_flag": rng.choice([True, False]),
                "ppc_flag": rng.choice([True, False]),
                "created_at": datetime.now(timezone.utc),
                "inherent_event": False,
                "hierarchy_json": {"level": g_seq, "position": n_seq},
            })

    return groups, nodes


def _generate_edges(nodes: list[dict], rng) -> list[dict]:
    """Create sequential edges between nodes to form a simple DAG."""
    edges = []
    if len(nodes) < 2:
        return edges

    for i in range(len(nodes) - 1):
        # Connect each node to the next one
        if rng.random() < 0.7:  # 70% chance of edge
            edges.append({
                "id": uuid.uuid4(),
                "source_node_id": nodes[i]["id"],
                "target_node_id": nodes[i + 1]["id"],
                "created_at": datetime.now(timezone.utc),
            })

    # Add some cross-group edges
    if len(nodes) > 10:
        for _ in range(min(5, len(nodes) // 5)):
            src_idx = rng.randint(0, len(nodes) // 2)
            tgt_idx = rng.randint(len(nodes) // 2, len(nodes) - 1)
            if src_idx != tgt_idx:
                edges.append({
                    "id": uuid.uuid4(),
                    "source_node_id": nodes[src_idx]["id"],
                    "target_node_id": nodes[tgt_idx]["id"],
                    "created_at": datetime.now(timezone.utc),
                })

    return edges
