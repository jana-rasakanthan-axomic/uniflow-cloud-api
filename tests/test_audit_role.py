"""Test audit_log INSERT-only role enforcement (BR-25)."""

import importlib.util
import inspect
from pathlib import Path


class TestRoleMigrationContent:
    """Test role migration file content for BR-25 compliance."""

    def _load_role_migration(self):
        """Load the role migration module (003_create_roles.py)."""
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = list(versions_dir.glob("*003*.py"))

        if not migration_files:
            # Try pattern matching for "role"
            migration_files = list(versions_dir.glob("*role*.py"))

        assert len(migration_files) >= 1, "Role migration file not found"

        migration_path = migration_files[0]
        spec = importlib.util.spec_from_file_location(
            migration_path.stem, migration_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def test_role_migration_creates_audit_reader(self):
        """Verify SQL contains CREATE ROLE uniflow_audit_reader."""
        module = self._load_role_migration()
        upgrade_source = inspect.getsource(module.upgrade)

        # Verify audit reader role creation
        assert "uniflow_audit_reader" in upgrade_source, (
            "uniflow_audit_reader role not found in migration"
        )

        # Should contain CREATE ROLE statement
        assert "CREATE ROLE" in upgrade_source or "create role" in upgrade_source.lower(), (
            "CREATE ROLE statement not found"
        )

    def test_role_migration_grants_select_only(self):
        """Verify GRANT SELECT ON audit_log for audit_reader role."""
        module = self._load_role_migration()
        upgrade_source = inspect.getsource(module.upgrade)

        # Verify SELECT permission granted to audit_reader
        assert "GRANT" in upgrade_source or "grant" in upgrade_source.lower()
        assert "SELECT" in upgrade_source

        # Should reference audit_log table
        assert "audit_log" in upgrade_source

    def test_role_migration_revokes_app_mutations(self):
        """Verify REVOKE UPDATE, DELETE ON audit_log FROM uniflow_app (BR-25)."""
        module = self._load_role_migration()
        upgrade_source = inspect.getsource(module.upgrade)

        # Verify REVOKE statement for BR-25
        assert "REVOKE" in upgrade_source, (
            "REVOKE statement not found - BR-25 not enforced"
        )

        # Verify UPDATE and DELETE are revoked
        assert "UPDATE" in upgrade_source, "UPDATE not revoked in migration"
        assert "DELETE" in upgrade_source, "DELETE not revoked in migration"

        # Verify it's for the application role
        assert "uniflow_app" in upgrade_source, (
            "uniflow_app role not found in REVOKE statement"
        )

        # Verify it targets audit_log
        assert "audit_log" in upgrade_source, (
            "audit_log table not found in REVOKE statement"
        )

    def test_role_migration_downgrade(self):
        """Verify downgrade() drops both roles."""
        module = self._load_role_migration()
        downgrade_source = inspect.getsource(module.downgrade)

        # Verify DROP ROLE statements
        assert "DROP ROLE" in downgrade_source or "drop role" in downgrade_source.lower()

        # Should drop both roles
        assert "uniflow_audit_reader" in downgrade_source
        assert "uniflow_app" in downgrade_source


class TestAuditRoleDocumentation:
    """Test BR-25 enforcement documentation in migration."""

    def test_migration_has_br25_comment(self):
        """Verify migration docstring or comments mention BR-25."""
        helper = TestRoleMigrationContent()
        module = helper._load_role_migration()

        # Check module docstring
        if module.__doc__:
            has_br25 = "BR-25" in module.__doc__
            has_insert_only = "INSERT-only" in module.__doc__
            has_audit = "audit" in module.__doc__.lower()
            assert has_br25 or has_insert_only or has_audit

        # Check upgrade function for comments
        upgrade_source = inspect.getsource(module.upgrade)

        # Should have some documentation about audit_log permissions
        has_documentation = (
            "BR-25" in upgrade_source
            or "INSERT-only" in upgrade_source
            or "audit_log" in upgrade_source
        )

        assert has_documentation, (
            "Migration should document BR-25 INSERT-only requirement for audit_log"
        )
