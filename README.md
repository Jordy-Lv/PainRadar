# PainRadar

Radar de oportunidades en dos carriles. Detecta antes que la competencia,
clasifica con IA, redacta un borrador y te lo manda a Telegram. **Nunca
publica ni postula solo.**

| Carril | Qué busca | Dónde | Bot |
|---|---|---|---|
| `sales` | Trabajo pagado | Freelancer.com (API oficial), Workana (IMAP), Upwork (GraphQL, fase 3) | Bot de ventas |
| `contrib` | Gente a la que ayudar en abierto | GitHub, Stack Exchange, Reddit | Bot de contribuciones |

Los dos carriles comparten pipeline, base de datos y verticales. Lo que
cambia es el criterio: en `sales` gana el presupuesto, en `contrib` gana la
reputación — que es justo el activo que le falta a un perfil recién creado.

## Puesta en marcha

```bash
uv sync
cp .env.example .env      # y rellena lo que tengas
uv run alembic upgrade head
uv run painradar sources  # qué fuentes están configuradas
```

Ninguna credencial es obligatoria: cada fuente sin token se salta sola, sin
tumbar el ciclo.

## Comandos

```bash
uv run painradar sources                                  # estado de las fuentes
uv run painradar profile                                  # verticales cargados
uv run painradar fetch --source freelancer --dry-run      # imprime, no escribe
uv run painradar fetch --track contrib --limit 30         # ingesta un carril entero
```

## Credenciales

| Variable | Dónde se saca | Carril |
|---|---|---|
| `FREELANCER_OAUTH_TOKEN` | https://accounts.freelancer.com/settings/develop | sales |
| `GITHUB_TOKEN` | Settings → Developer settings → Tokens. Sin scopes basta | contrib |
| `STACKEXCHANGE_KEY` | https://stackapps.com/apps/oauth/register — sube la cuota de 300 a 10.000/día | contrib |
| `REDDIT_CLIENT_ID` / `_SECRET` | https://www.reddit.com/prefs/apps, tipo *script* | contrib |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com | fase 2 |
| `TELEGRAM_*_BOT_TOKEN` | @BotFather, **dos bots distintos** | fase 2 |

## Desarrollo

```bash
uv run pytest          # ningún test toca la red
uv run ruff check src/ tests/
uv run mypy
uv run pre-commit install
```

Las fixtures de `tests/fixtures/` están escritas siguiendo la forma
documentada de cada API. Cuando tengas credenciales, regrábalas contra
respuestas reales — es lo único que detecta un cambio de API silencioso:

```bash
uv run python scripts/record_fixtures.py --source freelancer
```

## Estructura

```
src/painradar/
├── sources/      adapters por fuente, aislados tras un Protocol
├── pipeline/     normalizar → deduplicar → guardar (→ filtrar → clasificar, fase 2)
├── models/       tablas SQLAlchemy + esquemas Pydantic
├── config.py     .env (secretos) + perfiles.yaml (criterio)
└── cli.py
config/perfiles.yaml   ← el único archivo que hay que tocar para cambiar el criterio
```

## Documentación viva

El comportamiento del sistema está especificado en `openspec/specs/`, y esa es
la fuente de verdad — no el código. La regla del proyecto es que la spec se
actualiza en el mismo turno que el código (ver [CLAUDE.md](CLAUDE.md)).

```bash
openspec validate --all --strict   # 5 capacidades, 24 requisitos, 39 escenarios
openspec list
```

| Capacidad | Qué garantiza |
|---|---|
| `ingesta-oportunidades` | Contrato común, dedupe, registro de resultado, aislamiento de fallos |
| `fuentes-ventas` | Datos suficientes para decidir una postulación, respeto de límites de API |
| `fuentes-contribuciones` | Prioridad a lo no respondido y **ninguna publicación automática** |
| `configuracion-criterio` | Criterio y secretos separados; arranque sin credenciales |
| `cli-operacion` | Inspección y ejecución manual |

## Estado

- **Fase 1 — completa.** Ingesta funcionando en 4 fuentes, dedupe verificado,
  esquema migrado, 26 tests verdes sin red.
- **Fase 0 (descubrimiento) — activa** en cuanto haya un token. `MODE=discovery`
  captura todo sin filtrar y sin gastar en IA, para decidir los verticales con
  datos en vez de con intuición.
- Fases 2-4: filtro, IA, Telegram, reportes y deploy.

## Contribuir y licencia

Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un PR. Publicado bajo
la [licencia MIT](LICENSE).
