"""Example ETL script for RCA dashboard data loading.

Run this script to populate the reporting database with audit trail data.

Usage:
    python scripts/run_rca_etl.py --full                 # Full load
    python scripts/run_rca_etl.py --incremental          # Last 24 hours
    python scripts/run_rca_etl.py --scenario-id <uuid>   # Specific scenario
    python scripts/run_rca_etl.py --cloudwatch-days 7    # Load CloudWatch logs
"""

import argparse
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.db.source_engine import get_source_sync_session
from src.db.reporting_engine import get_reporting_sync_session
from src.etl.extractors.audit_trail import (
    extract_scenario_state_changes,
    extract_user_actions,
    extract_input_change_sequence,
)
from src.etl.extractors.cloudwatch import CloudWatchExtractor, MockCloudWatchExtractor
from src.etl.transformers.user_journey import reconstruct_user_journey
from src.etl.loaders.rca_loaders import (
    load_cloudwatch_logs,
    load_state_changes,
    load_user_actions,
)
from src.etl.state import update_watermark
from src.config import settings


def load_audit_trail_data(
    full_load: bool = False,
    scenario_id: uuid.UUID | None = None,
    since_hours: int = 24,
):
    """Load scenario audit trail data from source to reporting DB."""
    print("🔄 Starting audit trail ETL...")

    # Determine time cutoff
    since = None if full_load else datetime.now(timezone.utc) - timedelta(hours=since_hours)

    # Get sessions
    source_session = get_source_sync_session()
    reporting_session = get_reporting_sync_session()

    try:
        # 1. Extract state changes
        print(f"📤 Extracting state changes (since: {since or 'beginning'})...")
        scenario_ids = [scenario_id] if scenario_id else None
        state_changes = list(extract_scenario_state_changes(
            session=source_session,
            since=since,
            scenario_ids=scenario_ids,
        ))
        print(f"   ✅ Extracted {len(state_changes)} state change records")

        # 2. Extract user actions
        print("📤 Extracting user actions...")
        user_actions = list(extract_user_actions(
            session=source_session,
            since=since,
            scenario_ids=scenario_ids,
        ))
        print(f"   ✅ Extracted {len(user_actions)} user action records")

        # 3. Extract input changes (per scenario)
        print("📤 Extracting input changes...")
        input_changes = []
        if scenario_id:
            changes = extract_input_change_sequence(
                session=source_session,
                scenario_id=scenario_id,
            )
            input_changes.extend(changes)
        else:
            # For full load, extract for all scenarios (limit to recent ones)
            from src.models.source import FcScenario
            from sqlalchemy import select

            query = select(FcScenario.id)
            if since:
                query = query.where(FcScenario.updated_at >= since)
            query = query.limit(100)  # Limit to avoid overload

            result = source_session.execute(query)
            scenario_ids_list = [row[0] for row in result]

            for sid in scenario_ids_list:
                changes = extract_input_change_sequence(
                    session=source_session,
                    scenario_id=sid,
                )
                input_changes.extend(changes)

        print(f"   ✅ Extracted {len(input_changes)} input change records")

        # 4. Load into reporting database
        print("📥 Loading state changes into reporting DB...")
        loaded_state = load_state_changes(
            reporting_session=reporting_session,
            state_changes=state_changes,
        )
        print(f"   ✅ Loaded {loaded_state} state change records")

        print("📥 Loading user actions into reporting DB...")
        loaded_actions = load_user_actions(
            reporting_session=reporting_session,
            user_actions=user_actions,
        )
        print(f"   ✅ Loaded {loaded_actions} user action records")

        # 5. Update watermark
        now = datetime.now(timezone.utc)
        update_watermark(
            session=reporting_session,
            table_name="rca_audit_trail",
            last_loaded_at=now,
            row_count=loaded_state + loaded_actions,
            status="success",
        )
        reporting_session.commit()

        print("✅ Audit trail ETL completed successfully!")

        return {
            "state_changes": loaded_state,
            "user_actions": loaded_actions,
            "input_changes": len(input_changes),
        }

    except Exception as e:
        reporting_session.rollback()
        print(f"❌ ETL failed: {e}")
        raise

    finally:
        source_session.close()
        reporting_session.close()


