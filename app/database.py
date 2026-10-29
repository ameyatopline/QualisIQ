"""Local SQLite by default; PostgreSQL via DATABASE_URL for deployment."""
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./don_qualityos_demo.db')
IS_SQLITE = DATABASE_URL.startswith('sqlite')
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread': False} if IS_SQLITE else {}, pool_pre_ping=True)
if IS_SQLITE:
    @event.listens_for(engine, 'connect')
    def enable_foreign_keys(connection, _):
        cursor = connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.close()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db

def create_schema():
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
