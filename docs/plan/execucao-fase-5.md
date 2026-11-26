# Execução — Fase 5: SORA IA, Aniversários e Gateway

> Complementa o roadmap do [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md).

## Estado

- [x] **Passo 1 — SORA IA determinística + central (backend)** · branch `feat/api-ai`
  - webhook WhatsApp interno (`X-Internal-Token`) por tenant/telefone.
  - intents: saudação, agendamento com link mágico, preços, meus agendamentos,
    humano e fallback.
  - guardrail anti-prompt-injection: não altera tenant/escopo e não expõe
    score/bloqueio/dados de terceiros.
  - conversas/mensagens com RLS (`0013`), takeover humano, resposta e
    encerramento.
  - resumo diário e aniversariantes dos próximos 7 dias.
  - testes: token interno, link mágico, preços, injection, escopo do cliente,
    central, RBAC e cross-tenant.
- [ ] **Passo 2 — Central SORA IA no web**.
- [ ] **Passo 3 — Gateway real, envio WhatsApp e crédito de aniversário**.

## Regras de aceite

- Nenhuma mensagem do cliente altera `tenant_id`, `user_id`, `role` ou o
  `RunContext` usado nas consultas.
- Respostas de agenda nunca revelam nomes/existência de agendamentos de
  terceiros.
- Dados de score/bloqueio não aparecem em respostas públicas.
- A central é acessível apenas a `OWNER`/`ADMIN`.
