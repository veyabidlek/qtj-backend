# CLAUDE.md — Backend Rules

## Project

Locomotive digital twin backend. FastAPI, Python 3.11+, PostgreSQL (Docker local, Supabase production). Real-time telemetry ingestion, health index calculation, WebSocket streaming.

## Project Structure

```
backend/
├── app/
│   ├── main.py                    # FastAPI app factory, lifespan, CORS
│   ├── config.py                  # Pydantic Settings, env vars
│   ├── dependencies.py            # shared Depends: get_db, get_current_user
│   │
│   ├── models/                    # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── telemetry.py
│   │   ├── alert.py
│   │   └── health_config.py
│   │
│   ├── schemas/                   # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── telemetry.py
│   │   ├── alert.py
│   │   ├── health.py
│   │   └── common.py             # pagination, error responses
│   │
│   ├── api/                       # route handlers grouped by domain
│   │   ├── __init__.py
│   │   ├── router.py             # main APIRouter aggregating all sub-routers
│   │   ├── telemetry.py
│   │   ├── health.py
│   │   ├── alerts.py
│   │   ├── history.py
│   │   ├── export.py
│   │   └── ws.py                 # WebSocket endpoint
│   │
│   ├── services/                  # business logic, no HTTP awareness
│   │   ├── __init__.py
│   │   ├── telemetry_service.py
│   │   ├── health_calculator.py
│   │   ├── alert_service.py
│   │   ├── export_service.py
│   │   └── ws_manager.py         # WebSocket connection manager
│   │
│   ├── repositories/              # database queries, raw SQL or ORM
│   │   ├── __init__.py
│   │   ├── telemetry_repo.py
│   │   ├── alert_repo.py
│   │   └── health_config_repo.py
│   │
│   ├── core/                      # cross-cutting concerns
│   │   ├── __init__.py
│   │   ├── database.py           # engine, sessionmaker, Base
│   │   ├── security.py           # auth, API key validation
│   │   ├── exceptions.py         # custom exception classes
│   │   └── logging.py            # structured logging setup
│   │
│   └── utils/                     # pure helper functions
│       ├── __init__.py
│       ├── smoothing.py          # EMA, median filter
│       ├── validators.py         # telemetry data validation
│       └── time_helpers.py
│
├── simulator/                     # telemetry simulator (standalone)
│   ├── __init__.py
│   ├── main.py                   # entry point
│   ├── scenarios.py              # normal, overheat, brake_failure, highload
│   └── generator.py              # data generation logic
│
├── migrations/                    # Alembic migrations
│   ├── versions/
│   ├── env.py
│   └── alembic.ini
│
├── tests/
│   ├── conftest.py
│   ├── test_health_calculator.py
│   └── test_telemetry.py
│
├── health_config.yaml             # health index weights, thresholds (no recompile)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
├── .env.example
└── CLAUDE.md
```

## Architecture Rules

1. Follow strict layering: `api/ → services/ → repositories/ → database`. Never import from `api/` in `services/`. Never import from `services/` in `models/`.
2. Route handlers in `api/` must be thin: validate input, call service, return response. No business logic, no direct DB queries in route handlers.
3. All business logic lives in `services/`. Services receive data as Pydantic schemas or primitives, never raw `Request` objects.
4. All database access lives in `repositories/`. Services call repositories, never construct queries directly.
5. Models (`models/`) are SQLAlchemy ORM classes. Schemas (`schemas/`) are Pydantic models. Never mix them. Never return ORM models from API endpoints.
6. Use `dependencies.py` for all shared FastAPI `Depends()`: database session, current user, config. Keep dependency functions small and focused.
7. Never import `app` instance in modules. Use `APIRouter` everywhere, aggregate in `api/router.py`, include in `main.py` once.

## FastAPI Rules

