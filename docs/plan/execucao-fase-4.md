# Execução — Fase 4: Financeiro Desacoplado

> Complementa o roadmap do [`plano-implementacao-mvp-sora.md`](plano-implementacao-mvp-sora.md).

## Estado

- [x] **Passo 1 — Backend financeiro** · branch `feat/api-finance`
  - `FinancialAccount` (caixa/banco) e `FinancialEntry` (competência + caixa)
    com migration `0012` e RLS `FORCE`.
  - categorias de receita/despesa e status `PENDING`/`PAID`.
  - fluxo de caixa realizado, saldo por conta, DRE por competência,
    comissões apuradas e valor líquido por atendimento.
  - dízimo/oferta opcionais em `tenant_settings`.
  - exportação CSV com proteção contra injeção de fórmula.
  - tudo restrito a `OWNER`; comissão própria continua em
    `/users/me/commission`.
- [ ] **Passo 2 — Dashboard financeiro no web**.
- [ ] **Passo 3 — Fechamento da fase (documentação/seed de demonstração)**.

## Regras de aceite

- `ADMIN` e `COLLABORATOR` recebem `403` em contas, DRE, extrato, comissões da
  equipe e exportação.
- Valores sempre em `Decimal`/`Numeric`.
- CSV não executa fórmulas em planilhas.
- Nenhum dado financeiro atravessa tenants (RLS + testes).
- DRE não mistura caixa com competência.
