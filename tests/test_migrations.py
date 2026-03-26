"""Test Alembic migration infrastructure and migration files."""

import importlib.util
import inspect
from pathlib import Path


class TestAlembicConfiguration:
    """Test Alembic configuration and migration file existence."""

    def test_alembic_config_loads(self):
        """Verify alembic.ini parses correctly."""
        alembic_ini_path = (
            Path(__file__).parent.parent / "alembic.ini"
        )

        assert alembic_ini_path.exists(), "alembic.ini not found"

        content = alembic_ini_path.read_text()

        # Verify critical configuration keys
        assert "[alembic]" in content
        assert "script_location = alembic" in content
        assert "sqlalchemy.url" in content

    def test_migration_files_exist(self):
        """Verify 3 migration files exist in alembic/versions/."""
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"

        assert versions_dir.exists(), "alembic/versions/ directory not found"

        # Find all Python files in versions directory
        migration_files = list(versions_dir.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__init__.py"]

        assert len(migration_files) >= 3, (
            f"Expected at least 3 migration files, found {len(migration_files)}"
        )

        # Check for specific migration file patterns
        migration_names = [f.name for f in migration_files]

        # Should have initial schema, indexes, and roles migrations
        has_initial = any("001" in name or "initial" in name for name in migration_names)
        has_indexes = any("002" in name or "index" in name for name in migration_names)
        has_roles = any("003" in name or "role" in name for name in migration_names)

        assert has_initial, "Initial schema migration not found"
        assert has_indexes, "Index migration not found"
        assert has_roles, "Role migration not found"


class TestInitialMigration:
    """Test initial schema migration (001_initial_schema.py)."""

    def _load_migration_module(self, pattern: str):
        """Load a migration module by filename pattern."""
        versions_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = list(versions_dir.glob(f"*{pattern}*.py"))

        assert len(migration_files) == 1, (
            f"Expected 1 migration file matching '{pattern}', "
            f"found {len(migration_files)}"
        )

        migration_path = migration_files[0]
        spec = importlib.util.spec_from_file_location(
            migration_path.stem, migration_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def test_initial_migration_has_all_tables(self):
        """Verify 001 migration creates all 13 tables."""
        module = self._load_migration_module("001")

        # Get upgrade function source
        upgrade_source = inspect.getsource(module.upgrade)

        # Expected tables (13 total)
        expected_tables = [
            "organizations",
            "users",
            "devices",
            "setup_codes",
            "folders",
            "assets",
            "collections",
            "collection_assets",
            "jobs",
            "job_files",
            "commands",
            "refresh_tokens",
            "audit_log",
        ]

        # Count op.create_table calls
        create_table_count = upgrade_source.count("op.create_table")

        assert create_table_count >= 13, (
            f"Expected at least 13 op.create_table calls, found {create_table_count}"
        )

        # Verify each table name appears in the migration
        for table_name in expected_tables:
            assert f'"{table_name}"' in upgrade_source or f"'{table_name}'" in upgrade_source, (
                f"Table '{table_name}' not found in initial migration"
            )

    def test_initial_migration_has_check_constraints(self):
        """Verify CHECK constraints for job, job_file, and command status."""
        module = self._load_migration_module("001")
        upgrade_source = inspect.getsource(module.upgrade)

        # Job status CHECK constraint (10 states)
        job_states = [
            "PRE_REGISTERING",
            "WAITING_FOR_AGENT",
            "IN_PROGRESS",
            "PAUSED_USER",
            "COMPLETED",
            "PARTIALLY_FAILED",
            "FAILED",
            "CANCELLED",
            "DENIED",
            "TIMEOUT",
        ]

        # At least some job states should appear in CHECK constraint
        job_states_found = sum(
            1 for state in job_states if state in upgrade_source
        )
        assert job_states_found >= 5, (
            f"Expected job status CHECK constraint, found {job_states_found}/10 states"
        )

        # JobFile status CHECK constraint (8 states)
        file_states = [
            "DISCOVERED",
            "PRE_REGISTERED",
            "UPLOADING",
            "PAUSED",
            "PAUSED_USER",
            "SYNCED",
            "FAILED",
            "CANCELLED",
        ]

        file_states_found = sum(
            1 for state in file_states if state in upgrade_source
        )
        assert file_states_found >= 4, (
            f"Expected file status CHECK constraint, found {file_states_found}/8 states"
        )

        # Command status CHECK constraint (3 states)
        command_states = ["PENDING", "DELIVERED", "EXPIRED"]

        command_states_found = sum(
            1 for state in command_states if state in upgrade_source
        )
        assert command_states_found >= 2, (
            f"Expected command status CHECK constraint, found {command_states_found}/3 states"
        )


class TestIndexMigration:
    """Test index creation migration (002_create_indexes.py)."""

    def test_index_migration_count(self):
        """Verify 002 has 11 op.create_index calls."""
        helper = TestInitialMigration()
        module = helper._load_migration_module("002")
        upgrade_source = inspect.getsource(module.upgrade)

        # Count op.create_index calls
        create_index_count = upgrade_source.count("op.create_index")

        assert create_index_count >= 11, (
            f"Expected at least 11 op.create_index calls, found {create_index_count}"
        )

        # Verify key indexes exist
        expected_indexes = [
            "idx_devices_agent_id",
            "idx_devices_org_id",
            "idx_devices_status",
            "idx_jobs_org_id",
            "idx_jobs_status",
            "idx_jobs_created_at",
            "idx_commands_agent_id",
            "idx_commands_status",
            "idx_audit_log_org_id",
            "idx_audit_log_event_type",
            "idx_audit_log_created_at",
        ]

        for index_name in expected_indexes:
            assert f'"{index_name}"' in upgrade_source or f"'{index_name}'" in upgrade_source, (
                f"Index '{index_name}' not found in index migration"
            )


class TestRoleMigration:
    """Test database role creation migration (003_create_roles.py)."""

    def test_role_migration_sql(self):
        """Verify 003 contains REVOKE UPDATE, DELETE ON audit_log."""
        helper = TestInitialMigration()
        module = helper._load_migration_module("003")
        upgrade_source = inspect.getsource(module.upgrade)

        # Verify REVOKE statement for BR-25 enforcement
        assert "REVOKE" in upgrade_source, "REVOKE statement not found"
        assert "UPDATE" in upgrade_source, "UPDATE permission not found in REVOKE"
        assert "DELETE" in upgrade_source, "DELETE permission not found in REVOKE"
        assert "audit_log" in upgrade_source, "audit_log table not found in REVOKE"

        # Verify role creation
        assert "CREATE ROLE" in upgrade_source or "create role" in upgrade_source.lower()