8. Use `lifespan` context manager in `main.py` for startup/shutdown (DB pool, WebSocket manager, simulator). No `@app.on_event` — it is deprecated.
9. Always define `response_model` on endpoints. Always define status codes explicitly: `@router.get("/health", response_model=HealthResponse, status_code=200)`.
10. Use `Annotated[T, Depends(...)]` syntax for dependency injection, not default parameter values. Example: `db: Annotated[AsyncSession, Depends(get_db)]`.
11. Group routes by domain in separate files. Each file creates its own `APIRouter(prefix="/telemetry", tags=["telemetry"])`.
12. Return Pydantic schemas from all endpoints. Never return raw dicts. Never return SQLAlchemy model instances.
13. Use `HTTPException` for expected errors (404, 400, 409). Use custom exception handlers for unexpected errors. Never let raw 500 tracebacks reach the client.
14. Enable OpenAPI docs automatically. Add `summary` and `description` to every endpoint. Add `response_model` examples in schemas using `model_config = ConfigDict(json_schema_extra={"example": {...}})`.

## Database Rules

15. Use SQLAlchemy 2.0 async with `asyncpg`. Engine via `create_async_engine`. Sessions via `async_sessionmaker`.
16. All DB operations must be `async`. Use `await session.execute(...)`, not sync `session.query(...)`.
17. Use Alembic for ALL schema changes. Never modify tables manually. Run `alembic revision --autogenerate -m "description"` for every model change.
18. Connection string from env var `DATABASE_URL`. The app does not care where PostgreSQL runs — it just reads this env var.
    - Local dev: `postgresql+asyncpg://postgres:postgres@localhost:5432/locomotive` (Docker container)
    - Production: `postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres` (Supabase pooler)
19. Always use connection pooling. For local dev: `pool_size=5, max_overflow=10`. For production (Supabase): `pool_size=10, max_overflow=20, pool_timeout=30, pool_recycle=1800`. Detect via `ENVIRONMENT` env var.
20. Alembic migrations: ALWAYS run against direct connection (port 5432), never through pooler (port 6543). In local dev this doesn't matter. In production, set `MIGRATION_DATABASE_URL` separately pointing to Supabase direct connection.
21. Use `UUID` as primary key for all tables. Generate with `uuid4()` server-side, not in database.
22. Every table must have `created_at` (server default `now()`) and `updated_at` (auto-update on change) timestamp columns.
23. Telemetry table: partition by time or use index on `timestamp` column. Add index on `(locomotive_id, timestamp DESC)` for fast range queries.
24. Use `select()` with explicit columns when you don't need the full row. Avoid `select(Model)` when you only need 2-3 fields.
25. Wrap multi-step operations in transactions. Use `async with session.begin():` for implicit commit/rollback.

## Pydantic / Schemas Rules

26. Use Pydantic V2 (`BaseModel` with `model_config`). No Pydantic V1 syntax.
27. Every schema must have `model_config = ConfigDict(from_attributes=True)` if it maps from ORM model.
28. Separate schemas by purpose: `TelemetryCreate` (input), `TelemetryResponse` (output), `TelemetryInDB` (internal). Never use one schema for everything.
29. Use `Field()` with `description`, `ge`, `le`, `examples` on all fields. This auto-generates good OpenAPI docs.
30. Validate telemetry ranges in schemas: `speed: float = Field(ge=0, le=300)`, `fuel_level: float = Field(ge=0, le=100)`, etc. Reject garbage at the boundary.
31. Use `datetime` for all timestamps. Accept ISO 8601. Return ISO 8601. Never use Unix timestamps in API responses.

## WebSocket Rules

32. Single WebSocket endpoint: `ws://host/api/ws/telemetry`. Managed by `WSManager` class in `services/ws_manager.py`.
33. `WSManager` maintains a set of connected clients. Methods: `connect(ws)`, `disconnect(ws)`, `broadcast(data)`. Thread-safe via `asyncio.Lock` if needed.
34. Send data as JSON over WebSocket. Same schema as REST response for telemetry snapshot. Clients must be able to use same types for REST and WS data.
35. Handle client disconnects gracefully. Catch `WebSocketDisconnect`, remove from active set, log. Never let one broken client crash the broadcast loop.
36. Implement heartbeat: server sends `{"type": "ping"}` every 30 seconds. Client responds with `{"type": "pong"}`. If no pong in 60 seconds, server drops the connection.
37. Rate limit outbound messages: max 5 messages/second per client. Buffer and send latest snapshot, drop intermediate if client is slow.
38. WebSocket endpoint should accept optional query params: `?locomotive_id=LOC-001` for filtering.

