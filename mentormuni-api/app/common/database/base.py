"""
SQLAlchemy Declarative Base.

Every Phase 1 model inherits from `Base`.
Alembic imports `Base.metadata` to autogenerate migrations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared base for all ORM models."""

    pass
