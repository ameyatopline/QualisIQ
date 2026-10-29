"""Explicit schema lifecycle; never logs connection URLs or credentials."""
import os
from alembic import context
from sqlalchemy import create_engine,pool
from app.database import Base
from app import models
config=context.config
target_metadata=Base.metadata
url=os.getenv('DATABASE_URL','sqlite:///./don_qualityos_demo.db')
if context.is_offline_mode():
    context.configure(url=url,target_metadata=target_metadata,literal_binds=True,dialect_opts={'paramstyle':'named'})
    with context.begin_transaction():context.run_migrations()
else:
    engine=create_engine(url,poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
