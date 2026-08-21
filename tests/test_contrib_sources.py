"""Tests de las fuentes del track de contribuciones."""

from __future__ import annotations

import httpx
import respx

from painradar.models.enums import Track
from painradar.sources.github import GithubAdapter
from painradar.sources.reddit import RedditAdapter
from painradar.sources.stackexchange import StackExchangeAdapter, strip_html
from tests.conftest import load_fixture

# ------------------------------------------------------------------- github


def test_github_normaliza_issue(settings, profiles) -> None:
    adapter = GithubAdapter(settings=settings, profiles=profiles)
    raw = load_fixture("github_search_issues")["items"][0]

    item = adapter.normalize(raw)

    assert item is not None
    assert item.track == Track.CONTRIB
    assert item.container == "pandas-dev/pandas"
    assert item.engagement_count == 0
    assert item.is_answered is False
    assert item.score == 3
    assert "help wanted" in item.tags


def test_github_ignora_pull_requests(settings, profiles) -> None:
    """La Search API mezcla issues y PRs; un PR ajeno no es una oportunidad."""
    adapter = GithubAdapter(settings=settings, profiles=profiles)
    raw = load_fixture("github_search_issues")["items"][1]

    assert adapter.normalize(raw) is None


def test_github_construye_consulta_con_ventana_temporal(settings, profiles) -> None:
    from datetime import UTC, datetime

    adapter = GithubAdapter(settings=settings, profiles=profiles)
    queries = adapter._build_queries(datetime(2026, 8, 21, 0, 0, tzinfo=UTC))

    assert queries, "debe generar al menos una consulta"
    assert all("is:issue" in q and "no:assignee" in q for q in queries)
    assert all("created:>2026-08-21T00:00:00Z" in q for q in queries)
    assert any('label:"help wanted"' in q for q in queries)
    # labels x languages
    assert len(queries) == len(profiles.contrib.github.labels) * len(
        profiles.contrib.github.languages
    )


@respx.mock
async def test_github_fetch_deduplica_entre_consultas(settings, profiles) -> None:
    payload = load_fixture("github_search_issues")
    respx.get("https://api.github.com/search/issues").mock(
        return_value=httpx.Response(200, json=payload)
    )

    adapter = GithubAdapter(settings=settings, profiles=profiles)
    items = await adapter.fetch(limit=50)
    await adapter.aclose()

    # Varias consultas devuelven el mismo issue: debe aparecer una sola vez.
    assert len(items) == 1
    assert items[0].container == "pandas-dev/pandas"


# ------------------------------------------------------------ stackexchange


def test_stackexchange_normaliza_y_limpia_html(settings, profiles) -> None:
    adapter = StackExchangeAdapter(settings=settings, profiles=profiles)
    raw = load_fixture("stackexchange_questions")["items"][0]

    item = adapter.normalize(raw, "stackoverflow")

    assert item is not None
    assert item.external_id == "stackoverflow:79412233"
    assert item.container == "stackoverflow"
    assert item.is_answered is False
    assert "<p>" not in item.description
    assert "bulk_insert_mappings" in item.description


def test_strip_html_desescapa_entidades() -> None:
    assert strip_html("<p>a &lt; b</p>") == "a < b"


def test_stackexchange_params_piden_preguntas_sin_responder(settings, profiles) -> None:
    adapter = StackExchangeAdapter(settings=settings, profiles=profiles)
    params = adapter._params("stackoverflow", "python", 0)

    assert params["answers"] == 0
    assert params["filter"] == "withbody"
    assert params["key"] == "key-prueba"


# ------------------------------------------------------------------- reddit


def test_reddit_normaliza_post(settings, profiles) -> None:
    adapter = RedditAdapter(settings=settings, profiles=profiles)
    raw = load_fixture("reddit_new")["data"]["children"][0]["data"]

    item = adapter.normalize(raw)

    assert item is not None
    assert item.container == "r/learnpython"
    assert str(item.url).startswith("https://www.reddit.com/r/learnpython/")
    assert item.engagement_count == 0
    assert item.tags == ["Help"]


def test_reddit_ignora_posts_fijados(settings, profiles) -> None:
    adapter = RedditAdapter(settings=settings, profiles=profiles)
    raw = load_fixture("reddit_new")["data"]["children"][1]["data"]

    assert adapter.normalize(raw) is None


@respx.mock
async def test_reddit_pide_token_antes_de_leer(settings, profiles) -> None:
    token_route = respx.post("https://www.reddit.com/api/v1/access_token").mock(
        return_value=httpx.Response(
            200, json={"access_token": "tok123", "expires_in": 3600, "token_type": "bearer"}
        )
    )
    respx.get(url__regex=r"https://oauth\.reddit\.com/r/.+/new").mock(
        return_value=httpx.Response(200, json=load_fixture("reddit_new"))
    )

    adapter = RedditAdapter(settings=settings, profiles=profiles)
    items = await adapter.fetch(limit=10)
    await adapter.aclose()

    assert token_route.called
    # El post fijado y el que ya tiene comentarios quedan fuera.
    assert len(items) == 1
