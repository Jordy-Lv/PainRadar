"""Registro de fuentes.

Añadir una fuente nueva = escribir el adapter + una línea aquí.
"""

from __future__ import annotations

from painradar.models.enums import Track
from painradar.sources.base import (
    HttpSourceAdapter,
    SourceAdapter,
    SourceError,
    SourceNotConfigured,
)
from painradar.sources.freelancer import FreelancerAdapter
from painradar.sources.github import GithubAdapter
from painradar.sources.reddit import RedditAdapter
from painradar.sources.stackexchange import StackExchangeAdapter

ADAPTERS: dict[str, type[HttpSourceAdapter]] = {
    FreelancerAdapter.name: FreelancerAdapter,
    GithubAdapter.name: GithubAdapter,
    StackExchangeAdapter.name: StackExchangeAdapter,
    RedditAdapter.name: RedditAdapter,
}

# Intervalos por defecto (segundos). En ventas la latencia es la ventaja
# competitiva; en contribuciones un hilo sigue vivo horas, así que sondear
# más despacio ahorra cuota sin perder nada.
DEFAULT_POLL_INTERVALS: dict[str, int] = {
    "freelancer": 180,
    "github": 600,
    "stackexchange": 900,
    "reddit": 600,
}


def build_adapter(name: str, **kwargs: object) -> HttpSourceAdapter:
    try:
        cls = ADAPTERS[name]
    except KeyError as exc:
        raise KeyError(f"Fuente desconocida: {name}. Disponibles: {sorted(ADAPTERS)}") from exc
    return cls(**kwargs)  # type: ignore[arg-type]


def adapters_for_track(track: Track) -> list[str]:
    return [name for name, cls in ADAPTERS.items() if cls.track == track]


__all__ = [
    "ADAPTERS",
    "DEFAULT_POLL_INTERVALS",
    "FreelancerAdapter",
    "GithubAdapter",
    "HttpSourceAdapter",
    "RedditAdapter",
    "SourceAdapter",
    "SourceError",
    "SourceNotConfigured",
    "StackExchangeAdapter",
    "adapters_for_track",
    "build_adapter",
]
