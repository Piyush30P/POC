"""Read-only synchronous engine for the OLTP source database.

Used by the ETL pipeline for batch extraction.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import settings

source_engine = create_engine(
    settings.source_db_url_sync,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    execution_options={"schema_translate_map": {None: settings.source_db_schema}},
)

SourceSessionLocal = sessionmaker(bind=source_engine, expire_on_commit=False)


def get_source_session() -> Session:
    session = SourceSessionLocal()
    try:
        yield session
    finally:
        session.close()
