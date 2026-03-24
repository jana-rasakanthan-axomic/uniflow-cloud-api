"""Create indexes on frequently queried columns.

Revision ID: 002
Revises: 001
Create Date: 2026-03-24

This migration creates 11 indexes to optimize query performance for:
- Device lookups by agent_id, org_id, and status
- Job filtering by org_id, status, and creation time
- Command routing by agent_id and status polling
- Audit log querying by org_id, event_type, and time-based filtering

Indexes support the long-poll signaling pattern (commands by agent_id),
job dashboard queries (status + created_at), and audit log analytics.

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration - create all indexes."""
    # Device indexes (3 indexes)
    op.create_index('idx_devices_agent_id', 'devices', ['agent_id'])
    op.create_index('idx_devices_org_id', 'devices', ['org_id'])
    op.create_index('idx_devices_status', 'devices', ['status'])

    # Job indexes (3 indexes)
    op.create_index('idx_jobs_org_id', 'jobs', ['org_id'])
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_created_at', 'jobs', ['created_at'])

    # Command indexes (2 indexes)
    op.create_index('idx_commands_agent_id', 'commands', ['agent_id'])
    op.create_index('idx_commands_status', 'commands', ['status'])

    # Audit log indexes (3 indexes)
    op.create_index('idx_audit_log_org_id', 'audit_log', ['org_id'])
    op.create_index('idx_audit_log_event_type', 'audit_log', ['event_type'])
    op.create_index('idx_audit_log_created_at', 'audit_log', ['created_at'])


def downgrade() -> None:
    """Revert migration - drop all indexes."""
    # Drop audit log indexes
    op.drop_index('idx_audit_log_created_at', table_name='audit_log')
    op.drop_index('idx_audit_log_event_type', table_name='audit_log')
    op.drop_index('idx_audit_log_org_id', table_name='audit_log')

    # Drop command indexes
    op.drop_index('idx_commands_status', table_name='commands')
    op.drop_index('idx_commands_agent_id', table_name='commands')

    # Drop job indexes
    op.drop_index('idx_jobs_created_at', table_name='jobs')
    op.drop_index('idx_jobs_status', table_name='jobs')
    op.drop_index('idx_jobs_org_id', table_name='jobs')

    # Drop device indexes
    op.drop_index('idx_devices_status', table_name='devices')
    op.drop_index('idx_devices_org_id', table_name='devices')
    op.drop_index('idx_devices_agent_id', table_name='devices')
