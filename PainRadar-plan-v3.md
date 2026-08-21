# PainRadar v3 — Dos carriles, dos bots, un solo pipeline

> v2 ([PainRadar-spec.md](PainRadar-spec.md)) descartó los foros públicos porque
> ahí nadie paga. Eso sigue siendo cierto — y sigue siendo irrelevante, porque
> el propósito cambió. v3 los recupera con otro objetivo.

## Por qué esto encaja y no es dispersión

El riesgo número uno del plan v2 está escrito en su propia tabla de riesgos:
**arranque en frío, 0 reseñas contra gente con 50**. Y su mitigación era
puramente táctica: "cobra barato las primeras 2-3 veces".

Ayudar en abierto ataca ese riesgo de frente. Un issue resuelto en un repo con
tracción, una respuesta aceptada en Stack Overflow o un hilo de Reddit donde
resolviste el problema de alguien son **evidencia pública y verificable de que
sabes hacer lo que dices**. Eso es exactamente lo que un perfil nuevo no tiene
y no puede comprar.

Los dos carriles no compiten: uno genera ingresos, el otro genera la
credibilidad que hace que el primero funcione.

| | `sales` | `contrib` |
|---|---|---|
| Busca | Trabajo pagado | Gente a la que ayudar |
| Fuentes | Freelancer.com, Workana (IMAP), Upwork | GitHub, Stack Exchange, Reddit |
| Gana | El presupuesto | La reputación |
| Filtro protege | Tu tiempo y tus Connects | Tu reputación |
| Métrica | Propuestas enviadas → contratos | Respuestas aceptadas → perfil público |
| Bot | `@tu_ventas_bot` | `@tu_contrib_bot` |

**Dos bots, no dos sistemas.** Comparten base de datos, adapters, dedupe,
scheduler, clasificador y reportes. Lo único separado es el token de Telegram,
el criterio de filtrado y el tipo de borrador. Un bot no vale la pena; el
segundo cuesta un puñado de líneas.

## Por qué dos bots y no un bot con dos canales

Porque son dos modos mentales distintos y mezclarlos los degrada:

- El de ventas es **urgente**: llegar en 15 minutos o no llegar. Merece
  notificación con sonido.
- El de contribuciones es **de fondo**: un hilo vive horas. Silenciarlo y
  revisarlo dos veces al día es lo correcto.

Con un solo bot acabas silenciando los dos o aguantando los dos. Separarlos
permite configurarlos distinto en el propio Telegram, sin escribir código.

---

## Arquitectura

```
              APScheduler (intervalo por fuente)
                          │
     ┌────────────────────┼────────────────────┐
     │  TRACK SALES       │  TRACK CONTRIB     │
     ▼                    ▼                    ▼
 Freelancer          GitHub              StackExchange
 EmailAlert (IMAP)   Reddit
 Upwork (fase 3)
     └────────────────────┴────────────────────┘
                          ▼
                  Normalizer → NormalizedOpportunity
                          ▼
                  Dedupe (url + (fuente, external_id))
                          ▼
                  RuleFilter ← config/perfiles.yaml
                   ├─ sales:   presupuesto, competencia, vetos
                   └─ contrib: sin responder, reciente, esfuerzo acotado
                          ▼
                  Classifier (Claude Haiku) → vertical, fit, red flags, esfuerzo
                          ▼
          ┌───────────────┴───────────────┐
          ▼                               ▼
   ProposalWriter                   ReplyWriter
   (propuesta comercial)            (respuesta técnica útil)
          ▼                               ▼
   Bot de VENTAS                    Bot de CONTRIBUCIONES
   ✅ Postulé  ❌ Descartar          ✅ Respondí  ❌ Paso
   🔄 Regenerar 📊 Ver cliente       🔄 Regenerar 🔗 Abrir
          └───────────────┬───────────────┘
                          ▼
                       outcome
```

**Sin frontend.** Los botones inline son la interfaz completa.

## Regla que no se negocia

**Ningún bot publica nada por su cuenta.**

En ventas, postular solo es la vía rápida a la suspensión. En contribuciones es
peor: una respuesta automática en Reddit o en un issue de GitHub se detecta al
instante y quema la reputación que este carril existe precisamente para
construir. El borrador ahorra 25 minutos de redacción; no sustituye tu criterio.

---

## Estado actual — Fase 1 completa ✅

Lo que ya corre, con `uv run pytest` verde (26 tests, ninguno toca la red):

| Pieza | Estado |
|---|---|
| Esqueleto `uv` + `ruff` + `mypy --strict` + `pytest` + `pre-commit` | ✅ |
| Esquema SQLAlchemy + migración Alembic aplicada | ✅ |
| `FreelancerAdapter` (OAuth2, paginación, backoff con `Retry-After`) | ✅ |
| `GithubAdapter` (issues sin responder, ignora PRs) | ✅ |
| `StackExchangeAdapter` (preguntas con 0 respuestas) | ✅ |
| `RedditAdapter` (OAuth2 client_credentials, /new) | ✅ |
| Normalizer + dedupe verificado (segunda corrida = 0 duplicados) | ✅ |
| CLI: `sources`, `profile`, `fetch --dry-run`, `init-db` | ✅ |
| `perfiles.yaml` con los dos carriles | ✅ |
| OpenSpec inicializado con los invariantes del proyecto | ✅ |

