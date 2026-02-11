"""CloudWatch logs extractor for RCA and scenario audit.

Fetches logs from AWS CloudWatch filtered by:
- Correlation IDs
- Scenario IDs
- Run IDs
- Time ranges
- Severity levels
"""

import re
import uuid
from datetime import datetime, timezone, timedelta
from typing import Iterator

try:
    import boto3
    from botocore.exceptions import ClientError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


class CloudWatchExtractor:
    """Extract and normalize CloudWatch logs for reporting database."""

    def __init__(
        self,
        log_group: str,
        region: str = "us-east-1",
        profile: str | None = None,
    ):
        """Initialize CloudWatch client.

        Args:
            log_group: CloudWatch log group name (e.g., /aws/lambda/forecast-service)
            region: AWS region
            profile: AWS profile name (optional, uses default if None)
        """
        if not BOTO3_AVAILABLE:
            raise ImportError(
                "boto3 is required for CloudWatch extraction. "
                "Install it with: pip install boto3"
            )

        session = boto3.Session(profile_name=profile, region_name=region)
        self.client = session.client("logs")
        self.log_group = log_group

    def extract_logs(
        self,
        start_time: datetime,
        end_time: datetime | None = None,
        correlation_ids: list[str] | None = None,
        scenario_ids: list[str] | None = None,
        run_ids: list[str] | None = None,
        severity_levels: list[str] | None = None,
        limit: int = 10000,
    ) -> Iterator[dict]:
        """Extract logs from CloudWatch with filtering.

        Args:
            start_time: Start of time range (inclusive)
            end_time: End of time range (exclusive, defaults to now)
            correlation_ids: Filter by correlation/request IDs
            scenario_ids: Filter by scenario UUIDs
            run_ids: Filter by run UUIDs
            severity_levels: Filter by log level (INFO, WARN, ERROR)
            limit: Maximum number of log events to return

        Yields:
            Normalized log records as dictionaries
        """
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Build CloudWatch Insights query
        query = self._build_query(
            correlation_ids=correlation_ids,
            scenario_ids=scenario_ids,
            run_ids=run_ids,
            severity_levels=severity_levels,
        )

        # Convert to epoch milliseconds
        start_ms = int(start_time.timestamp() * 1000)
        end_ms = int(end_time.timestamp() * 1000)

        try:
            # Start query
            response = self.client.start_query(
                logGroupName=self.log_group,
                startTime=start_ms,
                endTime=end_ms,
                queryString=query,
                limit=limit,
            )
            query_id = response["queryId"]

            # Poll for results
            while True:
                result = self.client.get_query_results(queryId=query_id)
                status = result["status"]

                if status == "Complete":
                    break
                elif status == "Failed":
                    raise RuntimeError(f"CloudWatch query failed: {result}")
                elif status in ("Running", "Scheduled"):
                    import time
                    time.sleep(0.5)
                else:
                    raise RuntimeError(f"Unknown query status: {status}")

            # Parse and yield results
            for record in result.get("results", []):
                normalized = self._normalize_log_record(record)
                if normalized:
                    yield normalized

        except ClientError as e:
            raise RuntimeError(f"CloudWatch API error: {e}") from e

    def _build_query(
        self,
        correlation_ids: list[str] | None,
        scenario_ids: list[str] | None,
        run_ids: list[str] | None,
        severity_levels: list[str] | None,
    ) -> str:
        """Build CloudWatch Insights query string."""
        filters = []

        # Base query
        query_parts = ["fields @timestamp, @message, @logStream, level, correlationId, scenarioId, runId, userId, stackTrace"]

        if correlation_ids:
            ids_filter = " or ".join(f'correlationId = "{cid}"' for cid in correlation_ids)
            filters.append(f"({ids_filter})")

        if scenario_ids:
            ids_filter = " or ".join(f'scenarioId = "{sid}"' for sid in scenario_ids)
            filters.append(f"({ids_filter})")

        if run_ids:
            ids_filter = " or ".join(f'runId = "{rid}"' for rid in run_ids)
            filters.append(f"({ids_filter})")

        if severity_levels:
            levels_filter = " or ".join(f'level = "{lvl}"' for lvl in severity_levels)
            filters.append(f"({levels_filter})")

        if filters:
            query_parts.append("filter " + " and ".join(filters))

        query_parts.append("sort @timestamp asc")

        return " | ".join(query_parts)

    def _normalize_log_record(self, record: list[dict]) -> dict | None:
        """Convert CloudWatch Insights result row to normalized dict.

        CloudWatch returns results as list of field dictionaries:
        [{"field": "@timestamp", "value": "..."}, {"field": "level", "value": "ERROR"}, ...]
        """
        field_map = {item["field"]: item.get("value") for item in record}

        # Required fields
        timestamp_str = field_map.get("@timestamp")
        message = field_map.get("@message")
        if not timestamp_str or not message:
            return None

        # Parse timestamp
        try:
            log_timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None

        # Extract structured data
        return {
            "log_timestamp": log_timestamp,
            "log_stream": field_map.get("@logStream", "unknown"),
            "message": message,
            "severity": field_map.get("level", "INFO").upper(),
            "correlation_id": self._parse_uuid(field_map.get("correlationId")),
            "scenario_id": self._parse_uuid(field_map.get("scenarioId")),
            "run_id": self._parse_uuid(field_map.get("runId")),
            "user_id": field_map.get("userId"),
            "stack_trace": field_map.get("stackTrace"),
            "error_category": self._categorize_error(message),
            "metadata": {
                k: v for k, v in field_map.items()
                if k not in ("@timestamp", "@message", "@logStream", "level", "correlationId", "scenarioId", "runId", "userId", "stackTrace")
            },
        }

    @staticmethod
    def _parse_uuid(value: str | None) -> uuid.UUID | None:
        """Safely parse UUID string."""
        if not value:
            return None
        try:
            return uuid.UUID(value)
        except (ValueError, AttributeError):
            return None

    @staticmethod
    def _categorize_error(message: str) -> str | None:
        """Categorize error messages for aggregation."""
        message_lower = message.lower()

        error_patterns = {
            "timeout": r"timeout|timed out|deadline exceeded",
            "validation": r"validation|invalid|missing required|constraint",
            "database": r"database|sql|connection|deadlock|transaction",
            "calculation": r"calculation|compute|division by zero|nan|infinity",
            "permission": r"permission|unauthorized|forbidden|access denied",
            "not_found": r"not found|does not exist|missing",
            "network": r"network|connection refused|unreachable",
            "config": r"configuration|config|missing env|invalid setting",
        }

        for category, pattern in error_patterns.items():
            if re.search(pattern, message_lower):
                return category

        return "uncategorized"


