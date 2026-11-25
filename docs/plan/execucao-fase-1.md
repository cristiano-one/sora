# Execução — Fase 1: Fundação Zero-Leak, RBAC, Banco Multi-Tenant e Cadastros Base

> **Documento de execução (backlog granular).** Complementa — não substitui — o
> [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md), que segue
> como **fonte de verdade da arquitetura**. Aqui a Fase 1 é quebrada em passos
> ordenados, cada um mapeado para um PR pequeno em `develop` e para os testes
> Zero-Leak obrigatórios do [`AGENTS.md`](../../AGENTS.md).

---

## Estado Atual (antes de começar)

| Item | Status | Evidência |
| :--- | :---: | :--- |
| Padronização do monorepo (`.gitignore`, `.editorconfig`, `.env.example`, Makefile, pre-commit) | ✅ Concluído | commit `646eeec` |
| Infra local (`docker-compose.dev.yml`): Traefik + Postgres 16 + Redis 7 + MinIO | ✅ Concluído | commit `c0f78de` |
| Init RLS do PostgreSQL (`01-init-rls-roles.sh`: role `sora_app` `NOBYPASSRLS`) | ✅ Concluído | commit `c0f78de` |
| Traefik v3 (roteamento `api.sora.localhost` / wildcard `*.sora.localhost`) | ✅ Concluído | `infra/traefik/*` |
| CI/CD (pipeline + PR template + dependabot) | ✅ Concluído | commit `1e5a593` |
| **Backend `services/api`** | ✅ **Passos 1–3 concluídos** | skeleton, banco/RLS, auth JWT+Redis |
| **`apps/web` (preview)** | 🟡 **Slice de login + dashboard** | antecipação da Fase 3 |
| **`apps/mobile`** | ⏭️ Fora desta fase (Fase 3 do roadmap) | — |

> **Conclusão:** a "fundação" de infraestrutura já está entregue. A Fase 1, a
> partir daqui, concentra-se no **backend FastAPI** (`services/api`).

---

## Convenções

- **Branch:** cada passo abaixo vira uma branch `feat/*` a partir de `develop`, e
  um PR pequeno de volta para `develop`.
- **"Pronto" (Definition of Done):** lint + type-check + testes verdes **com
  evidência**, incluindo testes Zero-Leak quando o passo tocar em dados/auth/RLS.
- **Dinheiro:** `Decimal` no backend (nunca `float`).
- **Segurança:** SQL parametrizado, segredos fora do código, auditoria em ações
  sensíveis.

---

## Passos Ordenados

### Passo 1 — Skeleton do FastAPI (`services/api`) · branch `feat/api-skeleton` · ✅ Concluído
- **Objetivo:** subir a estrutura mínima da API com configuração centralizada,
  logging sem PII e health check.
- **Entregáveis:**
  - `pyproject.toml` (uv) com a stack declarada (FastAPI, SQLAlchemy async,
    asyncpg, Alembic, Redis, PyJWT, Pydantic v2) + grupos `dev`/`test`.
  - `app/main.py` (factory `create_app`), `app/core/config.py` (pydantic-settings),
    `app/core/logging.py`, `app/api/routes/health.py`.
  - Testes do health check e das configurações.
- **Critério de aceite:**
  - `ruff check .` limpo, `mypy app` limpo, `pytest --cov=app --cov-fail-under=80` verde.
  - `GET /health` → `200 {"status": "ok"}`.
- **Zero-Leak:** logging configurado sem PII; config não loga credenciais.

### Passo 2 — Banco multi-tenant base + Alembic + RLS · branch `feat/api-db-rls` · ✅ Concluído
- **Objetivo:** modelo `tenants` + `users` com `tenant_id`, policies RLS e
  migrations idempotentes (`up` **e** `downgrade`).
- **Entregáveis:** `app/db/` (engine/session), `app/models/`, `alembic.ini`,
  `migrations/` com policies `ENABLE/FORCE ROW LEVEL SECURITY`.
- **Critério de aceite:** `alembic upgrade head` e `downgrade base` funcionais;
  teste de integração prova que query sem filtro de tenant é bloqueada pela RLS.

### Passo 3 — Auth JWT + Refresh Token no Redis · branch `feat/api-auth` · ✅ Concluído
- **Objetivo:** access token (15 min) + refresh rotativo no Redis + revogação
  instantânea.
- **Critério de aceite:** login gera par; token revogado → `401` imediato;
  chave Redis prefixada com `tenant:{tenant_id}:`.

### Passo 4 — RBAC 3 níveis + middleware RLS
- **Objetivo:** `OWNER` / `ADMIN` / `COLLABORATOR`, injeção de
  `SET LOCAL app.current_tenant_id` por requisição, e dependência de escopo.
- **Critério de aceite:** `COLLABORATOR` acessa apenas o próprio escopo; ausência
  de `current_tenant_id` falha ou retorna vazio; acesso cruzado → `404`.

### Passo 5 — Cadastro de Empresa + seed do OWNER
- **Objetivo:** empresa (MEI vs Completo), usuário OWNER inicial e bootstrap do
  tenant com políticas RLS aplicadas.

### Passo 6 — Colaboradores + regras de comissão
- **Objetivo:** CRUD de colaboradores com percentuais/regras de comissão
  (base `Decimal`), restrito a `ADMIN`/`OWNER`.

### Passo 7 — Serviços, Pacotes e Planos de Assinatura
- **Objetivo:** catálogo com `duration_minutes`, `buffer_minutes`, `requires_deposit`,
  custo de insumo, valor médio (toggle público) e planos recorrentes.

### Passo 8 — Clientes + Score + Prontuário multimídia
- **Objetivo:** clientes com score confidencial, prontuário em storage privado com
  pre-signed URL (TTL 60s), consentimento LGPD e `AuditLog`.
- **Critério de aceite:** URL exige JWT + `tenant_id` + papel; expirada → erro;
  `PublicResponse` nunca expõe `score`/`is_blocked`.

### Passo 9 — Suíte Zero-Leak consolidada
- **Objetivo:** suite `pytest -m security` cobrindo RLS (tenant A ≠ B), RBAC 3
  níveis, mascaramento de telefone e contratos de resposta por nível de acesso.

---

> Após a Fase 1, seguir para **Fase 2** (Motor de Agenda, Assinaturas, Score e
> Link Mágico) e **Fase 3** (`apps/web` e `apps/mobile`), conforme o roadmap.
