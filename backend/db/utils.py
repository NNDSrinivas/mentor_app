from __future__ import annotations

from sqlalchemy import inspect

from .base import Base, get_engine


def ensure_schema() -> None:
    engine = get_engine()
    inspector = inspect(engine)
    if not inspector.has_table("meeting"):
        Base.metadata.create_all(engine)


__all__ = ["ensure_schema"]
