"""Configuración: variables de entorno (secretos) + perfiles.yaml (criterio)."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILES_PATH = PROJECT_ROOT / "config" / "perfiles.yaml"


class Settings(BaseSettings):
    """Secretos y ajustes de entorno. Todo opcional: cada fase activa lo suyo."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # track sales
    freelancer_oauth_token: str | None = None
    freelancer_env: Literal["prod", "sandbox"] = "prod"
    imap_host: str | None = None
    imap_user: str | None = None
    imap_password: str | None = None
    upwork_client_id: str | None = None
    upwork_client_secret: str | None = None

    # track contrib
    github_token: str | None = None
    stackexchange_key: str | None = None
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "painradar/0.1"

    # ia
    anthropic_api_key: str | None = None

    # dos bots: uno vende, otro ayuda
    telegram_sales_bot_token: str | None = None
    telegram_sales_chat_id: str | None = None
    telegram_contrib_bot_token: str | None = None
    telegram_contrib_chat_id: str | None = None

    database_url: str = "sqlite:///data/painradar.db"
    mode: Literal["discovery", "live"] = "discovery"
    log_level: str = "INFO"
    profiles_path: Path = DEFAULT_PROFILES_PATH

    @property
    def freelancer_base_url(self) -> str:
        if self.freelancer_env == "sandbox":
            return "https://www.freelancer-sandbox.com/api"
        return "https://www.freelancer.com/api"


# ---------------------------------------------------------------- perfiles


class Vertical(BaseModel):
    id: str
    keywords: list[str] = Field(default_factory=list)
    angulo: str = ""
    tarifa_min_usd: float | None = None


class SalesFilters(BaseModel):
    presupuesto_min_usd: float = 0
    max_propuestas_existentes: int = 999
    paises_excluidos: list[str] = Field(default_factory=list)
    keywords_veto: list[str] = Field(default_factory=list)
    max_antiguedad_horas: float = 24


class ContribFilters(BaseModel):
    """El criterio aquí no es dinero: es 'puedo aportar algo real y llego a tiempo'."""

    max_antiguedad_horas: float = 12
    max_respuestas_existentes: int = 2
    solo_sin_responder: bool = True
    max_esfuerzo_horas: float = 2.0
    keywords_veto: list[str] = Field(default_factory=list)


class GithubTargets(BaseModel):
    labels: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    excluir_repos: list[str] = Field(default_factory=list)
    min_stars: int = 0


class StackExchangeTargets(BaseModel):
    sites: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class RedditTargets(BaseModel):
    subreddits: list[str] = Field(default_factory=list)


class ContribConfig(BaseModel):
    filtros: ContribFilters = Field(default_factory=ContribFilters)
    github: GithubTargets = Field(default_factory=GithubTargets)
    stackexchange: StackExchangeTargets = Field(default_factory=StackExchangeTargets)
    reddit: RedditTargets = Field(default_factory=RedditTargets)


class SalesConfig(BaseModel):
    filtros: SalesFilters = Field(default_factory=SalesFilters)


class Profiles(BaseModel):
    """`perfiles.yaml` completo: qué sé hacer y qué merece mi tiempo."""

    verticales: list[Vertical] = Field(default_factory=list)
    sales: SalesConfig = Field(default_factory=SalesConfig)
    contrib: ContribConfig = Field(default_factory=ContribConfig)

    def match_vertical(self, *texts: str) -> Vertical | None:
        """Primer vertical cuyas keywords aparezcan en el texto. Barato, sin IA."""
        haystack = " ".join(t.lower() for t in texts if t)
        best: tuple[int, Vertical] | None = None
        for vertical in self.verticales:
            hits = sum(1 for kw in vertical.keywords if kw.lower() in haystack)
            if hits and (best is None or hits > best[0]):
                best = (hits, vertical)
        return best[1] if best else None


def load_profiles(path: Path | None = None) -> Profiles:
    target = path or get_settings().profiles_path
    if not target.exists():
        return Profiles()
    data: dict[str, Any] = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    return Profiles.model_validate(data)


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


@functools.lru_cache(maxsize=1)
def get_profiles() -> Profiles:
    return load_profiles()
