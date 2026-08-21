"""Reddit — track de contribuciones.

Lee /new de los subreddits configurados y se queda con lo que aún no tiene
comentarios. Reddit es la fuente más ruidosa de las tres y también la más
sensible: responder de forma genérica o con cualquier tufo comercial se
castiga rápido. Por eso aquí el borrador es solo eso — un borrador.

Autenticación: OAuth2 `client_credentials` con una app de tipo *script*
(https://www.reddit.com/prefs/apps). Da lectura de contenido público sin
necesidad de las credenciales de la cuenta. El endpoint público `.json`
existe, pero Reddit lo bloquea de forma irregular; no se usa.

El User-Agent descriptivo no es cosmético: Reddit responde 429 de forma
agresiva a los agentes genéricos.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from painradar.config import Profiles, Settings, get_profiles, get_settings
from painradar.logging_setup import get_logger
from painradar.models.enums import Track
from painradar.models.schemas import NormalizedOpportunity
from painradar.sources.base import HttpSourceAdapter, SourceError, SourceNotConfigured

log = get_logger(__name__)

OAUTH_BASE = "https://oauth.reddit.com"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


class RedditAdapter(HttpSourceAdapter):
    name = "reddit"
    track = Track.CONTRIB
    base_url = OAUTH_BASE

    def __init__(
        self,
        settings: Settings | None = None,
        profiles: Profiles | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.profiles = profiles or get_profiles()
        self._token: str | None = None
        self._token_expires_at: datetime | None = None
        super().__init__(client=client)

    def is_configured(self) -> bool:
        return bool(self.settings.reddit_client_id and self.settings.reddit_client_secret)

    def _headers(self) -> dict[str, str]:
        headers = super()._headers()
        headers["User-Agent"] = self.settings.reddit_user_agent
        if self._token:
            headers["Authorization"] = f"bearer {self._token}"
        return headers

    async def _ensure_token(self) -> str:
        now = datetime.now(tz=UTC)
        if self._token and self._token_expires_at and now < self._token_expires_at:
            return self._token

        if not self.is_configured():
            raise SourceNotConfigured("Faltan REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET")

        async with httpx.AsyncClient(timeout=20.0) as auth_client:
            response = await auth_client.post(
                TOKEN_URL,
                data={"grant_type": "client_credentials"},
                auth=(
                    self.settings.reddit_client_id or "",
                    self.settings.reddit_client_secret or "",
                ),
                headers={"User-Agent": self.settings.reddit_user_agent},
            )
        if response.status_code != 200:
            raise SourceError(f"reddit: token HTTP {response.status_code} — {response.text[:200]}")

        payload = response.json()
        self._token = payload["access_token"]
        expires_in = int(payload.get("expires_in", 3600))
        # Se renueva al 90% de la vida del token, sin esperar al fallo.
        self._token_expires_at = now + timedelta(seconds=expires_in * 0.9)

        # El cliente cacheado lleva el Authorization antiguo: se descarta.
        await self.aclose()
        return self._token

    async def fetch(self, limit: int = 50) -> list[NormalizedOpportunity]:
        await self._ensure_token()
        filtros = self.profiles.contrib.filtros
        collected: dict[str, NormalizedOpportunity] = {}

        for subreddit in self.profiles.contrib.reddit.subreddits:
            if len(collected) >= limit:
                break
            payload = await self._request_json(
                f"/r/{subreddit}/new", params={"limit": 25, "raw_json": 1}
            )
            for child in (payload.get("data") or {}).get("children") or []:
                raw = child.get("data") or {}
                if filtros.solo_sin_responder and raw.get("num_comments"):
                    continue
                normalized = self.normalize(raw)
                if normalized is not None:
                    collected[normalized.external_id] = normalized

        log.info("fuente.fetch", source=self.name, encontrados=len(collected))
        return list(collected.values())[:limit]

    # -------------------------------------------------------------- normalize

    def normalize(self, raw: dict[str, Any]) -> NormalizedOpportunity | None:
        post_id = raw.get("id")
        permalink = raw.get("permalink")
        if not post_id or not permalink:
            return None
        if raw.get("stickied") or raw.get("over_18"):
            return None

        flair = raw.get("link_flair_text")
        return NormalizedOpportunity(
            source_name=self.name,
            track=self.track,
            external_id=f"reddit:{post_id}",
            url=f"https://www.reddit.com{permalink}",
            title=raw.get("title") or "(sin título)",
            description=(raw.get("selftext") or "")[:8000],
            author=raw.get("author"),
            tags=[flair] if flair else [],
            published_at=_epoch_to_dt(raw.get("created_utc")),
            container=f"r/{raw.get('subreddit')}",
            engagement_count=raw.get("num_comments"),
            is_answered=bool(raw.get("num_comments")),
            score=raw.get("score"),
            raw=raw,
        )


def _epoch_to_dt(value: Any) -> datetime:
    try:
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (TypeError, ValueError):
        return datetime.now(tz=UTC)
