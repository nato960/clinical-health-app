# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Backend-only FastAPI app for a clinical health system. The `frontend/` directory exists but is empty. All active code lives in `backend/`.

## Commands (run from `backend/`)

```bash
# Start the database
docker-compose up -d

# Install dependencies
pip install -r requirements.txt

# Apply migrations
alembic upgrade head

# Run dev server (hot-reload)
uvicorn app.main:app --reload

# Create a new migration
alembic revision --autogenerate -m "description"
```

API docs auto-generated at `http://localhost:8000/docs` when the server is running.

## Testing

- Stack: `pytest`, `pytest-asyncio` (`asyncio_mode = "auto"` in `backend/pyproject.toml` — no `@pytest.mark.asyncio` needed), `pytest-mock`, and `httpx.AsyncClient` with `ASGITransport` for in-process API tests (no running server required).
- Layout mirrors the architecture: `backend/tests/unit/` (services, with the repository mocked) and `backend/tests/integration/` (real DB, marked with `@pytest.mark.integration`).
- **Integration tests use a separate database**, `clinical_health_test_db`, on the same port-5433 Postgres container. `docker-compose up -d` only provisions `clinical_health_api_db` — the test database must be created manually once, or `pytest -m integration` will fail to connect.
- Isolation pattern (`backend/tests/conftest.py`): the `db_session` fixture opens a connection, starts a transaction plus a nested SAVEPOINT, and rolls the outer transaction back after each test — so tests share one schema without truncating tables between runs. The `client` fixture layers an `httpx.AsyncClient` on top and overrides `get_db` via `app.dependency_overrides` so API tests use the same isolated session.

```bash
# Run from `backend/`
pytest                        # run everything
pytest tests/unit             # unit tests only (no DB needed)
pytest -m integration         # integration tests only
pytest -m "not integration"   # skip DB-dependent tests
```

## Architecture

The backend uses a strict 4-layer architecture — every feature must follow this flow:

```
API Router (app/api/)
  → Service (app/services/)
    → Repository (app/repositories/)
      → Model (app/models/)
```

- **Routers** — HTTP handling; inject services via `Depends()`
- **Services** — business logic, uniqueness checks, pagination
- **Repositories** — all SQLAlchemy queries via `AsyncSession`
- **Models** — ORM mappings

### Async patterns

- All route handlers are `async def`.
- SQLAlchemy uses `AsyncSession` with the `asyncpg` driver.
- Session factory sets `expire_on_commit=False` — required to avoid lazy-load failures after commit.
- Alembic migrations run synchronously with `psycopg2` — this is intentional and separate from the app driver.
- Relationships use `lazy="selectin"` for async-compatible eager loading.

### Database

- PostgreSQL 15 running on **port 5433** (not the default 5432).
- Connection string in `backend/.env`: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5433/clinical_health_api_db`

### Error handling

Custom exception hierarchy in `app/core/exceptions.py`:

- `AppException` — base
- `NotFoundException` → 404
- `ConflictException` → 409 (duplicate email or CRM)
- `BusinessException` → 400

Global FastAPI exception handlers in `main.py` convert these to consistent JSON error responses.

### Logging

- Configured ad hoc in `app/main.py` via `logging.basicConfig(...)` (INFO level, stdout, `"%(asctime)s [%(levelname)s] %(name)s: %(message)s"`) — not driven by settings/env.
- Convention: every module that logs declares `logger = logging.getLogger(__name__)` at module top; follow this in new services/repositories rather than using the root logger.
- Exception handlers in `main.py` log on the way to a response: `AppException`/`RequestValidationError` → `logger.warning`, `SQLAlchemyError` → `logger.error(..., exc_info=True)`.
- Services log business events directly — e.g. `DoctorService` logs on create/deactivate, and warns before raising `ConflictException`.

### Shared patterns

- **Pagination**: use `PaginatedResponse` from `app/schemas/shared.py`; max page size enforced by `DOCTORS_LIST_MAX_LIMIT = 100`.
- **Soft deletes**: set `is_active = False` instead of hard-deleting rows. `DoctorRepository.get_by_id` excludes inactive rows by default (`active_only: bool = True`) — pass `active_only=False` to fetch a deactivated doctor.
- **Timestamps**: `created_at` / `updated_at` use `server_default` — do not set manually.
- **Address**: optional FK on Doctor, loaded via `lazy="selectin"`, embedded in Doctor responses.

## Tech Stack

- Python 3.11, FastAPI 0.138, Uvicorn
- SQLAlchemy 2.0 (async), asyncpg, psycopg2-binary (Alembic only)
- Pydantic v2, pydantic-settings
- Alembic 1.18.4
- PostgreSQL 15 (Docker)
