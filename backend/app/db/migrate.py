from pathlib import Path

from alembic import command
from alembic.config import Config

from app.core.config import Settings

_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def run_migrations(settings: Settings) -> None:
    """Brings the SQLite schema to head. Synchronous; call from a worker thread."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    cfg = Config(str(_INI))
    cfg.attributes["url"] = settings.sync_db_url
    command.upgrade(cfg, "head")
