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

## Migrations (Alembic + RLS)

```bash
# Requer MIGRATION_DATABASE_URL (owner) apontando para o PostgreSQL
uv run alembic upgrade head
uv run alembic downgrade base   # rollback completo
```

As migrations criam as policies de **Row-Level Security**. O runtime usa o
`DATABASE_URL` com o role `sora_app` (`NOBYPASSRLS`); o `MIGRATION_DATABASE_URL`
com o owner `sora` fica restrito ao Alembic (DDL).

## Testes de integração

Os testes em `tests/integration/` sobem um **PostgreSQL 16 real** via
`testcontainers` (Docker obrigatório), aplicam as migrations e provam o
isolamento multi-tenant da RLS. A suíte de segurança roda com `-m security`.

## Rodar localmente

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://127.0.0.1:8000/health`
- Domínio roteado pelo Traefik (dev): `http://api.sora.localhost:8000`

> As variáveis de ambiente são lidas de `.env` (raiz do monorepo) ou do ambiente.
> Veja o modelo em `.env.example` na raiz.
