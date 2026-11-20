"""Alembic migrations run against DATABASE_URL (same setting the app uses)."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.config import get_settings
from app.db import Base

if context.config.config_file_name:
    fileConfig(context.config.config_file_name)
target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(get_settings().sqlalchemy_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
