"""Modelos Pydantic: la frontera entre el mundo exterior y la base de datos.

`NormalizedOpportunity` es el contrato que toda fuente debe cumplir. Si una
fuente nueva puede llenar esto, entra al pipeline sin tocar nada más.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from painradar.models.enums import Track


class NormalizedOpportunity(BaseModel):
    """Una oportunidad ya traducida al vocabulario común de PainRadar."""

    model_config = ConfigDict(str_strip_whitespace=True)

    source_name: str
    track: Track
    external_id: str
    url: HttpUrl
    title: str
    description: str = ""

    author: str | None = None
    tags: list[str] = Field(default_factory=list)
    published_at: datetime

    # --- track sales ---
    budget_min: float | None = None
    budget_max: float | None = None
    currency: str | None = None
    is_hourly: bool | None = None
    bids_count: int | None = None
    client_country: str | None = None
    client_rating: float | None = None
    client_spend: float | None = None
    client_payment_verified: bool | None = None

    # --- track contrib ---
    container: str | None = None
    engagement_count: int | None = None
    is_answered: bool | None = None
    score: int | None = None

    raw: dict[str, Any] = Field(default_factory=dict, repr=False)

    @property
    def budget_display(self) -> str:
        """Presupuesto legible para el mensaje de Telegram y los logs."""
        if self.budget_min is None and self.budget_max is None:
            return "sin presupuesto"
        cur = self.currency or ""
        unit = "/h" if self.is_hourly else ""
        if self.budget_min is not None and self.budget_max is not None:
            return f"{self.budget_min:.0f}-{self.budget_max:.0f} {cur}{unit}".strip()
        value = self.budget_min if self.budget_min is not None else self.budget_max
        return f"{value:.0f} {cur}{unit}".strip()
