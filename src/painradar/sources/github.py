"""GitHub — track de contribuciones.

Busca issues abiertos, recientes y **sin responder** en los lenguajes que
manejo. Aquí `help wanted` significa lo que siempre significó — "acepto
voluntarios" — y por eso esta fuente no sirve para vender. Sirve para lo
otro: dejar rastro público de trabajo real, que es exactamente lo que le
falta a un perfil de marketplace recién creado.

Rate limit: 30 req/min en la Search API con token, 10/min sin él. Un token
personal sin scopes basta para leer issues públicos.

Nota sobre `min_stars`: la Search API de issues no admite filtrar por
estrellas del repo (ese calificador solo existe para repos). El filtro vive
en el pipeline de reglas, donde una caché de repos evita pagar una llamada
por issue.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from painradar.config import Profiles, Settings, get_profiles, get_settings
from painradar.logging_setup import get_logger
from painradar.models.enums import Track
from painradar.models.schemas import NormalizedOpportunity
from painradar.sources.base import HttpSourceAdapter

log = get_logger(__name__)

SEARCH_PATH = "/search/issues"
API_BASE = "https://api.github.com"


class GithubAdapter(HttpSourceAdapter):
    name = "github"
    track = Track.CONTRIB
    base_url = API_BASE

    def __init__(
        self,
        settings: Settings | None = None,
        profiles: Profiles | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.profiles = profiles or get_profiles()
        super().__init__(client=client)

    def is_configured(self) -> bool:
        # Funciona sin token, pero con 10 req/min es inservible en la práctica.
        return bool(self.settings.github_token)

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["Accept"] = "application/vnd.github+json"
        headers["X-GitHub-Api-Version"] = "2022-11-28"
        if self.settings.github_token:
            headers["Authorization"] = f"Bearer {self.settings.github_token}"
        return headers

    async def fetch(self, limit: int = 50) -> list[NormalizedOpportunity]:
        cfg = self.profiles.contrib.github
        filtros = self.profiles.contrib.filtros
        since = datetime.now(tz=UTC) - timedelta(hours=filtros.max_antiguedad_horas)

        collected: dict[str, NormalizedOpportunity] = {}
        queries = self._build_queries(since)

        for query in queries:
            if len(collected) >= limit:
                break
            payload = await self._request_json(
                SEARCH_PATH,
                params={
                    "q": query,
                    "sort": "created",
                    "order": "desc",
                    "per_page": min(50, limit),
                },
            )
            for raw in payload.get("items") or []:
                normalized = self.normalize(raw)
                if normalized is None:
                    continue
                if _repo_of(raw) in cfg.excluir_repos:
                    continue
                collected[normalized.external_id] = normalized

        log.info(
            "fuente.fetch",
            source=self.name,
            encontrados=len(collected),
            consultas=len(queries),
        )
        return list(collected.values())[:limit]

    def _build_queries(self, since: datetime) -> list[str]:
        """Una consulta por (label × lenguaje): GitHub trata las etiquetas como AND."""
        cfg = self.profiles.contrib.github
        stamp = since.strftime("%Y-%m-%dT%H:%M:%SZ")
        base = ["is:issue", "is:open", "no:assignee", f"created:>{stamp}"]
        if self.profiles.contrib.filtros.solo_sin_responder:
            base.append("comments:0")

        labels = cfg.labels or [""]
        languages = cfg.languages or [""]
        queries: list[str] = []
        for label in labels:
            for language in languages:
                parts = list(base)
                if label:
                    parts.append(f'label:"{label}"')
                if language:
                    parts.append(f"language:{language}")
                queries.append(" ".join(parts))
        return queries

    # -------------------------------------------------------------- normalize

    def normalize(self, raw: dict[str, Any]) -> NormalizedOpportunity | None:
        issue_id = raw.get("id")
        html_url = raw.get("html_url")
        if issue_id is None or not html_url:
            return None
        # La Search API mezcla issues y PRs; los PRs ajenos no son oportunidad.
        if "pull_request" in raw:
            return None

        reactions = raw.get("reactions") or {}
        owner = raw.get("user") or {}

        return NormalizedOpportunity(
            source_name=self.name,
            track=self.track,
            external_id=str(issue_id),
            url=html_url,
            title=raw.get("title") or "(sin título)",
            description=(raw.get("body") or "")[:8000],
            author=owner.get("login"),
            tags=[label["name"] for label in raw.get("labels") or [] if label.get("name")],
            published_at=_parse_iso(raw.get("created_at")),
            container=_repo_of(raw),
            engagement_count=raw.get("comments"),
            is_answered=bool(raw.get("comments")),
            score=reactions.get("total_count"),
            raw=raw,
        )


def _repo_of(raw: dict[str, Any]) -> str | None:
    """`repository_url` viene como https://api.github.com/repos/owner/repo."""
    url = raw.get("repository_url") or ""
    marker = "/repos/"
    if marker in url:
        return url.split(marker, 1)[1]
    return None


def _parse_iso(value: Any) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)
