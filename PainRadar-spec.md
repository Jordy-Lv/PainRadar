# PainRadar (versión personal) — Especificación del proyecto

## 1. Resumen

Herramienta personal de detección temprana de oportunidades de trabajo freelance/consultoría. Monitorea fuentes públicas en busca de personas o empresas que expresan un problema técnico + intención de contratar/pagar, filtra por el dominio de expertise del usuario (bases de datos, automatización empresarial, backend Java), y notifica por Telegram con un borrador de mensaje de contacto ya redactado.

**No es:** un producto para vender a terceros, ni un agregador masivo de "ideas de SaaS". Es un radar de leads para una sola persona.

**Éxito = ** 3-5 leads accionables al mes, detectados con suficiente anticipación para contactar antes que otros freelancers.

---

## 2. Requisitos funcionales

- RF1: Consultar periódicamente varias fuentes públicas (GitHub Issues, Hacker News, Stack Exchange, Reddit cuando esté aprobado) buscando señales de dolor + intención de pago.
- RF2: Filtrar resultados por relevancia al dominio del usuario (DBA, SQL Server/Oracle/DB2/MySQL, Power Automate, automatización empresarial, backend Java/Spring).
- RF3: Clasificar cada resultado con IA: ¿es una señal real de oportunidad freelance? severidad, urgencia, ¿hay intención de pago explícita?
- RF4: Deduplicar (no notificar el mismo item dos veces).
- RF5: Generar un borrador de mensaje de primer contacto, con un mini-insight técnico gratuito incluido.
- RF6: Notificar por Telegram con: fuente, link, resumen del problema, y el borrador.
- RF7: Marcar leads como contactado/descartado (para no repetir seguimiento).

## 3. Requisitos no funcionales / restricciones

- Uso personal, bajo volumen — nada de infraestructura para escala masiva.
- Costo operativo cercano a $0/mes.
- Debe correr 24/7 para no perder frescura de los leads (no vale correrlo solo cuando el usuario prende su PC).
- Cumplir los términos de cada API (especialmente Reddit: acceso no comercial, requiere aprobación previa desde junio 2026, cola de 2-4 semanas).
- El código debe servir como práctica de Java/Spring Boot (parte del objetivo es aprendizaje, no solo el resultado).

---

## 4. Arquitectura de alto nivel

```
                ┌─────────────────┐
                │   Scheduler      │  (Spring @Scheduled, cada 1-4h)
                └────────┬─────────┘
                         │
        ┌────────────────┼────────────────┬──────────────┐
        ▼                ▼                ▼              ▼
  GitHubAdapter     HNAdapter      StackExchangeAdapter  RedditAdapter (fase 2)
        │                │                │              │
        └────────────────┴────────────────┴──────────────┘
                         │
                         ▼
                ┌─────────────────┐
                │   Normalizer     │  → RawItem { source, url, text, author, date }
                └────────┬─────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Dedup (Postgres)│  → descarta si url/hash ya existe
                └────────┬─────────┘
                         │
                         ▼
                ┌─────────────────┐
                │  AI Classifier   │  (Claude API) → PainSignal
                │  - relevante?    │
                │  - severidad     │
                │  - intención pago│
                │  - borrador msg  │
                └────────┬─────────┘
                         │
                    ¿score > umbral?
                         │
                         ▼
                ┌─────────────────┐
                │ Telegram Notifier│
                └─────────────────┘
```

---

## 5. Modelo de datos (Postgres, vía Flyway)

```sql
-- fuente de origen
CREATE TABLE source (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,        -- 'github', 'hackernews', 'stackexchange', 'reddit'
    enabled BOOLEAN DEFAULT TRUE
);

-- item crudo recolectado
CREATE TABLE raw_item (
    id BIGSERIAL PRIMARY KEY,
    source_id INT REFERENCES source(id),
    external_id VARCHAR(255) NOT NULL,  -- id nativo de la fuente
    url TEXT NOT NULL UNIQUE,
    title TEXT,
    body TEXT,
    author VARCHAR(255),
    published_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT now()
);

-- resultado de clasificación IA
CREATE TABLE pain_signal (
    id BIGSERIAL PRIMARY KEY,
    raw_item_id BIGINT REFERENCES raw_item(id),
    is_relevant BOOLEAN,
    domain_match VARCHAR(100),          -- ej: 'dba', 'automation', 'backend'
    severity SMALLINT,                  -- 1-5
    payment_intent SMALLINT,            -- 1-5
    summary TEXT,
    draft_message TEXT,
    status VARCHAR(20) DEFAULT 'new',   -- new | notified | contacted | discarded
    created_at TIMESTAMP DEFAULT now()
);
```

---

## 6. Adapters de fuentes (interfaz común)

```java
public interface SourceAdapter {
    String sourceName();
    List<RawItem> fetchRecent(); // últimos N items desde el último fetch exitoso
}
```

**Fase 1 (implementar primero, sin espera de aprobación):**
- `GitHubIssueAdapter`: GitHub Search API, issues con label `help wanted`/`bounty`, filtrando por keywords de dominio (java, spring, sql server, oracle, power automate, etl, database automation). Auth: token personal, 5000 req/hora.
- `HackerNewsAdapter`: Algolia HN Search API (`hn.algolia.com/api/v1/search`), sin auth, buscar por keywords + "Ask HN"/"Who is hiring".
- `StackExchangeAdapter`: API de dba.stackexchange.com y stackoverflow.com filtrando por tags relevantes, con key gratuita.

