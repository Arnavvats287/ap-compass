import os
from pathlib import Path
from sqlalchemy import create_engine, event
from .models import Base

ROOT = Path(__file__).resolve().parents[3]

def create_db_engine(path=None):
    db_path = Path(path or os.environ.get("AP_COMPASS_DB_PATH", ROOT / "runtime/ap-compass.db"))
    if not db_path.is_absolute():
        db_path = ROOT / db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine("sqlite:///" + db_path.as_posix(), connect_args={"check_same_thread": False})
    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    return engine

def initialize(engine):
    # Phase 1 initial schema only. Subsequent schema evolution requires migrations.
    Base.metadata.create_all(engine)
