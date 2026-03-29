# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run with Docker (recommended):**
```bash
docker-compose up
# App: http://localhost:8000
# PostgreSQL: localhost:5432
```

**Run locally:**
```bash
pip install -r requirements.txt
# Set DATABASE_URL environment variable
uvicorn main:app --reload
```

**Environment variables:**
- `DATABASE_URL` — PostgreSQL connection string (e.g. `postgresql://admin:secret@localhost:5432/finance`)
- `SECRET_KEY` — JWT secret (defaults to a dev value in `core/settings.py`)

There are no tests or linting configurations in this repository.

## Architecture

**Stack:** FastAPI + SQLAlchemy + PostgreSQL + Jinja2 server-side rendering. No separate frontend build step.

**Request flow:**
1. `main.py` — initializes the FastAPI app, mounts static files, adds middleware (session, CORS, redirect-401-to-login), registers all routers, and runs `startup_event()` which creates DB tables and seeds fixtures
2. Routes in `routes/` return `TemplateResponse` with a `TemplateContext` object that auto-populates current user, alert messages, pagination, and sort state
3. All authenticated routes use the `get_current_user` dependency from `routes/auth.py`, which reads a JWT from the session cookie

**Core modules:**
- `core/models.py` — SQLAlchemy ORM: `User`, `Account`, `Card`, `Category`, `Budget`, `Transaction`. All entities cascade-delete from `User`.
- `core/schemas.py` — Pydantic models for request validation and a `TemplateContext` model that drives the generic CRUD UI
- `core/fixtures.py` — Seed data applied at startup (accounts, cards, categories, budgets)
- `core/database.py` — Engine, session factory, and `Base`

**Generic CRUD UI pattern:**
The frontend uses a set of reusable components (`templates/components/crud_modal.html`, `datagrid.html`, `detail_modal.html`) driven by schema definitions. Routes pass lists of `Column`, `CrudField`, `FilterField`, and `DetailField` Pydantic objects to describe what to render — the templates iterate over these to build tables, modals, and forms dynamically.

**Transaction model complexity:**
`Transaction` supports recurring transactions (weekly, biweekly, monthly, quarterly, semi-annual, annual) and has import/export via Excel (pandas + openpyxl). `routes/transactions.py` (~1400 lines) and `routes/index.py` (~700 lines, dashboard) are the most complex files.

**Dashboard period logic:**
The dashboard (`GET /`) uses a configurable billing period: by default day 20 of the previous month through day 19 of the current month. This is controlled by `first_day`/`last_day` query parameters.

**Code language:** Variable names, comments, and user-facing strings are in Portuguese.
