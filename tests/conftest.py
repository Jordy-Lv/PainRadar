"""Fixtures compartidas. Ningún test toca la red ni el .env real."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from painradar.config import Profiles, Settings, load_profiles
from painradar.models import Base

FIXTURES = Path(__file__).parent / "fixtures"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_fixture(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
    return data


@pytest.fixture
def settings() -> Settings:
    """Settings con credenciales de mentira; _env_file=None ignora el .env local."""
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        freelancer_oauth_token="token-de-prueba",
        github_token="ghp_prueba",
        stackexchange_key="key-prueba",
        reddit_client_id="rid",
        reddit_client_secret="rsecret",
        database_url="sqlite://",
    )


@pytest.fixture
def profiles() -> Profiles:
    return load_profiles(PROJECT_ROOT / "config" / "perfiles.yaml")


@pytest.fixture
def session() -> Iterator[Session]:
    """Base en memoria, creada y destruida por test."""
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()
