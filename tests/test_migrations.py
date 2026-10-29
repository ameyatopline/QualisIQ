from pathlib import Path
from alembic.config import Config
from alembic import command
from sqlalchemy import create_engine,inspect
from app.database import Base

def test_baseline_upgrade_downgrade_and_schema_parity(tmp_path,monkeypatch):
    path=tmp_path/'migration.db';monkeypatch.setenv('DATABASE_URL',f'sqlite:///{path}')
    cfg=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
    command.upgrade(cfg,'head');engine=create_engine(f'sqlite:///{path}')
    assert set(Base.metadata.tables).issubset(inspect(engine).get_table_names())
    command.check(cfg)
    command.downgrade(cfg,'base')
    assert set(inspect(engine).get_table_names())=={'alembic_version'}
    command.upgrade(cfg,'head');engine.dispose()
