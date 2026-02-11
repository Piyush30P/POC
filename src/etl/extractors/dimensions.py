"""Extract dimension data from source OLTP tables."""

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def extract_models(source_session: Session) -> pd.DataFrame:
    result = source_session.execute(text("""
        SELECT id, model_display_name, therapeutic_area_name,
               model_disease_area_name, model_publish_level, model_type,
               model_country_display_name, model_region_display_name,
               created_at
        FROM fc_model
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_forecast_cycles(source_session: Session) -> pd.DataFrame:
    result = source_session.execute(text("""
        SELECT fi.id, fi.model_id, fi.forecast_cycle_display_name,
               fi.forecast_cycle_start_dt, fi.forecast_cycle_end_dt,
               fi.horizon_start_limit, fi.horizon_end_limit,
               fi.initiated_at, fi.initiated_by
        FROM fc_forecast_init fi
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_scenarios(source_session: Session) -> pd.DataFrame:
    result = source_session.execute(text("""
        SELECT s.id, s.model_id, s.forecast_init_id,
               s.scenario_display_name, s.is_starter, s.status,
               s.scenario_start_year, s.scenario_end_year,
               s.scenario_region_name, s.scenario_country_name,
               s.currency, s.created_by, s.created_at
        FROM fc_scenario s
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_nodes(source_session: Session) -> pd.DataFrame:
    """Extract nodes with their full tab path."""
    result = source_session.execute(text("""
        SELECT
            n.id AS node_id,
            n.model_id,
            n.node_display_name,
            n.node_type,
            n.flow,
            n.node_seq,
            n.is_output,
            n.disabled,
            g.group_display_name,
            t4.tab_display_name AS tab_l4_name,
            t3.tab_display_name AS tab_l3_name,
            t2.tab_display_name AS tab_l2_name
        FROM fc_model_node n
        JOIN fc_model_node_groups g ON n.model_node_group_id = g.id
        JOIN fc_model_node_tab t4 ON g.model_node_tab_id = t4.id
        LEFT JOIN fc_model_node_tab t3 ON t4.parent_tab_id = t3.id
        LEFT JOIN fc_model_node_tab t2 ON t3.parent_tab_id = t2.id
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_users(source_session: Session) -> pd.DataFrame:
    """Extract unique usernames from all *_by columns."""
    result = source_session.execute(text("""
        SELECT DISTINCT username FROM (
            SELECT created_by AS username FROM fc_scenario
            UNION SELECT updated_by FROM fc_scenario
            UNION SELECT submitted_by FROM fc_scenario WHERE submitted_by IS NOT NULL
            UNION SELECT locked_by FROM fc_scenario WHERE locked_by IS NOT NULL
            UNION SELECT created_by FROM fc_scenario_node_data
            UNION SELECT end_by FROM fc_scenario_node_data WHERE end_by IS NOT NULL
            UNION SELECT run_by FROM fc_scenario_run
            UNION SELECT initiated_by FROM fc_forecast_init
        ) u
        WHERE username IS NOT NULL
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_event_types(source_session: Session) -> pd.DataFrame:
    result = source_session.execute(text("""
        SELECT id, display_name, inherent
        FROM fc_event_type
    """))
    return pd.DataFrame(result.fetchall(), columns=result.keys())
