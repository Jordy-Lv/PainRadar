"""Graba respuestas reales de las APIs como fixtures de test.

Las fixtures incluidas en el repo están escritas a mano siguiendo la forma
documentada de cada API. En cuanto haya credenciales, este script las
reemplaza por respuestas reales — que es lo único que detecta cuando una API
cambia sin avisar.

    uv run python scripts/record_fixtures.py --source freelancer

Cuidado: la respuesta cruda puede traer datos personales del cliente
(nombres, países, historial). Revisa el JSON antes de commitearlo.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import httpx

from painradar.config import get_profiles, get_settings

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures"

TARGETS: dict[str, tuple[str, str, dict[str, Any]]] = {
    # nombre -> (fichero, url, params)
    "freelancer": (
        "freelancer_active_projects",
        "{base}/projects/0.1/projects/active/",
        {
            "limit": 5,
            "full_description": "true",
            "job_details": "true",
            "user_details": "true",
            "user_country_details": "true",
            "user_status": "true",
            "user_employer_reputation": "true",
        },
    ),
    "github": (
        "github_search_issues",
        "https://api.github.com/search/issues",
        {"q": 'is:issue is:open no:assignee label:"help wanted" language:Python', "per_page": 5},
    ),
    "stackexchange": (
        "stackexchange_questions",
        "https://api.stackexchange.com/2.3/search/advanced",
        {
            "site": "stackoverflow",
            "tagged": "python",
            "answers": 0,
            "order": "desc",
            "sort": "creation",
            "pagesize": 5,
            "filter": "withbody",
        },
    ),
}


async def record(source: str) -> Path:
    settings = get_settings()
    get_profiles()
    filename, url_template, params = TARGETS[source]
    url = url_template.format(base=settings.freelancer_base_url)

    headers: dict[str, str] = {"User-Agent": "painradar/0.1"}
    if source == "freelancer":
        token = settings.freelancer_oauth_token
        if not token:
            raise SystemExit("Falta FREELANCER_OAUTH_TOKEN en el .env")
        headers["Freelancer-OAuth-V1"] = token
    elif source == "github":
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"
    elif source == "stackexchange" and settings.stackexchange_key:
        params = {**params, "key": settings.stackexchange_key}

    async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        payload = response.json()

    target = FIXTURES_DIR / f"{filename}.real.json"
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=sorted(TARGETS))
    args = parser.parse_args()

    path = asyncio.run(record(args.source))
    print(f"Grabado en {path}")
    print("Revísalo, quita datos personales y renómbralo sin el sufijo .real")


if __name__ == "__main__":
    main()
