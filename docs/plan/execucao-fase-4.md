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
- [x] **Passo 2 — Dashboard financeiro no web** · branch `feat/web-finance`
  - menu Financeiro com submenus: Fluxo de caixa, DRE, Lançamentos,
    Contas e caixa, Comissões e Vendas.
  - cada seção tem rota própria (`/financeiro/*`) e não mistura formulários
    com relatórios.
  - criação de conta, criação/baixa de lançamentos e exportação CSV.
  - dízimo/oferta configuráveis em `/configuracoes` e refletidos na DRE.
  - link de financeiro apenas para `OWNER` no menu e no dashboard.
- [x] **Passo 3 — Fechamento da fase** · seed de demonstração
  - `Caixa Demo` com saldo inicial, receitas de serviço/assinatura e despesas.
  - atendimento concluído gerando comissão e valor líquido.
  - smoke: `/financeiro` 200, caixa/DRE/comissões/exportação 200.
  - dashboard e menu exibem Financeiro apenas para `OWNER`.

## Regras de aceite

- `ADMIN` e `COLLABORATOR` recebem `403` em contas, DRE, extrato, comissões da
  equipe e exportação.
- Valores sempre em `Decimal`/`Numeric`.
- CSV não executa fórmulas em planilhas.
- Nenhum dado financeiro atravessa tenants (RLS + testes).
- DRE não mistura caixa com competência.