def load_cloudwatch_data(
    days: int = 7,
    environment: str = "dev",
    use_mock: bool = False,
):
    """Load CloudWatch logs into reporting database."""
    print(f"🔄 Starting CloudWatch ETL (last {days} days)...")

    if use_mock:
        print("⚠️  Using MOCK CloudWatch extractor (no AWS credentials needed)")
        extractor = MockCloudWatchExtractor()
    else:
        print("🔐 Using AWS CloudWatch extractor (requires credentials)")
        extractor = CloudWatchExtractor(
            log_group=f"/aws/lambda/forecast-service-{environment}",
            region="us-east-1",
        )

    # Calculate time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days)

    reporting_session = get_reporting_sync_session()

    try:
        # Extract logs
        print(f"📤 Extracting logs from {start_time} to {end_time}...")
        logs = list(extractor.extract_logs(
            start_time=start_time,
            end_time=end_time,
            severity_levels=["ERROR", "WARN", "INFO"],
        ))
        print(f"   ✅ Extracted {len(logs)} log records")

        # Load logs
        print("📥 Loading CloudWatch logs into reporting DB...")
        loaded = load_cloudwatch_logs(
            reporting_session=reporting_session,
            logs=logs,
            log_group=extractor.log_group,
            environment=environment,
        )
        print(f"   ✅ Loaded {loaded} log records")

        # Update watermark
        update_watermark(
            session=reporting_session,
            table_name="rca_cloudwatch_logs",
            last_loaded_at=end_time,
            row_count=loaded,
            status="success",
        )
        reporting_session.commit()

        print("✅ CloudWatch ETL completed successfully!")

        return {"logs_loaded": loaded}

    except Exception as e:
        reporting_session.rollback()
        print(f"❌ ETL failed: {e}")
        raise

    finally:
        reporting_session.close()


def main():
    parser = argparse.ArgumentParser(description="Run RCA Dashboard ETL")

    # ETL type
    parser.add_argument("--full", action="store_true", help="Full load (all data)")
    parser.add_argument("--incremental", action="store_true", help="Incremental load (last 24 hours)")
    parser.add_argument("--scenario-id", type=str, help="Load specific scenario UUID")

    # CloudWatch options
    parser.add_argument("--cloudwatch-days", type=int, help="Load CloudWatch logs for last N days")
    parser.add_argument("--environment", default="dev", choices=["dev", "sit", "uat", "prod"])
    parser.add_argument("--mock-cloudwatch", action="store_true", help="Use mock CloudWatch data")

    args = parser.parse_args()

    # Validate arguments
    if not any([args.full, args.incremental, args.scenario_id, args.cloudwatch_days]):
        parser.error("Must specify one of: --full, --incremental, --scenario-id, --cloudwatch-days")

    print("=" * 60)
    print("🚀 RCA Dashboard ETL Pipeline")
    print("=" * 60)
    print(f"Environment: {args.environment}")
    print(f"Timestamp: {datetime.now()}")
    print("=" * 60)

    results = {}

    # Run audit trail ETL
    if args.full or args.incremental or args.scenario_id:
        scenario_uuid = uuid.UUID(args.scenario_id) if args.scenario_id else None
        results["audit_trail"] = load_audit_trail_data(
            full_load=args.full,
            scenario_id=scenario_uuid,
            since_hours=24 if args.incremental else 0,
        )

    # Run CloudWatch ETL
    if args.cloudwatch_days:
        results["cloudwatch"] = load_cloudwatch_data(
            days=args.cloudwatch_days,
            environment=args.environment,
            use_mock=args.mock_cloudwatch,
        )

    print("\n" + "=" * 60)
    print("📊 ETL Summary:")
    print("=" * 60)
    for etl_type, metrics in results.items():
        print(f"\n{etl_type.upper()}:")
        for key, value in metrics.items():
            print(f"  {key}: {value}")

    print("\n✅ All ETL processes completed!")


if __name__ == "__main__":
    main()
