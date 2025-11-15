"""Setup TimescaleDB hypertables and aggregates

Revision ID: 002
Revises: 001
Create Date: 2025-11-15 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE")

    # Convert monitor_checks to hypertable
    op.execute("""
        SELECT create_hypertable(
            'monitor_checks',
            'checked_at',
            if_not_exists => TRUE,
            chunk_time_interval => INTERVAL '1 day'
        )
    """)

    # Enable compression on monitor_checks
    op.execute("""
        ALTER TABLE monitor_checks SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'monitor_id',
            timescaledb.compress_orderby = 'checked_at DESC'
        )
    """)

    # Add compression policy (compress data older than 7 days)
    op.execute("""
        SELECT add_compression_policy(
            'monitor_checks',
            INTERVAL '7 days',
            if_not_exists => TRUE
        )
    """)

    # Create continuous aggregate for hourly stats
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS monitor_stats_hourly
        WITH (timescaledb.continuous) AS
        SELECT
            monitor_id,
            time_bucket('1 hour', checked_at) AS bucket,
            region,
            COUNT(*) AS total_checks,
            COUNT(*) FILTER (WHERE status = 'up') AS successful_checks,
            AVG(response_time_ms) AS avg_response_time,
            MIN(response_time_ms) AS min_response_time,
            MAX(response_time_ms) AS max_response_time,
            PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY response_time_ms) AS median_response_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_response_time,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_response_time,
            AVG(response_size_bytes) AS avg_response_size,
            100.0 * COUNT(*) FILTER (WHERE status = 'up') / NULLIF(COUNT(*), 0) AS uptime_percentage
        FROM monitor_checks
        GROUP BY monitor_id, bucket, region
    """)

    # Add refresh policy for hourly stats
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'monitor_stats_hourly',
            start_offset => INTERVAL '3 hours',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour',
            if_not_exists => TRUE
        )
    """)

    # Create continuous aggregate for daily stats
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS monitor_stats_daily
        WITH (timescaledb.continuous) AS
        SELECT
            monitor_id,
            time_bucket('1 day', checked_at) AS day,
            COUNT(*) AS total_checks,
            COUNT(*) FILTER (WHERE status = 'up') AS successful_checks,
            AVG(response_time_ms) AS avg_response_time,
            MIN(response_time_ms) AS min_response_time,
            MAX(response_time_ms) AS max_response_time,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY response_time_ms) AS p95_response_time,
            PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY response_time_ms) AS p99_response_time,
            100.0 * COUNT(*) FILTER (WHERE status = 'up') / NULLIF(COUNT(*), 0) AS uptime_percentage
        FROM monitor_checks
        GROUP BY monitor_id, day
    """)

    # Add refresh policy for daily stats
    op.execute("""
        SELECT add_continuous_aggregate_policy(
            'monitor_stats_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 day',
            schedule_interval => INTERVAL '1 day',
            if_not_exists => TRUE
        )
    """)

    # Add data retention policy (keep raw data for 90 days)
    op.execute("""
        SELECT add_retention_policy(
            'monitor_checks',
            INTERVAL '90 days',
            if_not_exists => TRUE
        )
    """)

    # Create indexes on continuous aggregates
    op.execute("CREATE INDEX IF NOT EXISTS idx_monitor_stats_hourly_monitor ON monitor_stats_hourly(monitor_id, bucket DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_monitor_stats_daily_monitor ON monitor_stats_daily(monitor_id, day DESC)")


def downgrade() -> None:
    # Remove retention policy
    op.execute("SELECT remove_retention_policy('monitor_checks', if_exists => TRUE)")

    # Remove continuous aggregate policies
    op.execute("SELECT remove_continuous_aggregate_policy('monitor_stats_hourly', if_exists => TRUE)")
    op.execute("SELECT remove_continuous_aggregate_policy('monitor_stats_daily', if_exists => TRUE)")

    # Drop continuous aggregates
    op.execute("DROP MATERIALIZED VIEW IF EXISTS monitor_stats_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS monitor_stats_hourly CASCADE")

    # Remove compression policy
    op.execute("SELECT remove_compression_policy('monitor_checks', if_exists => TRUE)")

    # This will fail if TimescaleDB is in use, but that's expected
    # op.execute("DROP EXTENSION IF EXISTS timescaledb CASCADE")