**Fase 2 (cuando Reddit apruebe el acceso):**
- `RedditAdapter`: OAuth2 script app, 100 QPM, subreddits objetivo: r/sysadmin, r/SQLServer, r/oracle, r/PowerAutomate, r/dataengineering. Solicitar la aprobación del lado de Reddit desde el día 1 del proyecto, en paralelo a construir fase 1.

---

## 7. Clasificador IA (prompt base — ajustar con ejemplos reales)

Modelo sugerido: Claude Haiku (costo bajo, volumen bajo justifica no usar un modelo más caro).

Input al modelo: texto crudo del item + contexto del dominio del usuario.
Output esperado (JSON estructurado):

```json
{
  "is_relevant": true,
  "domain_match": "dba",
  "severity": 4,
  "payment_intent": 3,
  "summary": "Usuario busca automatizar reportes de errores en SQL Server, actualmente lo hace manual cada semana",
  "draft_message": "Borrador de comentario/mensaje con un insight técnico gratuito + oferta sutil de ayuda"
}
```

Reglas para el prompt:
- Rechazar como no relevante cualquier cosa fuera del dominio declarado (evitar ruido).
- `payment_intent` solo alto si hay lenguaje explícito de presupuesto, contratación, o frustración con costo actual — no inferir de la nada.
- El `draft_message` debe sonar natural, aportar valor primero, sin ofrecer el servicio de forma agresiva (riesgo de baneo en foros técnicos).

---

## 8. Notificación (Telegram)

- Crear un bot con @BotFather, guardar `TELEGRAM_BOT_TOKEN` y el `CHAT_ID` del usuario.
- Un `TelegramNotifier` envía un mensaje por cada `pain_signal` nuevo con score sobre el umbral, formato:

```
🎯 [dba] Severidad 4 · Intención de pago 3
Fuente: GitHub Issues
{resumen}
{url}

Borrador de mensaje:
{draft_message}
```

---

## 9. Scheduling

- `@Scheduled(cron = "0 0 */2 * * *")` — cada 2 horas, ajustable por fuente si alguna tiene límites más estrictos.
- Guardar `last_fetched_at` por fuente para no re-consultar desde cero cada vez.

---

## 10. Stack técnico final

| Capa | Elección |
|---|---|
| Backend | Java 21 + Spring Boot 3.5 |
| DB | PostgreSQL + Flyway |
| Jobs | Spring `@Scheduled` |
| HTTP client | Spring `RestClient` |
| IA | Anthropic API (Claude Haiku) |
| Notificación | Telegram Bot API |
| Hosting | Oracle Cloud Free Tier (VM ARM Always Free) |
| Empaque | Docker + docker-compose |

---

## 11. Estructura de carpetas sugerida

```
painradar/
├── src/main/java/com/jordy/painradar/
│   ├── adapter/          (GitHubIssueAdapter, HackerNewsAdapter, StackExchangeAdapter, RedditAdapter)
│   ├── domain/            (RawItem, PainSignal, Source — entidades JPA)
│   ├── classifier/         (ClaudeClassifierService)
│   ├── notifier/           (TelegramNotifier)
│   ├── scheduler/          (FetchScheduler)
│   ├── repository/         (Spring Data JPA repos)
│   └── config/
├── src/main/resources/
│   ├── db/migration/       (scripts Flyway)
│   └── application.yml
├── docker-compose.yml
└── Dockerfile
```

---

## 12. Variables de entorno necesarias

```
DB_URL, DB_USER, DB_PASSWORD
GITHUB_TOKEN
ANTHROPIC_API_KEY
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
REDDIT_CLIENT_ID (fase 2)
REDDIT_CLIENT_SECRET (fase 2)
DOMAIN_KEYWORDS  (lista de keywords del dominio del usuario, configurable sin recompilar)
```

---

## 13. Roadmap de construcción

**Fase 0 (día 1):** Solicitar acceso a la API de Reddit (cola de aprobación de 2-4 semanas) para no bloquear después.

**Fase 1:** Proyecto base Spring Boot + Postgres + Flyway. Adapter de GitHub funcionando end-to-end (fetch → normalize → guardar en DB), sin IA todavía — validar que la ingesta funciona.

**Fase 2:** Agregar clasificador IA + Telegram notifier. Validar con datos reales que el filtro de relevancia funciona bien (ajustar el prompt).

**Fase 3:** Agregar HackerNews y StackExchange adapters.

**Fase 4:** Cuando Reddit apruebe, agregar RedditAdapter.

**Fuera de alcance para v1:** frontend web, multi-tenancy, autenticación, dashboard — no se necesitan para uso personal.

---

## 14. Nota de cumplimiento

Revisar y respetar los términos de uso de cada plataforma (especialmente Reddit y GitHub) antes de automatizar contacto directo. Este sistema solo detecta y redacta borradores — el envío de mensajes en foros/Reddit debe hacerlo el usuario manualmente para evitar baneos por automatización de contacto.
