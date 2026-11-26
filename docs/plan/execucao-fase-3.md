# Execução — Fase 3: Front-end Web, Design System e Painel

> Complementa o roadmap do [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md)
> e a [`execucao-fase-2.md`](execucao-fase-2.md) (concluída).

## Estado

- [x] **Passo 1 — Design system + AppShell** · branch `feat/web-admin-shell`
  - shell com sidebar por seções, perfil/cargo e logout.
  - tema primário do tenant aplicado no painel e no link público.
  - páginas passam a usar o mesmo container `page`/`panel`/`data-table`.
- [x] **Passo 2 — Cadastros do painel**
  - `/clientes`: busca, cadastro, score e bloqueio/desbloqueio.
  - `/catalogo`: serviços com duração, buffer, preço, custo e sinal.
  - `/equipe`: usuários, papéis, status e comissões.
- [x] **Passo 3 — Assinaturas e configurações**
  - `/assinaturas`: planos, cotas, contratação manual e cancelamento.
  - `/configuracoes`: score mínimo, valor do sinal, cor primária e agente.
  - agenda com tag `Assinante` e tema dinâmico.
- [x] **Passo 4 — `apps/mobile` (Expo iOS/Android)** · branch `feat/mobile-core`
  - login JWT + refresh com SecureStore.
  - abas Agenda, Clientes, Equipe (gestor/admin) e Perfil.
  - agenda do dia com navegação, confirmação, conclusão e cancelamento.
  - clientes com busca, score pós-atendimento e telefone mascarado.
  - comissão do próprio usuário e regra de comissão da equipe.
  - tema primário do tenant aplicado ao app para gestores.
  - validação: lint, `tsc --noEmit`, 5 testes e bundle Android via
    `expo export`.
- [ ] **Passo 5 — Financeiro (Fase 4) e SORA IA (Fase 5)**.
  - próximos: prontuário com câmera, caixa/DRE/comissões e atendente IA.

## Regras de aceite

- `COLLABORATOR` não acessa equipe, assinaturas, configurações nem catálogo de gestão.
- Telefone de cliente continua mascarado para `COLLABORATOR`.
- Tema e dados da clínica nunca vazam entre tenants.
- Toda tela usa a API real (sem dados mockados no front).
