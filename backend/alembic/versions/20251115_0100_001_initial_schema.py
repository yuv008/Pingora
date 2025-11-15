"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2025-11-15 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255)),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('email_verification_token', sa.String(255)),
        sa.Column('email_verification_sent_at', sa.DateTime(timezone=True)),
        sa.Column('password_reset_token', sa.String(255)),
        sa.Column('password_reset_expires', sa.DateTime(timezone=True)),
        sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('mfa_secret', sa.String(255)),
        sa.Column('active_sessions', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
        sa.Column('last_login_ip', sa.String(45)),
        sa.Column('api_calls_today', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('api_calls_reset_at', sa.DateTime(timezone=True)),
        sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('locked_until', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('idx_user_email_active', 'users', ['email', 'is_active'])
    op.create_index('idx_user_username_active', 'users', ['username', 'is_active'])

    # Create user_sessions table
    op.create_table(
        'user_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('refresh_token', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(500)),
        sa.Column('device_fingerprint', sa.String(255)),
        sa.Column('access_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('refresh_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True)),
        sa.Column('requests_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('revoked_at', sa.DateTime(timezone=True)),
        sa.Column('revoked_reason', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_session_user_active', 'user_sessions', ['user_id', 'is_active'])
    op.create_index('idx_session_expires', 'user_sessions', ['refresh_expires_at'])

    # Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text()),
        sa.Column('plan_type', sa.Enum('free', 'starter', 'pro', 'business', 'enterprise', name='plantype'), nullable=False, server_default='free'),
        sa.Column('billing_email', sa.String(255)),
        sa.Column('stripe_customer_id', sa.String(255), unique=True),
        sa.Column('stripe_subscription_id', sa.String(255)),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True)),
        sa.Column('subscription_ends_at', sa.DateTime(timezone=True)),
        sa.Column('max_monitors', sa.Integer(), nullable=False, server_default=sa.text('10')),
        sa.Column('max_team_members', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('max_alert_channels', sa.Integer(), nullable=False, server_default=sa.text('2')),
        sa.Column('check_interval_minimum', sa.Integer(), nullable=False, server_default=sa.text('300')),
        sa.Column('data_retention_days', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('current_monitors_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('current_members_count', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('checks_this_month', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('checks_last_reset', sa.DateTime(timezone=True)),
        sa.Column('settings', postgresql.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column('features', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('suspension_reason', sa.String(500)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_workspace_stripe_customer', 'workspaces', ['stripe_customer_id'])
    op.create_index('idx_workspace_plan', 'workspaces', ['plan_type'])
    op.create_index('idx_workspace_active', 'workspaces', ['is_active'])

    # Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.Enum('owner', 'admin', 'member', 'viewer', name='workspacerole'), nullable=False, server_default='member'),
        sa.Column('invited_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('invitation_token', sa.String(255)),
        sa.Column('invitation_sent_at', sa.DateTime(timezone=True)),
        sa.Column('invitation_accepted', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('joined_at', sa.DateTime(timezone=True)),
        sa.Column('permissions', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_workspace_member_workspace', 'workspace_members', ['workspace_id'])
    op.create_index('idx_workspace_member_user', 'workspace_members', ['user_id'])
    op.create_index('idx_workspace_member_unique', 'workspace_members', ['workspace_id', 'user_id'], unique=True)

    # Create monitors table
    op.create_table(
        'monitors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('monitor_type', sa.Enum('http', 'https', 'tcp', 'udp', 'ping', 'dns', 'websocket', 'grpc', name='monitortype'), nullable=False, server_default='https'),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('method', sa.String(10), server_default='GET'),
        sa.Column('port', sa.Integer()),
        sa.Column('headers', postgresql.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column('body', sa.Text()),
        sa.Column('query_params', postgresql.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column('auth_type', sa.String(50)),
        sa.Column('auth_config', postgresql.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column('interval_seconds', sa.Integer(), nullable=False, server_default=sa.text('300')),
        sa.Column('timeout_seconds', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('2')),
        sa.Column('regions', postgresql.ARRAY(sa.String()), server_default=sa.text("'{us-east-1}'::varchar[]")),
        sa.Column('check_from_all_regions', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('assertions', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('expected_status_codes', postgresql.ARRAY(sa.Integer()), server_default=sa.text("'{200}'::integer[]")),
        sa.Column('expected_response_time_ms', sa.Integer()),
        sa.Column('expected_body_contains', sa.Text()),
        sa.Column('expected_body_regex', sa.Text()),
        sa.Column('expected_headers', postgresql.JSON()),
        sa.Column('ssl_check_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('ssl_expiry_warning_days', sa.Integer(), nullable=False, server_default=sa.text('30')),
        sa.Column('ssl_verify', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_paused', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('current_status', sa.Enum('up', 'down', 'degraded', 'paused', 'unknown', name='monitorstatus'), nullable=False, server_default='unknown'),
        sa.Column('uptime_percentage_24h', sa.Float()),
        sa.Column('uptime_percentage_7d', sa.Float()),
        sa.Column('uptime_percentage_30d', sa.Float()),
        sa.Column('avg_response_time_24h', sa.Float()),
        sa.Column('avg_response_time_7d', sa.Float()),
        sa.Column('avg_response_time_30d', sa.Float()),
        sa.Column('last_checked_at', sa.DateTime(timezone=True)),
        sa.Column('next_check_at', sa.DateTime(timezone=True)),
        sa.Column('last_check_status', sa.String(20)),
        sa.Column('last_check_error', sa.Text()),
        sa.Column('maintenance_windows', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('tags', postgresql.ARRAY(sa.String()), server_default=sa.text("'{}'::varchar[]")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_monitor_workspace_active', 'monitors', ['workspace_id', 'is_active'])
    op.create_index('idx_monitor_next_check', 'monitors', ['next_check_at', 'is_active'])
    op.create_index('idx_monitor_status', 'monitors', ['current_status'])
    op.execute("CREATE INDEX idx_monitor_tags ON monitors USING gin(tags)")

    # Create monitor_checks table (will be converted to hypertable)
    op.create_table(
        'monitor_checks',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('region', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('status_code', sa.Integer()),
        sa.Column('response_time_ms', sa.Integer()),
        sa.Column('response_size_bytes', sa.Integer()),
        sa.Column('dns_lookup_time_ms', sa.Integer()),
        sa.Column('tcp_connection_time_ms', sa.Integer()),
        sa.Column('tls_handshake_time_ms', sa.Integer()),
        sa.Column('first_byte_time_ms', sa.Integer()),
        sa.Column('content_transfer_time_ms', sa.Integer()),
        sa.Column('response_headers', postgresql.JSON()),
        sa.Column('response_body_sample', sa.Text()),
        sa.Column('response_body_hash', sa.String(64)),
        sa.Column('ssl_valid', sa.Boolean()),
        sa.Column('ssl_issuer', sa.String(255)),
        sa.Column('ssl_expiry_date', sa.Date()),
        sa.Column('ssl_days_remaining', sa.Integer()),
        sa.Column('error_type', sa.String(50)),
        sa.Column('error_message', sa.Text()),
        sa.Column('triggered_by', sa.String(50), server_default='scheduled'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_check_monitor_time', 'monitor_checks', ['monitor_id', 'checked_at'])
    op.create_index('idx_check_status_time', 'monitor_checks', ['status', 'checked_at'])
    op.create_index('idx_check_region_time', 'monitor_checks', ['region', 'checked_at'])

    # Create incidents table
    op.create_table(
        'incidents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True)),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True)),
        sa.Column('resolved_at', sa.DateTime(timezone=True)),
        sa.Column('status', sa.Enum('open', 'acknowledged', 'investigating', 'identified', 'monitoring', 'resolved', name='incidentstatus'), nullable=False, server_default='open'),
        sa.Column('severity', sa.Enum('critical', 'high', 'medium', 'low', 'info', name='incidentseverity'), nullable=False, server_default='critical'),
        sa.Column('title', sa.String(255)),
        sa.Column('trigger_type', sa.String(50)),
        sa.Column('error_message', sa.Text()),
        sa.Column('description', sa.Text()),
        sa.Column('total_checks_failed', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('affected_regions', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('initial_check_result', postgresql.JSON()),
        sa.Column('resolution_check_result', postgresql.JSON()),
        sa.Column('notifications_sent', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('notification_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('acknowledged_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('resolved_by_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('resolution_notes', sa.Text()),
        sa.Column('auto_resolved', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('downtime_seconds', sa.Integer()),
        sa.Column('mttr_seconds', sa.Integer()),
        sa.Column('show_on_status_page', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('public_message', sa.Text()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_incident_monitor', 'incidents', ['monitor_id'])
    op.create_index('idx_incident_status', 'incidents', ['status'])
    op.create_index('idx_incident_started', 'incidents', ['started_at'])

    # Create incident_updates table
    op.create_table(
        'incident_updates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL')),
        sa.Column('status', sa.Enum('open', 'acknowledged', 'investigating', 'identified', 'monitoring', 'resolved', name='incidentstatus')),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('update_type', sa.String(50), server_default='comment'),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_incident_update_incident', 'incident_updates', ['incident_id', 'created_at'])

    # Create alert_channels table
    op.create_table(
        'alert_channels',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('workspaces.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('channel_type', sa.Enum('email', 'webhook', 'slack', 'sms', 'pagerduty', 'discord', 'teams', 'telegram', name='alertchanneltype'), nullable=False),
        sa.Column('config', postgresql.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verification_token', sa.String(255)),
        sa.Column('verified_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('total_alerts_sent', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('total_alerts_failed', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('max_alerts_per_hour', sa.Integer(), server_default=sa.text('60')),
        sa.Column('alerts_sent_this_hour', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('rate_limit_reset_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_alert_channel_workspace', 'alert_channels', ['workspace_id'])
    op.create_index('idx_alert_channel_type', 'alert_channels', ['channel_type'])

    # Create alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_channels.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('description', sa.Text()),
        sa.Column('alert_on_status_change', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('alert_on_slow_response', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('slow_response_threshold_ms', sa.Integer()),
        sa.Column('alert_on_ssl_expiry', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('ssl_expiry_threshold_days', sa.Integer(), server_default=sa.text('30')),
        sa.Column('custom_conditions', postgresql.JSON(), server_default=sa.text("'[]'::json")),
        sa.Column('notify_on_recovery', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('min_failures_before_alert', sa.Integer(), nullable=False, server_default=sa.text('2')),
        sa.Column('cooldown_minutes', sa.Integer(), nullable=False, server_default=sa.text('15')),
        sa.Column('escalation_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('escalation_minutes', sa.Integer(), server_default=sa.text('30')),
        sa.Column('escalation_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_channels.id', ondelete='SET NULL')),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_alert_sent_at', sa.DateTime(timezone=True)),
        sa.Column('total_alerts_sent', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_alert_rule_monitor', 'alert_rules', ['monitor_id'])
    op.create_index('idx_alert_rule_channel', 'alert_rules', ['alert_channel_id'])

    # Create alert_logs table
    op.create_table(
        'alert_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('incident_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('incidents.id', ondelete='CASCADE')),
        sa.Column('monitor_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('monitors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_channel_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_channels.id', ondelete='SET NULL')),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20)),
        sa.Column('message', sa.Text()),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True)),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text()),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('response_status_code', sa.Integer()),
        sa.Column('response_body', sa.Text()),
        sa.Column('response_time_ms', sa.Integer()),
        sa.Column('metadata', postgresql.JSON(), server_default=sa.text("'{}'::json")),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('idx_alert_log_incident', 'alert_logs', ['incident_id'])
    op.create_index('idx_alert_log_monitor', 'alert_logs', ['monitor_id', 'sent_at'])
    op.create_index('idx_alert_log_channel', 'alert_logs', ['alert_channel_id', 'sent_at'])
    op.create_index('idx_alert_log_sent', 'alert_logs', ['sent_at'])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_table('alert_logs')
    op.drop_table('alert_rules')
    op.drop_table('alert_channels')
    op.drop_table('incident_updates')
    op.drop_table('incidents')
    op.drop_table('monitor_checks')
    op.drop_table('monitors')
    op.drop_table('workspace_members')
    op.drop_table('workspaces')
    op.drop_table('user_sessions')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS alertchanneltype')
    op.execute('DROP TYPE IF EXISTS incidentseverity')
    op.execute('DROP TYPE IF EXISTS incidentstatus')
    op.execute('DROP TYPE IF EXISTS monitorstatus')
    op.execute('DROP TYPE IF EXISTS monitortype')
    op.execute('DROP TYPE IF EXISTS workspacerole')
    op.execute('DROP TYPE IF EXISTS plantype')
