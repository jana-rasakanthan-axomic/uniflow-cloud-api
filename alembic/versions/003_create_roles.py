"""Create database roles with audit_log INSERT-only enforcement (BR-25).

Revision ID: 003
Revises: 002
Create Date: 2026-03-24

This migration creates two PostgreSQL roles:

1. uniflow_audit_reader - Read-only access to audit_log for compliance auditing
   - GRANT SELECT ON audit_log
   - No INSERT, UPDATE, or DELETE permissions

2. uniflow_app - Application service role with restricted audit_log access
   - GRANT SELECT, INSERT, UPDATE, DELETE ON all tables
   - REVOKE UPDATE, DELETE ON audit_log (BR-25: INSERT-only for immutability)

BR-25 Enforcement: The application role can only INSERT audit_log entries,
ensuring the audit trail cannot be tampered with at the database level.

Production Deployment: Replace 'CHANGE_ME' passwords with secrets from
AWS Secrets Manager or equivalent key management system.

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply migration - create roles with permissions."""
    # Create audit reader role (read-only access to audit_log)
    op.execute(
        "CREATE ROLE uniflow_audit_reader WITH LOGIN PASSWORD 'CHANGE_ME';"
    )
    op.execute(
        "GRANT SELECT ON audit_log TO uniflow_audit_reader;"
    )

    # Create application role (full access except audit_log mutations)
    op.execute(
        "CREATE ROLE uniflow_app WITH LOGIN PASSWORD 'CHANGE_ME';"
    )

    # Grant full CRUD on all tables
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO uniflow_app;"
    )

    # BR-25: Revoke UPDATE and DELETE on audit_log to enforce INSERT-only
    # This ensures audit trail immutability at the database level
    op.execute(
        "REVOKE UPDATE, DELETE ON audit_log FROM uniflow_app;"
    )

    # Grant usage on sequences (for BIGSERIAL audit_log.id)
    op.execute(
        "GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO uniflow_app;"
    )


def downgrade() -> None:
    """Revert migration - drop roles."""
    # Drop roles (will fail if they own objects, which is expected)
    op.execute("DROP ROLE IF EXISTS uniflow_app;")
    op.execute("DROP ROLE IF EXISTS uniflow_audit_reader;")
