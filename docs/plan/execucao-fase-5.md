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
- [x] **Passo 2 — Central SORA IA no web** · branch `feat/web-ai-center`
  - `/sora-ia` com resumo diário, lista de conversas e histórico em bolhas.
  - assumir conversa, responder como humano e encerrar atendimento.
  - aniversariantes dos próximos 7 dias e link para configurar o agente.
  - menu/dashboard com a central para `OWNER`/`ADMIN`.
- [x] **Passo 2.1 — Persona e aprovação humana**
  - tom, saudação, conhecimento, política de cancelamento, endereço e upsell.
  - conversas com `needs_approval`, nota contextual e filtro de aprovações.
  - aprovação em 1 clique devolve a conversa para a SORA IA.
  - tags de intenção no feed e nas mensagens.
- [ ] **Passo 3 — Gateway real, envio WhatsApp e crédito de aniversário**.
  - [x] **3.1 Adapters e crédito de aniversário** · branch `feat/integrations-birthday`
    - envio WhatsApp com port `mock`/Meta Cloud API (`WHATSAPP_PROVIDER`).
    - `PaymentProviderPort` com mock e erro explícito para gateway não plugado.
    - `client_credits` + `birthday_credit_amount` (migration `0014`, RLS).
    - geração idempotente 1x/ano, validade 30 dias, mensagem via WhatsApp mock.
    - worker `python -m app.workers.birthday_credits` percorre todos os
      tenants ativos e pode rodar via cron/scheduler.
    - botão de geração na central e campo nas configurações.
    - `eas.json` com perfis preview/production.
  - [x] **3.1.1 Créditos aplicáveis no prontuário**
    - histórico `client_credit_usages` com RLS.
    - aplicação parcial/total com saldo, validade e vínculo ao cliente.
    - painel de créditos no prontuário para `OWNER`/`ADMIN`.
  - [ ] **3.2 Credenciais reais**.
    - Meta WhatsApp: token + phone_number_id.
    - Gateway: escolher Asaas/Mercado Pago/Stripe/Efí e plugar `PaymentProviderPort`.
    - EAS: login + credenciais Apple/Google e build em aparelho.

## Próximas fases (pós-MVP)

O backlog filtrado da referência Mangomint e das exigências brasileiras está em
[`backlog-pos-mvp.md`](backlog-pos-mvp.md): comanda rápida, automações/CRM,
check-in digital, pagamentos locais, NFS-e, vínculo parceiro/MEI e recepção por
voz.

## Regras de aceite

- Nenhuma mensagem do cliente altera `tenant_id`, `user_id`, `role` ou o
  `RunContext` usado nas consultas.
- Respostas de agenda nunca revelam nomes/existência de agendamentos de
  terceiros.
- Dados de score/bloqueio não aparecem em respostas públicas.
- A central é acessível apenas a `OWNER`/`ADMIN`.
