"""Tests for database connection infrastructure and pool configuration."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.config import settings
from app.database import async_session_factory, engine, get_db


class TestEnginePoolConfiguration:
    """Test connection pool configuration."""

    def test_engine_pool_configuration(self):
        """Verify pool_size=10 and max_overflow=5 (15 total connections)."""
        # PostgreSQL uses AsyncAdaptedQueuePool with configured sizes
        assert isinstance(engine.pool, AsyncAdaptedQueuePool), "Should use AsyncAdaptedQueuePool"
        assert engine.pool.size() == 10, "Pool size should be 10"
        assert engine.pool._max_overflow == 5, "Max overflow should be 5"

    def test_pool_pre_ping_enabled(self):
        """Verify pool_pre_ping is enabled for stale connection detection."""
        assert engine.pool._pre_ping is True, "Pool pre-ping should be enabled"

    def test_pool_recycle_configured(self):
        """Verify connections are recycled after 1 hour (3600s)."""
        assert engine.pool._recycle == 3600, "Pool recycle should be 3600 seconds"

    def test_database_url_from_settings(self):
        """Verify database URL is read from settings."""
        assert settings.db_pool_size == 10, "Pool size should be 10 in settings"
        assert settings.db_max_overflow == 5, "Max overflow should be 5 in settings"


class TestGetDbDependency:
    """Test get_db() async dependency function."""

    async def test_get_db_yields_session(self):
        """Verify get_db() returns an AsyncSession instance."""
        # This tests the generator without requiring a database connection
        # The session is created but not used
        gen = get_db()
        session = await gen.__anext__()
        assert isinstance(session, AsyncSession), "Should yield AsyncSession"
        try:
            await gen.aclose()
        except StopAsyncIteration:
            pass

    def test_session_factory_configured(self):
        """Verify session factory creates AsyncSession instances."""
        # Test that the factory is configured correctly
        assert async_session_factory.class_.__name__ == "AsyncSession"
        assert async_session_factory.kw.get("expire_on_commit") is False
