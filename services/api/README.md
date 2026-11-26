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

### Recuperação de senha e convite

- `POST /api/v1/auth/forgot-password` — resposta sempre genérica; quando o
  e-mail existe, grava token no Redis (`tenant:{id}:auth:password_reset:*`, TTL
  30 min) e envia link.
- `POST /api/v1/auth/reset-password` — define a nova senha, invalida o token e
  revoga todas as sessões do usuário.
- `POST /api/v1/users/invite` — cria colaborador/admin e envia convite
  (`tenant:{id}:auth:invite:*`, TTL 7 dias).
- `POST /api/v1/auth/accept-invite` — aceita o convite e define a senha inicial.
- `EMAIL_PROVIDER=mock` registra o e-mail no log; `smtp` usa `SMTP_HOST`,
  `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` e `EMAIL_FROM`.

## Tenants (RBAC + RLS)

- `POST /api/v1/tenants` — cadastro público de empresa + OWNER inicial
  (`tax_regime`: `MEI` ou `COMPLETE`). Slug único; conflito → `409`.
- `GET /api/v1/tenants/current` — dados do tenant do usuário autenticado
  (`OWNER`/`ADMIN`). `COLLABORATOR` recebe `403`.

O cadastro define `app.current_tenant_id` com o UUID gerado antes do INSERT,
atendendo à policy `WITH CHECK` da RLS. A dependência `get_tenant_session`
injeta o mesmo contexto nas requisições autenticadas.

### Portabilidade LGPD

`GET /api/v1/tenants/export` (exclusivo `OWNER`) devolve um JSON com dados da
clínica, usuários, clientes, catálogo, assinaturas, agenda, financeiro,
prontuários (notas decifradas), consentimentos e créditos. A exportação é
auditada e não inclui hash de senha nem URLs permanentes de anexos.

## Storage privado de anexos

- `STORAGE_PROVIDER=local` (padrão em dev) grava em `STORAGE_LOCAL_PATH`
  (`var/storage-private`) e assina URLs na própria API — não exige MinIO.
- `STORAGE_PROVIDER=s3` usa MinIO/S3/R2 com credenciais do `.env`.
- `PUT /api/v1/storage/upload/{token}` recebe o arquivo; o token é HMAC-SHA256,
  expira em `STORAGE_PRESIGNED_URL_TTL_SECONDS` (60s) e fixa chave, ação,
  `Content-Type` e tamanho máximo (10 MB).
- `GET /api/v1/storage/download/{token}` entrega o anexo com
  `Cache-Control: private, no-store`.
- Chaves fora da raiz do storage são rejeitadas (path traversal) e arquivos
  locais são gravados com permissão `0600`.
- `DELETE /api/v1/clients/{client_id}/records/{record_id}/attachments/{id}`
  (OWNER/ADMIN) remove o objeto e o metadado, com auditoria.

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

### Créditos de aniversário no prontuário

- `GET /api/v1/clients/{id}/credits` — saldo restante, validade e
  disponibilidade.
- `GET /api/v1/clients/{id}/credit-usages` — histórico de aplicações.
- `POST /api/v1/clients/{id}/credits/{credit_id}/use` — aplica valor parcial ou
  total, com validação de saldo/validade, vínculo opcional ao agendamento e
  auditoria. Exclusivo `OWNER`/`ADMIN`.

## Estoque de insumos

- `GET/POST /api/v1/inventory`, `PATCH/DELETE /api/v1/inventory/{id}`.
- `POST /api/v1/inventory/{id}/movements` — `IN`, `OUT` ou `ADJUSTMENT`, com
  bloqueio de saldo negativo.
- `GET /api/v1/inventory/{id}/movements` — histórico.
- Cada insumo traz `low_stock`, custo unitário e valor total. Exclusivo
  `OWNER`/`ADMIN`, com RLS e auditoria.

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
- `GET /my-commission` — comissão do próprio usuário autenticado (todos os
  papéis).
- `GET /sales` — valor bruto, custo, comissão e líquido por atendimento.
- `GET /export` — CSV com proteção contra injeção de fórmula.
- `GET/POST /payroll`, `PATCH/DELETE /payroll/{id}` — salários, adiantamentos,
  pró-labore e repasses. Verba paga gera automaticamente despesa `PAYROLL` no
  caixa/DRE; voltar para pendente remove o lançamento.
- `GET /tithe`, `POST/DELETE /tithe/deliveries` — provisão da DRE, entregas e
  pendências de dízimo/oferta (bloqueado quando a flag está desativada).

Dízimo/oferta são configurados em `/tenants/settings` (`enable_tithe_and_offering`,
`tithe_percentage`, `offering_amount`) e aparecem na DRE. O CSV não substitui o
gateway real; ele usa os lançamentos manuais para validar o fluxo.

## Cobranças Pix (gestão)

- `GET /api/v1/payments?status=` — lista cobranças com cliente e origem
  (`OWNER`/`ADMIN`).
- `POST /api/v1/payments/{id}/confirm` — confirma manualmente um Pix pendente,
  libera agendamento/assinatura e audita a ação. Idempotente para pagamentos já
  pagos.

## SORA IA (Fase 5)

- `POST /api/v1/ai/whatsapp/webhook` — **interno** (`X-Internal-Token`), recebe
  `{tenant_slug, phone, text}` do roteador de WhatsApp.
- Intents determinísticas: saudação, agendamento (gera link mágico), preços,
  meus agendamentos, humano e fallback.
- Guardrail: a mensagem nunca altera tenant/escopo; score, bloqueio e dados de
  terceiros não aparecem na resposta.
- `GET /api/v1/ai/conversations` e `GET /conversations/{id}` — central
  (`OWNER`/`ADMIN`).
- `POST /conversations/{id}/takeover`, `/messages` e `/close` — assume,
  responde e encerra o atendimento humano.
- `POST /conversations/{id}/approve` — aprova exceção sinalizada pela IA e
  devolve a conversa para `OPEN`.
- Conversas carregam `needs_approval`, `approval_note` e `last_intent`.
- Persona em `/tenants/settings`: `agent_tone`, `agent_welcome_message`,
  `agent_knowledge`, `agent_cancellation_policy`, `agent_address_info` e
  `agent_upsell`. Saudação, política, endereço e upsell são usados nas respostas
  determinísticas.
- `GET /api/v1/ai/summary?date=` — resumo diário, aprovações pendentes e
  aniversariantes (7 dias).
- `GET /api/v1/ai/birthday-credits?year=` e `POST /birthday-credits/run` —
  créditos idempotentes (1x/ano, 30 dias), valor em
  `tenant_settings.birthday_credit_amount`.
- Worker diário: `uv run python -m app.workers.birthday_credits` percorre todos
  os tenants ativos. Exemplo de cron:

  ```cron
  0 8 * * * cd /srv/sora/services/api && uv run python -m app.workers.birthday_credits
  ```
- Envio WhatsApp: `WHATSAPP_PROVIDER=mock` (padrão) ou `meta` com
  `WHATSAPP_META_TOKEN` + `WHATSAPP_META_PHONE_NUMBER_ID`.
- Pagamentos: `PaymentProviderPort` em `modules/payments/providers.py`; o mock
  gera BR Code local e o gateway real deve implementar a porta.

O webhook é mock: o envio real pelo WhatsApp e o LLM (PydanticAI) entram na
integração final. O motor atual é determinístico para validar o fluxo com custo
zero de tokens.

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
