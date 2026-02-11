"""Extract fact data from source OLTP tables with incremental support."""

from datetime import datetime

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session


def extract_scenario_runs(
    source_session: Session,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Extract scenario runs with branch and calc aggregates."""
    where_clause = ""
    params = {}
    if since:
        where_clause = "WHERE sr.run_at > :since"
        params["since"] = since

    result = source_session.execute(
        text(f"""
            SELECT
                sr.id AS run_id,
                sr.scenario_id,
                sr.run_status,
                sr.run_at,
                sr.run_by,
                sr.run_complete_at,
                sr.fail_reason,
                s.model_id,
                s.forecast_init_id,
                (SELECT COUNT(*) FROM fc_scenario_run_branch
                 WHERE scenario_run_id = sr.id) AS branch_count,
                (SELECT COUNT(*) FROM fc_scenario_node_calc nc
                 JOIN fc_scenario_run_branch rb ON nc.scenario_run_branch_id = rb.id
                 WHERE rb.scenario_run_id = sr.id) AS node_calc_total,
                (SELECT COUNT(*) FROM fc_scenario_node_calc nc
                 JOIN fc_scenario_run_branch rb ON nc.scenario_run_branch_id = rb.id
                 WHERE rb.scenario_run_id = sr.id AND nc.status = 'success') AS node_calc_success,
                (SELECT COUNT(*) FROM fc_scenario_node_calc nc
                 JOIN fc_scenario_run_branch rb ON nc.scenario_run_branch_id = rb.id
                 WHERE rb.scenario_run_id = sr.id AND nc.status = 'failed') AS node_calc_failed,
                (SELECT COUNT(*) FROM fc_scenario_node_calc nc
                 JOIN fc_scenario_run_branch rb ON nc.scenario_run_branch_id = rb.id
                 WHERE rb.scenario_run_id = sr.id AND nc.status = 'timeout') AS node_calc_timeout
            FROM fc_scenario_run sr
            JOIN fc_scenario s ON sr.scenario_id = s.id
            {where_clause}
            ORDER BY sr.run_at
        """),
        params,
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_node_calcs(
    source_session: Session,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Extract individual node calculation results."""
    where_clause = ""
    params = {}
    if since:
        where_clause = "WHERE nc.created_at > :since"
        params["since"] = since

    result = source_session.execute(
        text(f"""
            SELECT
                nc.id AS calc_id,
                rb.scenario_run_id AS run_id,
                rb.id AS branch_id,
                rb.event_tag,
                nc.model_node_id,
                nc.scenario_node_data_id,
                nc.status AS calc_status,
                nc.processing_start_at,
                nc.processing_end_at,
                nc.fail_reason,
                nc.output_data,
                nc.created_at,
                sr.scenario_id
            FROM fc_scenario_node_calc nc
            JOIN fc_scenario_run_branch rb ON nc.scenario_run_branch_id = rb.id
            JOIN fc_scenario_run sr ON rb.scenario_run_id = sr.id
            {where_clause}
            ORDER BY nc.created_at
        """),
        params,
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_scenario_node_data(
    source_session: Session,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Extract append-only scenario node data for timeline reconstruction."""
    where_clause = ""
    params = {}
    if since:
        where_clause = "WHERE snd.created_at > :since"
        params["since"] = since

    result = source_session.execute(
        text(f"""
            SELECT
                snd.id,
                snd.scenario_id,
                snd.model_node_id,
                snd.input_data,
                snd.input_hash,
                snd.input_validated,
                snd.created_by,
                snd.created_at,
                snd.end_by,
                snd.end_at
            FROM fc_scenario_node_data snd
            {where_clause}
            ORDER BY snd.scenario_id, snd.model_node_id, snd.created_at
        """),
        params,
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())


def extract_in_progress_run_ids(rpt_session: Session) -> list[str]:
    """Get run IDs that are still marked as in_progress in reporting."""
    result = rpt_session.execute(
        text("SELECT run_id FROM rpt.fact_scenario_run WHERE run_status = 'in progress'")
    )
    return [str(row[0]) for row in result.fetchall()]


def extract_scenario_event_data(
    source_session: Session,
    since: datetime | None = None,
) -> pd.DataFrame:
    """Extract append-only event data for event timeline."""
    where_clause = ""
    params = {}
    if since:
        where_clause = "WHERE sed.created_at > :since"
        params["since"] = since

    result = source_session.execute(
        text(f"""
            SELECT
                sed.id,
                sed.scenario_event_type_id,
                sed.event_data,
                sed.event_data_hash,
                sed.created_by,
                sed.created_at,
                sed.end_by,
                sed.end_at,
                setype.scenario_id,
                setype.event_type_id
            FROM fc_scenario_event_data sed
            JOIN fc_scenario_event_type setype ON sed.scenario_event_type_id = setype.id
            {where_clause}
            ORDER BY sed.created_at
        """),
        params,
    )
    return pd.DataFrame(result.fetchall(), columns=result.keys())
