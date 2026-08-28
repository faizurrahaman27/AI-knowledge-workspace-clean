from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from src.core.settings import settings
from src.core.logging import logger

DATABASE_URL = settings.DATABASE_URL

logger.info("Using database: %s", DATABASE_URL.split("://")[0] + "://***")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    # Needed only for SQLite, since it's single-threaded by default.
    connect_args = {"check_same_thread": False}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
