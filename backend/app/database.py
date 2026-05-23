import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


DEFAULT_DATABASE_URL = (
    "mysql+pymysql://root:123456@127.0.0.1:3306/SeafarerDB?charset=utf8mb4"
)


def get_database_url() -> str:
    return os.getenv("SEAFARER_DATABASE_URL", DEFAULT_DATABASE_URL)


def create_engine_from_url(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(database_url, pool_pre_ping=True)


def create_session_factory(database_url: str | None = None):
    engine = create_engine_from_url(database_url or get_database_url())
    return engine, sessionmaker(bind=engine, autoflush=False, autocommit=False)