## Health Index Rules

39. Health index formula must be configurable via `health_config.yaml`. No hardcoded weights or thresholds in code.
40. Config structure:

```yaml
parameters:
  coolant_temp:
    weight: 0.20
    ideal: 85.0
    min: 60.0
    max: 110.0
    critical_above: 105.0
  oil_pressure:
    weight: 0.20
    ideal: 4.5
    min: 2.0
    max: 7.0
    critical_below: 2.5
  # ... etc

penalties:
  warning_alert: 10
  critical_alert: 25

categories:
  normal: { min: 80, label: "Норма", color: "#22c55e" }
  warning: { min: 50, label: "Внимание", color: "#eab308" }
  critical: { min: 0, label: "Критично", color: "#ef4444" }
```

41. Reload config without restart: add `GET /api/health/config/reload` endpoint (admin only).
42. Health calculator must return: overall score (0-100), category, and top-5 contributing factors with their individual scores and weight contributions.
43. Health calculator is a pure function: takes telemetry snapshot + config, returns health result. No side effects, no DB calls. Easy to test.

## Simulator Rules

44. Simulator is a standalone Python script that connects to the backend via WebSocket or HTTP POST. It does NOT share the FastAPI process.
45. Support multiple scenarios via CLI arg: `python -m simulator --scenario=normal|overheat|brake_failure|highload`.
46. `normal`: steady cruise, small noise. `overheat`: coolant temp rises gradually. `brake_failure`: brake pressure drops. `highload`: 10x message rate.
47. Add realistic noise: each parameter = base_value + trend + random_noise (Gaussian, σ = 2% of range).
48. Simulator sends position data (lat/lng) along a predefined route (e.g., Astana → Almaty rail line coordinates).

## Environment Strategy

Two environments, one codebase. Only `DATABASE_URL` and `ENVIRONMENT` change.

### Local Development (Docker + PostgreSQL)

49. Local dev runs via `docker-compose up`. This starts: PostgreSQL 16, backend (FastAPI), simulator. No Supabase dependency for local dev.
50. PostgreSQL container config: user `postgres`, password `postgres`, db `locomotive`, port `5432`. Defined in `docker-compose.yml`.
51. Seed script: `python -m app.seed` to populate initial data (locomotive info, health config, sample telemetry). Run automatically on first `docker-compose up` via entrypoint.
52. Hot reload: mount source code as volume, run with `uvicorn app.main:app --reload`. Changes apply instantly without rebuilding container.
53. Local `.env` file:

```
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/locomotive
CORS_ORIGINS=http://localhost:3000
LOG_LEVEL=DEBUG
API_KEY=dev-secret-key
```

### Production (Supabase)

54. Supabase is just managed PostgreSQL. Do NOT use `supabase-py` client library. Connect directly via SQLAlchemy + asyncpg.
55. Use Supabase connection pooler (PgBouncer, port 6543, transaction mode) for the app. Direct connection (port 5432) only for Alembic migrations.
56. Enable Row Level Security (RLS) on all tables in Supabase, even if policies are permissive for now.
57. Store exported reports (PDF/CSV) in Supabase Storage if needed. Use presigned URLs for download.
58. Never commit Supabase credentials. Production env vars set in hosting platform (Vercel/Railway/Render), never in files.
59. Production `.env.example`:

```
ENVIRONMENT=production
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
MIGRATION_DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-[region].supabase.com:5432/postgres
CORS_ORIGINS=https://your-domain.com
LOG_LEVEL=INFO
API_KEY=<generate-secure-key>
```

## Config & Environment

60. Use Pydantic `BaseSettings` for all config. Load from `.env` file. No `os.getenv()` scattered in code.
61. Required env vars: `ENVIRONMENT`, `DATABASE_URL`, `CORS_ORIGINS`, `LOG_LEVEL`, `API_KEY`. Optional: `MIGRATION_DATABASE_URL`, `WS_PORT`, `API_PORT`.
62. `CORS_ORIGINS` must be a comma-separated list. Parse in config. Default for dev: `http://localhost:3000`.
63. Never log sensitive values (DATABASE_URL, API_KEY). Mask in startup logs.
64. Config must detect environment and adjust behavior:

