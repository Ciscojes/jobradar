import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


TEST_DATABASE_URL = (
    os.getenv("TEST_DATABASE_URL")
    or os.getenv("DATABASE_URL")
    or "sqlite:///:memory:"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.database import Base  # noqa: E402


def _create_testing_engine():
    if TEST_DATABASE_URL.startswith("sqlite"):
        return create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(TEST_DATABASE_URL)


engine = _create_testing_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
