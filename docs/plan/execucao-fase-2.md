# Execução — Fase 2: Motor de Agenda, Link Mágico, Assinaturas e Sinal

> Complementa o roadmap do [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md)
> e a [`execucao-fase-1.md`](execucao-fase-1.md) (concluída).

## Estado

- [x] **Passo 1 — Motor de agenda** · branch `feat/api-agenda`
  - models `Appointment`/`AppointmentStatus`, migration `0007`, RLS `FORCE`.
  - dupla trava anti-conflito: **Redis lock** (TTL 10s) + **`EXCLUDE USING gist`**
    (`tenant_id`, `collaborator_id`, `tstzrange(starts_at, ends_at, '[)')`).
  - intervalo ocupado = `duration_minutes + buffer_minutes`.
  - `COLLABORATOR` opera apenas a própria agenda; `OWNER`/`ADMIN` veem todas.
  - disponibilidade retorna somente horários livres (sem nomes/terceiros).
  - endpoints `POST/GET/PATCH /appointments` e `GET /agenda/availability`.
  - testes: conflito, slot adjacente, cancelamento liberando slot, buffer,
    RBAC, cross-tenant, lock Redis e constraint no banco.
- [x] **Passo 2 — Link mágico + agendamento público** · branch
  `feat/api-public-booking`
  - `POST /api/v1/public/{slug}/magic-link` (interno, `X-Internal-Token`)
    grava `tenant:{tenant_id}:public:magic:{token}` no Redis com TTL de 20 min.
  - `GET /api/v1/public/{slug}/context` retorna clínica, serviços, profissionais
    e apenas o nome do próprio cliente do token (sem score/bloqueio/telefone).
  - `GET /api/v1/public/{slug}/availability` reutiliza o motor da agenda e não
    expõe agendamentos de terceiros; cliente bloqueado recebe lista vazia.
  - `POST /api/v1/public/{slug}/appointments` reutiliza lock Redis + `EXCLUDE`
    e cria cliente novo quando o telefone ainda não existe.
  - conflito e cliente bloqueado retornam o mesmo `409` genérico (“fale com a
    recepção”), sem revelar o motivo.
  - testes: header interno, token inválido/cross-tenant, isolamento de campos,
    disponibilidade, criação, conflito, bloqueio neutro, sinal e TTL no Redis.
  - web: página pública `/public/[slug]?t=` com serviços, profissionais,
    horários livres, nome do cliente e confirmação (mobile-first).
- [x] **Passo 3 — Assinaturas/cotas + score no agendamento + sinal Pix (mock)**.
  - [x] **3.1 Assinaturas de clientes + cotas** · branch `feat/api-subscriptions`
    - models `ClientSubscription`/`SubscriptionUsage`, migration `0008`, RLS `FORCE`.
    - contratação pelo painel e pelo link público (`POST /public/{slug}/subscriptions`).
    - contexto público com planos ativos, assinatura do cliente e cotas usadas/restantes.
    - listagem/cancelamento interno restrito a `OWNER`/`ADMIN`.
    - testes: contratação, cotas, conflito de plano ativo, cross-tenant e RBAC.
  - [x] 3.2 Consumo de cotas na agenda + tag `ASSINANTE` · branch
    `feat/agenda-subscription-quota`
    - `Appointment.subscription_id` (migration `0009`), cota consumida na
      criação e liberada em `CANCELLED`/`EXPIRED`.
    - cota disponível dispensa sinal do serviço; sem cota/intervalo/dia
      permitido o fluxo cai para o agendamento avulso normal.
    - lock Redis por assinatura+serviço serializa o consumo concorrente.
    - resposta pública sinaliza `used_subscription`; agenda interna recebe
      `subscription_id` para a tag `ASSINANTE`.
  - [x] 3.3 Score mínimo + sinal e expiração de reserva · branch
    `feat/deposit-score-settings`
    - `tenant_settings` (migration `0010`, RLS) com limite de score, valor do
      sinal, cor primária e nome do agente.
    - `GET/PATCH /api/v1/tenants/settings` exclusivo de `OWNER`/`ADMIN`.
    - score abaixo do limite exige sinal mesmo sem regra do serviço; o motivo
      nunca é exposto ao cliente.
    - `PENDING_DEPOSIT` expira em 10 min e libera horário/cota na próxima
      consulta de disponibilidade ou agendamento.
  - [x] 3.4 Pix mock (copia-e-cola, QR e confirmação) · branch `feat/pix-mock`
    - `PaymentIntent` (migration `0011`, RLS) com BR Code + CRC16 e QR PNG
      gerado localmente (`segno`), sem serviço externo.
    - sinal cria cobrança automaticamente; contratação de plano fica
      `PENDING_PAYMENT` até o pagamento.
    - `GET /public/{slug}/payments/{id}` e `POST .../mock-confirm`
      (somente `PAYMENT_PROVIDER=mock`), com posse pelo token e idempotência.
    - pagamento aprovado confirma o agendamento/ativa a assinatura; expirado
      libera horário e encerra a assinatura pendente.
  - [x] 3.5 Web público: planos, cotas e sinal Pix · branch
    `feat/web-public-plans-pix`
    - vitrine de planos com preço/ciclo/cotas e assinatura pelo link.
    - tela de pagamento com QR, copia-e-cola, expiração e confirmação mock.
    - cotas restantes do plano e tag `Assinante` na agenda interna.
    - tema primário do tenant aplicado ao link público.
- [x] **Passo 4 — Tela de agenda no web preview** (consumindo os endpoints acima).

## Regras de aceite

- Nenhum agendamento sobreposto para o mesmo profissional, mesmo sob concorrência.
- Brechas menores que `duration + buffer` são rejeitadas.
- `COLLABORATOR` nunca lê/escreve agenda de outro profissional (403/404).
- Respostas de disponibilidade não expõem clientes/agendamentos de terceiros.
- Cancelar/expirar libera o slot para um novo agendamento.