Falta lo único que no depende del código: **los tokens**.

---

## Roadmap ajustado

### Fase 1 — Base y ingesta ✅ (hecha)

Los cuatro adapters ya existen. `contrib` salió casi gratis porque el diseño
por Protocol lo permitía: cada adapter son ~130 líneas y el pipeline aguas
abajo no se enteró.

### Fase 1b — Encender (bloqueada solo por credenciales)

En orden de esfuerzo, de menor a mayor:

1. **`GITHUB_TOKEN`** — 2 minutos, sin scopes. El carril `contrib` arranca hoy.
2. **`STACKEXCHANGE_KEY`** — 5 minutos en StackApps, sin revisión. Sube la
   cuota de 300 a 10.000 peticiones/día.
3. **`REDDIT_CLIENT_ID/SECRET`** — 5 minutos, app tipo *script*.
4. **`FREELANCER_OAUTH_TOKEN`** — requiere cuenta verificada. Es el que
   desbloquea el carril de ventas y la fase 0.

Que `contrib` no dependa de ninguna cuenta de marketplace es la ventaja
escondida de este ajuste: **produce valor durante los 10-14 días que la fase 0
tarda en dar datos**, en vez de esperar de brazos cruzados.

### Fase 2 — Inteligencia y los dos bots (días 6-10)

- `RuleFilter` con criterio por carril. Incluye el filtro de estrellas de
  GitHub, con caché de repos (la Search API de issues no permite filtrar por
  estrellas, así que se resuelve aguas abajo sin pagar una llamada por issue).
- `Classifier` con Claude Haiku → JSON validado con Pydantic. En `sales`
  detecta red flags; en `contrib` estima **esfuerzo en horas** — la señal que
  decide si una contribución escala o es un agujero negro.
- `ProposalWriter` (120-180 palabras, ángulo del vertical) y `ReplyWriter`
  (respuesta técnica concreta, sin pitch, sin firma comercial: en Reddit y
  GitHub eso se castiga).
- `TelegramNotifier` parametrizado por carril; dos tokens, dos chats.
- Handler de callbacks → `outcome`.

### Fase 3 — Upwork, Workana y reportes (días 11-15)

- Solicitar API key de Upwork el día que exista la cuenta (~1 semana de revisión).
- `EmailAlertAdapter` (IMAP) para Workana.
- `UpworkAdapter` GraphQL, activable por config.
- **Reporte semanal, uno por bot.** El de ventas: propuestas, tasa de respuesta,
  presupuesto por vertical. El de contribuciones: respuestas publicadas,
  aceptadas, y en qué vertical se concentra tu rastro público.

### Fase 4 — Deploy (días 16-18)

Sin cambios respecto de v2: Docker multi-stage, VPS, healthcheck, backup diario.

### Paralelo — lo que de verdad cierra ventas

- [ ] Cuentas en Freelancer.com, Upwork y Workana.
- [ ] API key de Upwork el día 1 de tener cuenta.
- [ ] W-8BEN y método de cobro para Colombia resueltos **antes** de la primera venta.
- [ ] Vender la zona horaria: UTC-5 solapa la jornada completa de EE.UU.
- [ ] **Nuevo:** enlazar el rastro de `contrib` desde el perfil del marketplace.
      Una contribución que nadie ve no construye credibilidad.

---

## Definición de éxito, revisada

| Semana | `sales` | `contrib` |
|---|---|---|
| 4 | 15+ propuestas/semana, < 15 min de latencia | 5+ respuestas publicadas |
| 8 | Primera respuesta de cliente + datos de qué vertical rinde | 2+ respuestas aceptadas / 1 PR mergeado |
| 12 | Primer contrato cerrado | Perfil público con rastro verificable |

**La verificación que importa** sigue siendo la de v2, ahora por duplicado: al
final de la fase 0, comparar lo que el bot detectó contra lo que habrías
encontrado buscando a mano 30 minutos. Si no encuentra significativamente más,
o más rápido, el carril no justifica seguir — y es mejor saberlo en la semana 2
que en el mes 3.

## Riesgos nuevos que trae este carril

| Riesgo | Mitigación |
|---|---|
| Contribuir se come el tiempo de vender | `max_esfuerzo_horas: 2.0` en `perfiles.yaml`; el clasificador estima y descarta lo que no cabe |
| Una respuesta con tufo a IA quema la reputación | Nunca publicación automática. El `ReplyWriter` tiene prohibido el pitch y la firma comercial |
| Reddit banea por comportamiento comercial | El bot solo lee vía API oficial; publicar es manual y con tu criterio |
| Cuota de Stack Exchange agotada | Con key son 10.000/día; el diseño gasta ~3.200. El adapter registra `quota_remaining` en cada ciclo |
| Dos bots = el doble de ruido | Intervalos distintos por carril (ventas 3 min, contrib 10-15 min) y Telegram permite silenciar uno solo |
