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

### Shared patterns

- **Pagination**: use `PaginatedResponse` from `app/schemas/shared.py`; max page size enforced by `DOCTORS_LIST_MAX_LIMIT = 100`.
- **Soft deletes**: set `is_active = False` instead of hard-deleting rows.
- **Timestamps**: `created_at` / `updated_at` use `server_default` — do not set manually.
- **Address**: optional FK on Doctor, loaded via `lazy="selectin"`, embedded in Doctor responses.

## Tech Stack

- Python 3.11, FastAPI 0.138, Uvicorn
- SQLAlchemy 2.0 (async), asyncpg, psycopg2-binary (Alembic only)
- Pydantic v2, pydantic-settings
- Alembic 1.18.4
- PostgreSQL 15 (Docker)
