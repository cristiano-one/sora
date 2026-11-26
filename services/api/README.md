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

## Autenticação (JWT + Redis)

- `POST /api/v1/auth/login` — `{tenant_slug, email, password}` → par de tokens.
- `POST /api/v1/auth/refresh` — rotaciona o refresh token (detecção de reuso).
- `POST /api/v1/auth/logout` — revoga o access (denylist) e o refresh token.
- `GET /api/v1/auth/me` — dados do usuário autenticado.

Access token: **15 min**. Refresh token: **7 dias**, rotativo no Redis com
chaves sempre prefixadas por `tenant:{tenant_id}:auth:*`. Revogação em massa
(desligamento de usuário) via `revoked_at` em milissegundos.

## Tenants (RBAC + RLS)

- `POST /api/v1/tenants` — cadastro público de empresa + OWNER inicial
  (`tax_regime`: `MEI` ou `COMPLETE`). Slug único; conflito → `409`.
- `GET /api/v1/tenants/current` — dados do tenant do usuário autenticado
  (`OWNER`/`ADMIN`). `COLLABORATOR` recebe `403`.

O cadastro define `app.current_tenant_id` com o UUID gerado antes do INSERT,
atendendo à policy `WITH CHECK` da RLS. A dependência `get_tenant_session`
injeta o mesmo contexto nas requisições autenticadas.

## Usuários / Colaboradores

- `GET /api/v1/users` — lista usuários do tenant (`OWNER`/`ADMIN`).
- `POST /api/v1/users` — cadastra colaborador/admin (`OWNER` cria
  `ADMIN`/`COLLABORATOR`; `ADMIN` cria apenas `COLLABORATOR`).
- `PATCH /api/v1/users/{id}` — atualiza nome, status, papel e comissão;
  `is_active=false` revoga as sessões no Redis.
- `GET /api/v1/users/me/commission` — comissão do próprio usuário autenticado.

Comissões usam `Decimal`/`Numeric` (`commission_percentage`, `commission_fixed`,
`commission_base`), nunca `float`.

## Catálogo (serviços, pacotes e planos)

- `GET/POST /api/v1/services` e `PATCH /api/v1/services/{id}`.
- `GET/POST /api/v1/packages` e `PATCH /api/v1/packages/{id}`.
- `GET/POST /api/v1/subscription-plans` e `PATCH /api/v1/subscription-plans/{id}`.

Leitura liberada para `OWNER`/`ADMIN`/`COLLABORATOR`; escrita apenas
`OWNER`/`ADMIN`. Preços, custos e sinal usam `Decimal`/`Numeric`. Planos têm
cotas por ciclo, intervalo mínimo e dias da semana permitidos.

## Clientes, Score e Prontuário

- `GET/POST /api/v1/clients` e `GET/PATCH /api/v1/clients/{id}` — telefone
  mascarado para `COLLABORATOR`.
- `POST /api/v1/clients/{id}/score-events` — avaliação pós-atendimento.
- `POST /api/v1/clients/{id}/consents` — aceite LGPD.
- `POST/GET /api/v1/clients/{id}/records` — evolução clínica com notas cifradas.
- `POST .../attachments/presign` e `GET .../attachments/{id}/url` — URLs S3
  pré-assinadas com TTL de **60s**.

Ações sensíveis gravam `AuditLog` append-only (UPDATE/DELETE revogados para
`sora_app`). O score e o bloqueio são confidenciais da clínica.

## Agenda (Fase 2)

- `POST /api/v1/appointments` — cria com **lock Redis** + **`EXCLUDE USING gist`**
  (anti-`double booking`).
- `GET /api/v1/appointments?from_date=&to_date=&collaborator_id=` —
  `COLLABORATOR` vê apenas a própria agenda.
- `GET/PATCH /api/v1/appointments/{id}` — consulta, reagenda, cancela e muda status.
- `GET /api/v1/agenda/availability?service_id=&date=&collaborator_id=` —
  horários livres sem revelar agendamentos de terceiros.

O intervalo ocupado inclui `duration_minutes + buffer_minutes`. Cancelar/expirar
libera o slot.

## Link mágico e agendamento público (Fase 2)

Fluxo sem login para o cliente final (link enviado pelo WhatsApp):

- `POST /api/v1/public/{slug}/magic-link` — **interno**; exige
  `X-Internal-Token` (`INTERNAL_API_TOKEN`). Gera token aleatório no Redis em
  `tenant:{tenant_id}:public:magic:{token}` com TTL de **20 min** e devolve
  `{PUBLIC_BOOKING_BASE_URL}/public/{slug}?t={token}`.
- `GET /api/v1/public/{slug}/context?t=` — nome da clínica, serviços ativos
  (preço só quando `show_average_price`) e profissionais ativos. Inclui apenas
  o nome do cliente dono do token; nunca score, bloqueio, telefone ou e-mail.
