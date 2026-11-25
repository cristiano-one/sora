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
- [ ] **Passo 2 — Link mágico + agendamento público** (WhatsApp → token Redis
  TTL 20 min → link leve no `apps/web`).
- [ ] **Passo 3 — Assinaturas/cotas + score no agendamento + sinal Pix (mock)**.
- [ ] **Passo 4 — Tela de agenda no web preview** (consumindo os endpoints acima).

## Regras de aceite

- Nenhum agendamento sobreposto para o mesmo profissional, mesmo sob concorrência.
- Brechas menores que `duration + buffer` são rejeitadas.
- `COLLABORATOR` nunca lê/escreve agenda de outro profissional (403/404).
- Respostas de disponibilidade não expõem clientes/agendamentos de terceiros.
- Cancelar/expirar libera o slot para um novo agendamento.
