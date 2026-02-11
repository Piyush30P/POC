"""Add RCA audit trail tables

Revision ID: rca_001
Revises: previous_revision
Create Date: 2026-02-11

Tables added:
- fact_cloudwatch_log
- fact_scenario_state_change
- fact_user_action
- fact_run_diagnostic
- view_scenario_audit_trail (materialized view)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'rca_001'
down_revision = None  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fact_cloudwatch_log
    op.create_table(
        'fact_cloudwatch_log',
        sa.Column('log_fact_key', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('log_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('log_stream', sa.String(500), nullable=False),
        sa.Column('log_group', sa.String(500), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_id', sa.String(255), nullable=True),
        sa.Column('environment', sa.String(20), nullable=False),
        sa.Column('service_name', sa.String(100), nullable=False),
        sa.Column('stack_trace', sa.Text(), nullable=True),
        sa.Column('error_category', sa.String(100), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('loaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('log_fact_key'),
        schema='rpt'
    )
    op.create_index('ix_rpt_fact_cloudwatch_log_timestamp', 'fact_cloudwatch_log', ['log_timestamp'], schema='rpt')
    op.create_index('ix_rpt_fact_cloudwatch_log_severity', 'fact_cloudwatch_log', ['severity'], schema='rpt')
    op.create_index('ix_rpt_fact_cloudwatch_log_correlation_id', 'fact_cloudwatch_log', ['correlation_id'], schema='rpt')
    op.create_index('ix_rpt_fact_cloudwatch_log_scenario_id', 'fact_cloudwatch_log', ['scenario_id'], schema='rpt')
    op.create_index('ix_rpt_fact_cloudwatch_log_run_id', 'fact_cloudwatch_log', ['run_id'], schema='rpt')
    op.create_index('ix_rpt_fact_cloudwatch_log_error_category', 'fact_cloudwatch_log', ['error_category'], schema='rpt')

    # fact_scenario_state_change
    op.create_table(
        'fact_scenario_state_change',
        sa.Column('state_change_key', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('scenario_key', sa.Integer(), nullable=False),
        sa.Column('scenario_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('previous_status', sa.String(50), nullable=True),
        sa.Column('new_status', sa.String(50), nullable=False),
        sa.Column('transition_type', sa.String(100), nullable=False),
        sa.Column('changed_by_user_key', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('change_reason', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('loaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['scenario_key'], ['rpt.dim_scenario.scenario_key']),
        sa.ForeignKeyConstraint(['changed_by_user_key'], ['rpt.dim_user.user_key']),
        sa.PrimaryKeyConstraint('state_change_key'),
        schema='rpt'
    )
    op.create_index('ix_rpt_fact_state_change_scenario_key', 'fact_scenario_state_change', ['scenario_key'], schema='rpt')
    op.create_index('ix_rpt_fact_state_change_scenario_id', 'fact_scenario_state_change', ['scenario_id'], schema='rpt')
    op.create_index('ix_rpt_fact_state_change_changed_at', 'fact_scenario_state_change', ['changed_at'], schema='rpt')
    op.create_index('ix_rpt_fact_state_change_correlation_id', 'fact_scenario_state_change', ['correlation_id'], schema='rpt')

    # fact_user_action
    op.create_table(
        'fact_user_action',
        sa.Column('action_key', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('user_key', sa.Integer(), nullable=False),
        sa.Column('scenario_key', sa.Integer(), nullable=True),
        sa.Column('action_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('action_category', sa.String(50), nullable=False),
        sa.Column('target_entity_type', sa.String(50), nullable=True),
        sa.Column('target_entity_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('request_endpoint', sa.String(500), nullable=True),
        sa.Column('http_method', sa.String(10), nullable=True),
        sa.Column('request_duration_ms', sa.Numeric(10, 2), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('action_details', postgresql.JSONB(), nullable=True),
        sa.Column('loaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_key'], ['rpt.dim_user.user_key']),
        sa.ForeignKeyConstraint(['scenario_key'], ['rpt.dim_scenario.scenario_key']),
        sa.PrimaryKeyConstraint('action_key'),
        schema='rpt'
    )
    op.create_index('ix_rpt_fact_user_action_user_key', 'fact_user_action', ['user_key'], schema='rpt')
    op.create_index('ix_rpt_fact_user_action_scenario_key', 'fact_user_action', ['scenario_key'], schema='rpt')
    op.create_index('ix_rpt_fact_user_action_timestamp', 'fact_user_action', ['action_timestamp'], schema='rpt')
    op.create_index('ix_rpt_fact_user_action_type', 'fact_user_action', ['action_type'], schema='rpt')
    op.create_index('ix_rpt_fact_user_action_correlation_id', 'fact_user_action', ['correlation_id'], schema='rpt')

    # fact_run_diagnostic
    op.create_table(
        'fact_run_diagnostic',
        sa.Column('diagnostic_key', sa.BigInteger(), nullable=False, autoincrement=True),
        sa.Column('run_fact_key', sa.BigInteger(), nullable=False),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('scenario_key', sa.Integer(), nullable=False),
        sa.Column('diagnostic_type', sa.String(50), nullable=False),
        sa.Column('node_key', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('diagnostic_category', sa.String(100), nullable=False),
        sa.Column('diagnostic_message', sa.Text(), nullable=False),
        sa.Column('diagnostic_details', postgresql.JSONB(), nullable=True),
        sa.Column('input_hash_at_run', sa.String(255), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cloudwatch_log_references', postgresql.ARRAY(sa.BigInteger()), nullable=True),
        sa.Column('loaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_fact_key'], ['rpt.fact_scenario_run.run_fact_key']),
        sa.ForeignKeyConstraint(['scenario_key'], ['rpt.dim_scenario.scenario_key']),
        sa.ForeignKeyConstraint(['node_key'], ['rpt.dim_node.node_key']),
        sa.PrimaryKeyConstraint('diagnostic_key'),
        schema='rpt'
    )
    op.create_index('ix_rpt_fact_diagnostic_run_fact_key', 'fact_run_diagnostic', ['run_fact_key'], schema='rpt')
    op.create_index('ix_rpt_fact_diagnostic_run_id', 'fact_run_diagnostic', ['run_id'], schema='rpt')
    op.create_index('ix_rpt_fact_diagnostic_type', 'fact_run_diagnostic', ['diagnostic_type'], schema='rpt')
    op.create_index('ix_rpt_fact_diagnostic_correlation_id', 'fact_run_diagnostic', ['correlation_id'], schema='rpt')

    # view_scenario_audit_trail (materialized view)
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS rpt.view_scenario_audit_trail AS
        SELECT
            row_number() OVER (ORDER BY event_timestamp) AS audit_key,
            scenario_key,
            scenario_id,
            event_timestamp,
            event_type,
            event_category,
            user_id,
            correlation_id,
            event_description,
            event_metadata
        FROM (
            -- State changes
            SELECT
                sc.scenario_key,
                sc.scenario_id,
                sc.changed_at AS event_timestamp,
                'state_change' AS event_type,
                'scenario_mgmt' AS event_category,
                u.user_id,
                sc.correlation_id,
                'Status changed from ' || COALESCE(sc.previous_status, 'none') || ' to ' || sc.new_status AS event_description,
                jsonb_build_object(
                    'transition_type', sc.transition_type,
                    'previous_status', sc.previous_status,
                    'new_status', sc.new_status
                ) AS event_metadata
            FROM rpt.fact_scenario_state_change sc
            JOIN rpt.dim_user u ON sc.changed_by_user_key = u.user_key

            UNION ALL

            -- User actions
            SELECT
                ua.scenario_key,
                ds.scenario_id,
                ua.action_timestamp AS event_timestamp,
                'user_action' AS event_type,
                ua.action_category,
                u.user_id,
                ua.correlation_id,
                'Action: ' || ua.action_type AS event_description,
                jsonb_build_object(
                    'action_type', ua.action_type,
                    'success', ua.success,
                    'target_entity_type', ua.target_entity_type
                ) AS event_metadata
            FROM rpt.fact_user_action ua
            JOIN rpt.dim_user u ON ua.user_key = u.user_key
            LEFT JOIN rpt.dim_scenario ds ON ua.scenario_key = ds.scenario_key
            WHERE ua.scenario_key IS NOT NULL

            UNION ALL

            -- Scenario runs
            SELECT
                sr.scenario_key,
                ds.scenario_id,
                sr.run_started_at AS event_timestamp,
                'run_started' AS event_type,
                'forecast_run' AS event_category,
                u.user_id,
                sr.run_id AS correlation_id,
                'Forecast run started' AS event_description,
                jsonb_build_object(
                    'run_id', sr.run_id,
                    'run_status', sr.run_status
                ) AS event_metadata
            FROM rpt.fact_scenario_run sr
            JOIN rpt.dim_scenario ds ON sr.scenario_key = ds.scenario_key
            JOIN rpt.dim_user u ON sr.run_by_user_key = u.user_key
        ) AS combined_events
        ORDER BY event_timestamp;

        CREATE INDEX IF NOT EXISTS ix_view_audit_trail_scenario_key
            ON rpt.view_scenario_audit_trail (scenario_key);
        CREATE INDEX IF NOT EXISTS ix_view_audit_trail_timestamp
            ON rpt.view_scenario_audit_trail (event_timestamp);
    """)


def downgrade() -> None:
    op.execute('DROP MATERIALIZED VIEW IF EXISTS rpt.view_scenario_audit_trail CASCADE')
    op.drop_table('fact_run_diagnostic', schema='rpt')
    op.drop_table('fact_user_action', schema='rpt')
    op.drop_table('fact_scenario_state_change', schema='rpt')
    op.drop_table('fact_cloudwatch_log', schema='rpt')
