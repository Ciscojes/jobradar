from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, create_engine, inspect

from tests.db import TEST_DATABASE_URL


def _database_url_for_migrations(tmp_path: Path) -> str:
    if TEST_DATABASE_URL == "sqlite:///:memory:":
        return f"sqlite:///{tmp_path / 'alembic-test.db'}"
    return TEST_DATABASE_URL


def _alembic_config(database_url: str) -> Config:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _drop_existing_schema(database_url: str) -> None:
    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(bind=engine)
    metadata.drop_all(bind=engine)
    engine.dispose()


def test_alembic_migrations_upgrade_downgrade_and_restore_head(tmp_path, monkeypatch):
    database_url = _database_url_for_migrations(tmp_path)
    monkeypatch.setenv("DATABASE_URL", database_url)
    _drop_existing_schema(database_url)

    config = _alembic_config(database_url)

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    assert {
        "users",
        "ofertas",
        "alertas",
        "user_ofertas",
        "notification_channels",
        "notification_logs",
        "scraper_runs",
        "alembic_version",
    }.issubset(tables)
    assert {"puesto_deseado", "bio"}.issubset(
        {column["name"] for column in inspector.get_columns("users")}
    )
    assert {"channel_id", "user_oferta_id", "channel_type"}.issubset(
        {column["name"] for column in inspector.get_columns("notification_logs")}
    )
    assert "new_matches" in {column["name"] for column in inspector.get_columns("scraper_runs")}
    engine.dispose()

    command.downgrade(config, "base")
    command.upgrade(config, "head")
