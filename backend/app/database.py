"""
Database configuration and session management
Supports both async (asyncpg) and sync (psycopg2) connections
"""
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from app.config import settings

# Create async engine for FastAPI
async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create sync engine for Celery and Alembic
sync_engine = create_engine(
    settings.DATABASE_URL_SYNC,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create session makers
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

SyncSessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


# Async session dependency for FastAPI
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session
    Usage in FastAPI endpoints:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Sync session context manager for Celery
@asynccontextmanager
async def get_sync_session() -> Session:
    """
    Get sync database session for Celery tasks
    Usage in Celery:
        with get_sync_session() as db:
            db.query(Model).all()
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def init_db() -> None:
    """
    Initialize database
    Create all tables (in development)
    """
    async with async_engine.begin() as conn:
        # Import all models here to ensure they are registered with Base
        from app.models import user, workspace, monitor, incident, alert  # noqa

        if settings.ENVIRONMENT == "development":
            # In development, create tables automatically
            await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections"""
    await async_engine.dispose()
    sync_engine.dispose()


# Event listeners for connection management
@event.listens_for(sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Set connection parameters for PostgreSQL"""
    # This can be used to set specific PostgreSQL parameters
    pass
