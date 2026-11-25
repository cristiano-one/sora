# AGENTS.md — Regras Obrigatórias (IA e Contribuidores)

> Vale para **qualquer modelo de IA** que implemente código neste repositório.
> **Regra de ouro:** nenhuma entrega é "pronta" sem **testes verdes**, incluindo **segurança Zero-Leak**. Se não rodou os testes, **declare isso explicitamente** — nunca afirme que funciona sem evidência.

**Antes de codar:** leia a seção relevante de [`docs/plan/plano-implementacao-mvp-sora.md`](docs/plan/plano-implementacao-mvp-sora.md).

---

## 1. Testes Obrigatórios em Toda Implementação

- **Unitários:** regra de negócio nova/alterada.
- **Integração:** endpoint/fluxo alterado, com banco real.
- **Regressão:** todo bug corrigido ganha teste que falha antes e passa depois.
- **Migrations:** `alembic upgrade` **e** `downgrade` funcionais.
- **Qualidade:** lint, type-check e build sem erros.

```bash
# API
cd services/api && ruff check . && mypy app && pytest -q --cov=app --cov-fail-under=80

# Web
cd apps/web && pnpm lint && pnpm tsc --noEmit && pnpm test && pnpm build

# Mobile
cd apps/mobile && pnpm lint && pnpm tsc --noEmit && pnpm test
```

---

## 2. Segurança Zero-Leak (Obrigatório)

Toda mudança que toque em **dados, auth, agenda, financeiro, prontuários, IA, SQL, Redis ou exportação** precisa de testes provando:

### Isolamento Multi-Tenant (RLS)
- Tenant A **nunca** lê/escreve dados do tenant B — mesmo passando o `id` explicitamente.
- Resposta correta para acesso cruzado: **`404`** (não `403`, para não revelar existência).
- Query sem filtro de tenant (simulando bug de ORM) deve ser bloqueada pela **RLS do PostgreSQL**.
- Redis sempre prefixado com `tenant:{tenant_id}:`.
- Testar com `app.current_tenant_id` ausente/inválido: deve falhar ou retornar vazio.

### RBAC em 3 Níveis
| Cenário | Esperado |
| :--- | :--- |
| `COLLABORATOR` vê agenda/comissão de outro colaborador | `403`/`404` |
| `COLLABORATOR` ou `ADMIN` acessa DRE, extrato, dízimo, exportação em massa | `403` |
| `ADMIN` exclui empresa ou rebaixa `OWNER` | `403` |
| JWT revogado no Redis | `401` imediato |

### Contratos de API e Mascaramento
- `PublicResponse` **nunca** contém `score`, `is_blocked`, notas internas, telefone completo ou IDs sensíveis.
- `COLLABORATOR` recebe telefone mascarado (`(11) 9****-1234`).
- Erros não expõem stack trace, SQL ou nome de tabelas.

### Blindagem da SORA IA (Anti-Prompt Injection)
- Injeções de texto/áudio **não** alteram `tenant_id`, `user_id`, `role` nem o escopo do `RunContext`.
- Tools só retornam dados da sessão autenticada.
- Respostas de agenda nunca revelam nome/existência de agendamento de terceiros (`available`, `reason`, `suggested_slots` apenas).

### Prontuários, Storage e Auditoria
- Bucket privado; pre-signed URL com TTL de **60s** (expirada = erro).
- URL exige JWT válido + `tenant_id` + papel autorizado.
- Ação sensível gera `AuditLog` (`who`, `role`, `when`, `ip`, `action`, `resource_id`).
- Logs sem PII/tokens/senhas; uploads validam MIME real e tamanho.

---

## 3. Regras Críticas de Implementação

- **Dinheiro:** `Decimal` (backend) e centavos/string (front). **Nunca `float`.**
- **SQL:** sempre parametrizado. **Proibido f-string em SQL.**
- **Segredos:** nunca hardcoded, nunca versionados (`.env`, `acme.json`, keystores).
- **Locks/Idempotência:** lock Redis sempre com TTL e liberação em `finally`; webhooks e workers idempotentes.
- **Migrations:** sempre com políticas RLS incluídas.
- **Git:** commits semânticos (`feat:`, `fix:`, `test:`, `security:`, `docs:`).
- **Branches:** `feature/*` → PR para `develop` → PR `develop` → `main`. Nunca comite direto em `main`.
- Nunca leia arquivos .env, id_ed25519.pub,ou .pub ou qualquer outros arquivos de segredos.

---

## 4. Checklist Final (copie na resposta)

```markdown
### Evidências de Teste
- [ ] Lint / Type-check: <comando> → <resultado>
- [ ] Unitários: <comando> → X passed, Y failed
- [ ] Integração: <comando> → resultado
- [ ] Segurança Zero-Leak: <comando> → resultado
- [ ] Build / Migrations: resultado

### Riscos e Observações
- <o que não foi testado e por quê>
```
