from __future__ import annotations

import httpx
import pytest
import respx

from painradar.models.enums import Track
from painradar.sources.freelancer import FreelancerAdapter
from tests.conftest import load_fixture


@pytest.fixture
def payload() -> dict:
    return load_fixture("freelancer_active_projects")


def test_normaliza_proyecto_completo(settings, payload) -> None:
    adapter = FreelancerAdapter(settings=settings)
    raw = payload["result"]["projects"][0]
    users = payload["result"]["users"]

    item = adapter.normalize(raw, users)

    assert item is not None
    assert item.external_id == "38472911"
    assert item.track == Track.SALES
    assert str(item.url) == (
        "https://www.freelancer.com/projects/data-processing/migracion-base-datos-sql"
    )
    assert item.budget_min == 750.0
    assert item.budget_max == 1500.0
    assert item.currency == "USD"
    assert item.is_hourly is False
    assert item.bids_count == 4
    assert item.client_country == "United States"
    assert item.client_rating == 4.8
    assert item.client_payment_verified is True
    assert "PostgreSQL" in item.tags


def test_detecta_proyecto_por_hora_y_cliente_sin_verificar(settings, payload) -> None:
    adapter = FreelancerAdapter(settings=settings)
    item = adapter.normalize(payload["result"]["projects"][1], payload["result"]["users"])

    assert item is not None
    assert item.is_hourly is True
    assert item.currency == "EUR"
    assert item.client_payment_verified is False
    assert item.budget_display == "30-60 EUR/h"


def test_descarta_proyecto_sin_seo_url(settings) -> None:
    adapter = FreelancerAdapter(settings=settings)
    assert adapter.normalize({"id": 1, "title": "x"}) is None


def test_sin_token_no_esta_configurada() -> None:
    from painradar.config import Settings

    adapter = FreelancerAdapter(settings=Settings(_env_file=None))  # type: ignore[call-arg]
    assert adapter.is_configured() is False


@respx.mock
async def test_fetch_manda_el_header_oauth(settings, payload) -> None:
    route = respx.get("https://www.freelancer.com/api/projects/0.1/projects/active/").mock(
        return_value=httpx.Response(200, json=payload)
    )

    adapter = FreelancerAdapter(settings=settings)
    items = await adapter.fetch(limit=3)
    await adapter.aclose()

    assert len(items) == 3
    assert route.calls[0].request.headers["Freelancer-OAuth-V1"] == "token-de-prueba"
    # full_description es lo que trae el texto que el clasificador necesita.
    assert b"full_description=true" in route.calls[0].request.url.query


@respx.mock
async def test_fetch_reintenta_ante_429(settings, payload) -> None:
    respx.get("https://www.freelancer.com/api/projects/0.1/projects/active/").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}),
            httpx.Response(200, json=payload),
        ]
    )

    adapter = FreelancerAdapter(settings=settings)
    items = await adapter.fetch(limit=3)
    await adapter.aclose()

    assert len(items) == 3