class MockCloudWatchExtractor(CloudWatchExtractor):
    """Mock extractor for testing without AWS credentials."""

    def __init__(self, log_group: str = "mock-log-group", **kwargs):
        """Initialize mock extractor (skips boto3)."""
        self.log_group = log_group
        self.client = None

    def extract_logs(
        self,
        start_time: datetime,
        end_time: datetime | None = None,
        **kwargs,
    ) -> Iterator[dict]:
        """Generate mock log records."""
        if end_time is None:
            end_time = datetime.now(timezone.utc)

        # Generate sample logs
        sample_logs = [
            {
                "log_timestamp": start_time,
                "log_stream": "forecast-service/2026-02-11/instance-1",
                "message": "Scenario run started",
                "severity": "INFO",
                "correlation_id": uuid.uuid4(),
                "scenario_id": uuid.uuid4(),
                "run_id": uuid.uuid4(),
                "user_id": "john.doe",
                "stack_trace": None,
                "error_category": None,
                "metadata": {},
            },
            {
                "log_timestamp": start_time + timedelta(seconds=30),
                "log_stream": "forecast-service/2026-02-11/instance-1",
                "message": "Node calculation failed: Division by zero in treatment node",
                "severity": "ERROR",
                "correlation_id": uuid.uuid4(),
                "scenario_id": uuid.uuid4(),
                "run_id": uuid.uuid4(),
                "user_id": "jane.smith",
                "stack_trace": "Traceback (most recent call last):\n  File ...",
                "error_category": "calculation",
                "metadata": {},
            },
        ]

        for log in sample_logs:
            if start_time <= log["log_timestamp"] <= end_time:
                yield log