```python
class Settings(BaseSettings):
    environment: str = "development"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

## Error Handling

65. Define custom exceptions in `core/exceptions.py`: `TelemetryValidationError`, `HealthConfigError`, `LocomotiveNotFoundError`.
66. Register global exception handlers in `main.py` that convert custom exceptions to proper HTTP responses with consistent JSON shape: `{"error": "code", "message": "human readable", "details": {...}}`.
67. Log all unhandled exceptions with full traceback. Return generic 500 to client, never expose internals.

## Logging

68. Use `structlog` for structured JSON logging. No `print()` statements. No bare `logging.info("string")`.
69. Log format: `{"timestamp": "...", "level": "...", "event": "...", "locomotive_id": "...", ...}`.
70. Log every WebSocket connect/disconnect, every alert triggered, every health index state change (normal→warning, warning→critical). Do not log every telemetry tick — too noisy.
71. Log level from env var `LOG_LEVEL`. Default `INFO` in production, `DEBUG` in development.

## Performance Rules

72. Use `asyncio` everywhere. No blocking calls. If you must call blocking code (file I/O, CPU-heavy), use `run_in_executor`.
73. Health index calculation must complete in < 5ms per telemetry tick. It's a simple weighted sum — keep it that way.
74. Batch DB inserts for telemetry: accumulate 10-50 rows in memory, insert with `session.execute(insert(Telemetry), list_of_dicts)`. Never insert one row per tick.
75. Add data retention: delete telemetry older than 72 hours. Run cleanup as background task every hour via `asyncio.create_task` in lifespan.
76. API response time target: < 100ms for REST endpoints (p95). Measure with middleware.

## Security

77. Protect admin endpoints (config reload, threshold changes) with API key auth via `X-API-Key` header.
78. Validate and sanitize all input. Pydantic handles most of it, but double-check query params for SQL injection vectors in raw queries.
79. Set CORS to exact frontend origin(s). Never use `allow_origins=["*"]` in production.
80. Rate limit REST endpoints: 100 req/min per IP. Use `slowapi` or custom middleware.

## Docker

81. Use multi-stage Dockerfile: build stage installs deps, runtime stage copies only what's needed.
82. `docker-compose.yml` for local dev must include: `postgres` (with named volume), `backend` (depends on postgres, mounts source for hot reload), `simulator` (depends on backend).
83. Healthcheck on backend container: `curl -f http://localhost:8000/api/health || exit 1`.
84. Postgres data volume must be named, not anonymous. Never lose data on `docker-compose down`.
85. Example `docker-compose.yml` services:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: locomotive
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  backend:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    env_file: .env
    volumes:
      - .:/app

  simulator:
    build:
      context: .
      dockerfile: simulator/Dockerfile
    depends_on:
      - backend

volumes:
  pgdata:
```

## Testing

86. Test the health calculator thoroughly — it is the core algorithm. Test edge cases: all params normal, all critical, single param critical, alert penalties.
87. Use `pytest` + `pytest-asyncio`. Use `httpx.AsyncClient` for endpoint tests.
88. Test database operations against a real PostgreSQL (use the Docker container from docker-compose). No SQLite for tests — behavior differs.

## File Naming

89. All Python files: `snake_case.py`. All classes: `PascalCase`. All functions and variables: `snake_case`.
90. One model per file in `models/`. One router per file in `api/`. One service per file in `services/`.
91. No circular imports. If two services need each other, extract shared logic into a third module.

## Git

92. Commit after each working feature. Message format: `feat: add health calculator`, `fix: websocket reconnect`, `chore: add docker healthcheck`.
93. Do not commit: `.env`, `__pycache__/`, `.venv/`, `*.pyc`, `.idea/`, `.vscode/`.
94. `.env.example` must always be up to date with all required variables (placeholder values only).
