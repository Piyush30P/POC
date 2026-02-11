"""Async engine for the reporting database.

Used by FastAPI to serve dashboard API requests.
Also provides a sync engine for ETL writes and Alembic migrations.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings

# Async engine for FastAPI
reporting_async_engine = create_async_engine(
    settings.reporting_db_url_async,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

ReportingAsyncSessionLocal = async_sessionmaker(
    bind=reporting_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for ETL writes and Alembic
reporting_sync_engine = create_engine(
    settings.reporting_db_url_sync,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    execution_options={"schema_translate_map": {None: settings.reporting_db_schema}},
)

ReportingSyncSessionLocal = sessionmaker(
    bind=reporting_sync_engine,
    expire_on_commit=False,
)


async def get_reporting_async_session() -> AsyncSession:
    async with ReportingAsyncSessionLocal() as session:
        yield session


def get_reporting_sync_session() -> Session:
    session = ReportingSyncSessionLocal()
    try:
        yield session
    finally:
        session.close()