- `GET /api/v1/public/{slug}/availability?t=&service_id=&collaborator_id=&date=`
  — horários livres; não revela agendamentos de terceiros.
- `POST /api/v1/public/{slug}/appointments?t=` — cria o agendamento com as
  mesmas travas do fluxo interno e cria o cliente quando o telefone é novo.

Cliente bloqueado recebe disponibilidade vazia e o mesmo `409` genérico de
conflito (“Não foi possível concluir o agendamento. Fale com a recepção.”),
sem revelar o motivo. Serviços com `requires_deposit=true` entram como
`PENDING_DEPOSIT` (o Pix real fica para o Passo 3).

## Assinaturas de clientes e cotas (Fase 2)

- `GET /api/v1/subscriptions` — lista assinaturas (`OWNER`/`ADMIN`).
- `GET /api/v1/clients/{id}/subscriptions` — assinaturas do cliente.
- `POST /api/v1/clients/{id}/subscriptions` — contratação manual de plano.
- `POST /api/v1/subscriptions/{id}/cancel` — cancela a assinatura.
- `POST /api/v1/public/{slug}/subscriptions?t=` — contratação pelo link mágico.

`ClientSubscription` guarda o ciclo atual e `SubscriptionUsage` registra cada
cota consumida. O contexto público expõe planos ativos, a assinatura do próprio
cliente e suas cotas (`used`/`remaining`), sem dados de terceiros.

No agendamento, uma cota disponível consome `SubscriptionUsage`, dispensa o
sinal do serviço e grava `Appointment.subscription_id` (tag `ASSINANTE`).
Cancelar/expirar devolve a cota. Sem cota, intervalo mínimo ou dia permitido, o
agendamento segue o fluxo avulso normal. Cada cliente pode ter **uma assinatura
ativa** por vez.

## Configurações de sinal e score (Fase 2)

- `GET/PATCH /api/v1/tenants/settings` (`OWNER`/`ADMIN`).
- `deposit_score_threshold` + `deposit_amount_low_score`: score abaixo do limite
  passa a exigir sinal, sem revelar o motivo ao cliente.
- `theme_primary_color` e `agent_name` preparam o tema dinâmico da Fase 3.
- `PENDING_DEPOSIT` carrega `deposit_expires_at` (10 min). A expiração é aplicada
  de forma preguiçosa na disponibilidade/agendamento, liberando horário e cota.

## Pagamentos Pix (mock)

- `PaymentIntent` guarda valor, status, payload Pix e expiração.
- O BR Code é gerado localmente (CRC16/CCITT) e o QR PNG vira data URI; nenhum
  payload é enviado a serviço externo.
- `GET /api/v1/public/{slug}/payments/{id}?t=` — status do próprio pagamento.
- `POST /api/v1/public/{slug}/payments/{id}/mock-confirm?t=` — confirma no
  provider mock (bloqueado quando `PAYMENT_PROVIDER != mock`).
- Sinal pago → agendamento `CONFIRMED`. Assinatura paga → `ACTIVE` e ciclo
  reiniciado. Pagamento expirado → reserva/assinatura `EXPIRED`.
- A confirmação é idempotente e só aceita o token do cliente dono da cobrança.

## Financeiro (Fase 4)

Tudo em `/api/v1/finance/*` é exclusivo do `OWNER`.

- `GET/POST /accounts` e `PATCH /accounts/{id}` — caixas e contas bancárias.
- `GET/POST /entries` e `PATCH /entries/{id}` — lançamentos com competência,
  caixa, categoria e status `PENDING`/`PAID`.
- `GET /cash-flow?from_date=&to_date=` — abertura, entradas, saídas e saldo.
- `GET /accounts/balances` — saldo atual por conta/caixa.
- `GET /dre?from_date=&to_date=` — receita, deduções, custos, despesas e lucro.
- `GET /commissions` — comissões apuradas por atendimentos `COMPLETED`.
- `GET /sales` — valor bruto, custo, comissão e líquido por atendimento.
- `GET /export` — CSV com proteção contra injeção de fórmula.

Dízimo/oferta são configurados em `/tenants/settings` (`enable_tithe_and_offering`,
`tithe_percentage`, `offering_amount`) e aparecem na DRE. O CSV não substitui o
gateway real; ele usa os lançamentos manuais para validar o fluxo.

## Testes de integração

Os testes em `tests/integration/` sobem um **PostgreSQL 16** e um **Redis 7**
reais via `testcontainers` (Docker obrigatório), aplicam as migrations e provam
isolamento multi-tenant (RLS), autonomia de tokens e revogação. A suíte de
segurança roda com `-m security`.

## Rodar localmente

```bash
uv run uvicorn app.main:app --reload --port 8000
```

- Health check: `GET http://127.0.0.1:8000/health`
- Domínio roteado pelo Traefik (dev): `http://api.sora.localhost:8000`

> As variáveis de ambiente são lidas de `.env` (raiz do monorepo) ou do ambiente.
> Veja o modelo em `.env.example` na raiz.
