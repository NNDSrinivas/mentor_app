from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session


Base = declarative_base()


def _default_database_url() -> str:
    return os.getenv("KNOWLEDGE_DATABASE_URL", os.getenv("DATABASE_URL", "sqlite:///./knowledge.db"))


def get_engine(url: str | None = None) -> Engine:
    database_url = url or _default_database_url()
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, future=True, connect_args=connect_args)


_engine = None
_SessionLocal = None


def get_sessionmaker(url: str | None = None) -> sessionmaker:
    global _engine, _SessionLocal
    if _engine is None or url is not None:
        _engine = get_engine(url)
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, class_=Session, future=True)
    return _SessionLocal


def get_session() -> Session:
    factory = get_sessionmaker()
    return factory()


@contextmanager
def session_scope(url: str | None = None) -> Iterator[Session]:
    factory = get_sessionmaker(url)
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
