from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from database import Base
import models  # Register tables without importing main or connecting to tracker.db.


def test_baseline_creates_current_schema(tmp_path):
    database_path = tmp_path / "migration.db"
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    url = f"sqlite:///{database_path.as_posix()}"
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    engine = create_engine(url)
    try:
        command.upgrade(config, "head")
        with engine.connect() as connection:
            assert [column["name"] for column in inspect(connection).get_columns("issues")] == [
                "id", "title", "description", "status", "priority",
                "created_at", "updated_at",
            ]
            context = MigrationContext.configure(
                connection, opts={"compare_server_default": True}
            )
            assert context.get_current_revision() == "0001"
            assert compare_metadata(context, Base.metadata) == []
        # Reapplying head must be a no-op, not another CREATE TABLE.
        command.upgrade(config, "head")
    finally:
        engine.dispose()
        database_path.unlink(missing_ok=True)
