# Sora Studio — API (FastAPI)

Backend multi-tenant da plataforma **Sora Studio**, com arquitetura **Zero-Leak**
(Row-Level Security + RBAC em 3 níveis) e motor financeiro em `Decimal`.

## Stack

- Python 3.12 + FastAPI (async) + Pydantic v2
- SQLAlchemy 2.0 (async) + asyncpg + Alembic
- Redis 7 (locks, refresh tokens, filas)
- PostgreSQL 16 com RLS (`sora_app` `NOBYPASSRLS` em runtime; `sora` só para migrations)

## Setup

```bash
uv sync                 # instala dependências + grupo dev (lint, mypy, testes)
uv run ruff check .     # lint
uv run mypy app         # type-check
uv run pytest -q --cov=app --cov-fail-under=80
```

## Rodar localmente

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://127.0.0.1:8000/health`
- Domínio roteado pelo Traefik (dev): `http://api.sora.localhost:8000`

> As variáveis de ambiente são lidas de `.env` (raiz do monorepo) ou do ambiente.
> Veja o modelo em `.env.example` na raiz.
