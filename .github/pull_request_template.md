## 📌 Descrição

<!-- O que este PR entrega? Qual problema resolve? -->

## 🔗 Issue / Contexto

<!-- Link da issue ou referência ao plano -->

## 🧪 Evidências de Teste (obrigatório)

| Verificação | Comando | Resultado |
| :--- | :--- | :--- |
| Lint | `ruff check .` / `pnpm lint` | |
| Type-check | `mypy app` / `pnpm tsc --noEmit` | |
| Unitários | `pytest -q` / `pnpm test` | |
| Integração | | |
| Segurança Zero-Leak | `pytest -q -m security` | |
| Build | `pnpm build` | |

## 🔒 Checklist de Segurança Zero-Leak

- [ ] Testei isolamento multi-tenant (tenant A não acessa tenant B).
- [ ] Testei RBAC (`COLLABORATOR` / `ADMIN` / `OWNER`) nos recursos alterados.
- [ ] Respostas públicas não expõem score, bloqueio, telefone completo ou dados internos.
- [ ] Testei anti-prompt-injection (se alterou IA/agentes).
- [ ] Pre-signed URLs com TTL de 60s (se alterou storage).
- [ ] Ações sensíveis geram AuditLog.
- [ ] Nenhum segredo/PII em código, logs ou fixtures.

## ✅ Checklist de Qualidade

- [ ] Teste de regressão adicionado (se for correção de bug).
- [ ] Migration com `upgrade` e `downgrade` funcionais (se aplicável).
- [ ] Sem `any` injustificado / sem `float` para dinheiro.
- [ ] Documentação atualizada (se mudou comportamento público).

## 📎 Observações

<!-- Algo que não foi possível testar? Dependências externas? -->
