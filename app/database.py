"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# Create async engine with connection pooling
# Note: Connection is lazy - actual DB connection happens on first query
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,  # Base pool size (10)
    max_overflow=settings.db_max_overflow,  # Max additional connections (5)
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.debug,  # Log SQL queries in debug mode
)

# Create async session factory
async_session_factory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions.

    Yields:
        AsyncSession: Database session that is automatically closed after use.
    """
    async with async_session_factory() as session:
        yield session
