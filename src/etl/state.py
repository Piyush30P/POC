"""ETL watermark tracking for incremental loads."""

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_watermark(session: Session, table_name: str) -> datetime | None:
    """Get the last_loaded_at timestamp for a source table."""
    result = session.execute(
        text("SELECT last_loaded_at FROM rpt.etl_watermark WHERE table_name = :tn"),
        {"tn": table_name},
    ).fetchone()
    return result[0] if result else None


def update_watermark(
    session: Session,
    table_name: str,
    last_loaded_at: datetime,
    row_count: int,
    status: str = "success",
) -> None:
    """Upsert the watermark for a source table."""
    now = datetime.now(timezone.utc)
    session.execute(
        text("""
            INSERT INTO rpt.etl_watermark
                (table_name, last_loaded_at, last_run_started, last_run_completed,
                 row_count_loaded, status)
            VALUES (:tn, :lla, :lrs, :lrc, :rcl, :st)
            ON CONFLICT (table_name) DO UPDATE SET
                last_loaded_at = :lla,
                last_run_completed = :lrc,
                row_count_loaded = rpt.etl_watermark.row_count_loaded + :rcl,
                status = :st
        """),
        {
            "tn": table_name,
            "lla": last_loaded_at,
            "lrs": now,
            "lrc": now,
            "rcl": row_count,
            "st": status,
        },
    )


def mark_run_started(session: Session, table_name: str) -> None:
    """Mark that an ETL run has started for a table."""
    now = datetime.now(timezone.utc)
    session.execute(
        text("""
            INSERT INTO rpt.etl_watermark
                (table_name, last_run_started, row_count_loaded, status)
            VALUES (:tn, :lrs, 0, 'in_progress')
            ON CONFLICT (table_name) DO UPDATE SET
                last_run_started = :lrs,
                status = 'in_progress'
        """),
        {"tn": table_name, "lrs": now},
    )
