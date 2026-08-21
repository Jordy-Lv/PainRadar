"""Conexión a la base de datos.

SQLAlchemy síncrono a propósito: el fetching es async (ahí está la latencia,
en la red), pero escribir en un SQLite local tarda microsegundos y no gana
nada con async — solo complejidad.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from painradar.config import get_settings
from painradar.models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def _ensure_sqlite_dir(url: str) -> None:
    """SQLite no crea el directorio del archivo; hay que hacerlo a mano."""
    prefix = "sqlite:///"
    if url.startswith(prefix):
        path = Path(url[len(prefix) :])
        if path.parent and not path.parent.exists():
            path.parent.mkdir(parents=True, exist_ok=True)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_settings().database_url
        _ensure_sqlite_dir(url)
        _engine = create_engine(url, echo=False, future=True)
        if url.startswith("sqlite"):

            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragmas(dbapi_conn, _record):  # type: ignore[no-untyped-def]
                cursor = dbapi_conn.cursor()
                # WAL: permite leer mientras el scheduler escribe.
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Sesión transaccional: commit al salir, rollback si algo revienta."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all() -> None:
    """Atajo para tests y para el primer arranque. En producción manda Alembic."""
    Base.metadata.create_all(get_engine())
