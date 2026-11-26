"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createFinancialAccount,
  createFinancialEntry,
  getAccountBalances,
  getCashFlow,
  getCommissions,
  getDre,
  getFinanceCsv,
  getFinancialAccounts,
  getFinancialEntries,
  getMe,
  getSales,
  updateFinancialEntry,
  type AccountBalance,
  type CashFlow,
  type CommissionSummary,
  type Dre,
  type FinancialAccount,
  type FinancialCategory,
  type FinancialEntry,
  type FinancialEntryType,
  type Me,
  type SalesSummary,
} from "@/lib/api";
import { formatDateLabel, formatTime, todayInTenant } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

const CATEGORY_LABEL: Record<FinancialCategory, string> = {
  SERVICE: "Serviço",
  PACKAGE: "Pacote",
  SUBSCRIPTION: "Assinatura",
  PRODUCT: "Produto",
  OTHER_INCOME: "Outra receita",
  TAX: "Imposto",
  CARD_FEE: "Taxa de cartão",
  SUPPLIES: "Insumos",
  COMMISSION: "Comissão",
  RENT: "Aluguel",
  UTILITY: "Contas fixas",
  MARKETING: "Marketing",
  PAYROLL: "Folha/pró-labore",
  OTHER_EXPENSE: "Outra despesa",
};

const INCOME_CATEGORIES: FinancialCategory[] = [
  "SERVICE",
  "PACKAGE",
  "SUBSCRIPTION",
  "PRODUCT",
  "OTHER_INCOME",
];
const EXPENSE_CATEGORIES = (
  Object.keys(CATEGORY_LABEL) as FinancialCategory[]
).filter((category) => !INCOME_CATEGORIES.includes(category));

export type FinanceSection =
  | "cashflow"
  | "dre"
  | "entries"
  | "accounts"
  | "commissions"
  | "sales";

const SECTION_META: Record<
  FinanceSection,
  { title: string; description: string }
> = {
  cashflow: {
    title: "Fluxo de caixa",
    description:
      "Abertura, entradas, saídas e saldo realizado no período.",
  },
  dre: {
    title: "DRE simplificada",
    description:
      "Receita, deduções, custos, despesas e lucro por competência.",
  },
  entries: {
    title: "Lançamentos",
    description:
      "Contas a pagar/receber, baixa de títulos e classificação por categoria.",
  },
  accounts: {
    title: "Contas e caixa",
    description:
      "Cadastro de caixas/contas bancárias e saldo atual de cada uma.",
  },
  commissions: {
    title: "Comissões",
    description:
      "Comissões apuradas por profissional nos atendimentos concluídos.",
  },
  sales: {
    title: "Vendas",
    description:
      "Valor bruto, custo, comissão e líquido por atendimento concluído.",
  },
};

export function FinanceDashboard({ section }: { section: FinanceSection }) {
  const meta = SECTION_META[section];
  const today = todayInTenant();
  const [me, setMe] = useState<Me | null>(null);
  const [fromDate, setFromDate] = useState(`${today.slice(0, 7)}-01`);
  const [toDate, setToDate] = useState(today);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [balances, setBalances] = useState<AccountBalance[]>([]);
  const [entries, setEntries] = useState<FinancialEntry[]>([]);
  const [cash, setCash] = useState<CashFlow | null>(null);
  const [dre, setDre] = useState<Dre | null>(null);
  const [commissions, setCommissions] = useState<CommissionSummary | null>(
    null,
  );
  const [sales, setSales] = useState<SalesSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [accountName, setAccountName] = useState("Caixa principal");
  const [accountType, setAccountType] = useState<"CASH" | "BANK">("CASH");
  const [initialBalance, setInitialBalance] = useState("0.00");

  const [entryAccount, setEntryAccount] = useState("");
  const [entryType, setEntryType] = useState<FinancialEntryType>("INCOME");
  const [entryCategory, setEntryCategory] =
    useState<FinancialCategory>("SERVICE");
  const [entryDescription, setEntryDescription] = useState("");
  const [entryAmount, setEntryAmount] = useState("100.00");
  const [entryCompetence, setEntryCompetence] = useState(today);
  const [entryStatus, setEntryStatus] = useState<"PENDING" | "PAID">("PAID");
  const [entryCashDate, setEntryCashDate] = useState(today);

  const [commissionCollaborator, setCommissionCollaborator] = useState("");
  const [commissionDescription, setCommissionDescription] = useState("");
  const [commissionAmount, setCommissionAmount] = useState("0.00");
  const [commissionCompetence, setCommissionCompetence] = useState(today);
  const [commissionStatus, setCommissionStatus] = useState<"PENDING" | "PAID">(
    "PAID",
  );
  const [commissionCashDate, setCommissionCashDate] = useState(today);

  const isOwner = me?.role === "OWNER";
  const categories = useMemo(
    () => (entryType === "INCOME" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES),
    [entryType],
  );
  const commissionEntries = useMemo(
    () => entries.filter((entry) => entry.category === "COMMISSION"),
    [entries],
  );

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        accountData,
        balanceData,
        entryData,
        cashData,
        dreData,
        commissionData,
        salesData,
      ] = await Promise.all([
        getFinancialAccounts(),
        getAccountBalances(),
        getFinancialEntries(fromDate, toDate),
        getCashFlow(fromDate, toDate),
        getDre(fromDate, toDate),
        getCommissions(fromDate, toDate),
        getSales(fromDate, toDate),
      ]);
      setAccounts(accountData);
      setBalances(balanceData);
      setEntries(entryData);
      setCash(cashData);
      setDre(dreData);
      setCommissions(commissionData);
      setSales(salesData);
      if (accountData.length > 0 && !entryAccount) {
        setEntryAccount(accountData[0].id);
      }
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar financeiro.",
      );
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, entryAccount]);

  useEffect(() => {
    getMe()
      .then(setMe)
      .catch(() => {
        // AppShell redireciona para o login.
      });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleCreateAccount(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await createFinancialAccount({
        name: accountName.trim(),
        type: accountType,
        initial_balance: initialBalance,
      });
      await load();
      setNotice("Conta criada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao criar conta.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateEntry(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!entryAccount) {
      setError("Cadastre uma conta antes de lançar.");
      return;
    }
    setSaving(true);
    try {
      await createFinancialEntry({
        account_id: entryAccount,
        type: entryType,
        category: entryCategory,
        description: entryDescription.trim(),
        amount: entryAmount,
        competence_date: entryCompetence,
        cash_date: entryStatus === "PAID" ? entryCashDate : null,
        status: entryStatus,
      });
      setEntryDescription("");
      await load();
      setNotice("Lançamento registrado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao criar lançamento.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateCommission(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!entryAccount) {
      setError("Cadastre uma conta antes de lançar a comissão.");
      return;
    }
    const collaborator = commissions?.items.find(
      (item) => item.collaborator_id === commissionCollaborator,
    );
    const description =
      commissionDescription.trim() ||
      (collaborator
        ? `Comissão — ${collaborator.collaborator_name}`
        : "Comissão");
    setSaving(true);
    try {
      await createFinancialEntry({
        account_id: entryAccount,
        type: "EXPENSE",
        category: "COMMISSION",
        description,
        amount: commissionAmount,
        competence_date: commissionCompetence,
        cash_date:
          commissionStatus === "PAID" ? commissionCashDate : null,
        status: commissionStatus,
      });
      setCommissionDescription("");
      setCommissionAmount("0.00");
      await load();
      setNotice("Comissão lançada no financeiro.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao lançar comissão.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function markPaid(entry: FinancialEntry) {
    setError(null);
    try {
      await updateFinancialEntry(entry.id, {
        status: "PAID",
        cash_date: today,
      });
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao baixar lançamento.",
      );
    }
  }

  async function handleExport() {
    setError(null);
    try {
      const csv = await getFinanceCsv(fromDate, toDate);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sora-financeiro-${fromDate}-${toDate}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao exportar CSV.",
      );
    }
  }

  if (!isOwner && me) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">Apenas o dono/gestor acessa o financeiro.</p>
        </div>
      </AppShell>
    );
  }

  const dreRows = dre
    ? [
        ["Receita bruta", dre.gross_revenue, false],
        ["(-) Deduções e taxas", dre.deductions, true],
        ["(-) Custos e insumos", dre.costs, true],
        ["(-) Despesas operacionais", dre.operating_expenses, true],
        ["(=) Lucro líquido", dre.net_profit, false],
        ["Comissões apuradas", dre.commissions_accrued, false],
        ["Dízimo", dre.tithe_amount, true],
        ["Oferta", dre.offering_amount, true],
        ["Após dízimo/oferta", dre.after_tithe_and_offering, false],
      ]
    : [];

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>{meta.title}</h1>
            <p>{meta.description}</p>
          </div>
          {section !== "accounts" ? (
            <div className="page-actions finance-datebar">
              <input
                aria-label="De"
                type="date"
                value={fromDate}
                onChange={(event) => setFromDate(event.target.value)}
              />
              <span className="muted-small">até</span>
              <input
                aria-label="Até"
                type="date"
                value={toDate}
                onChange={(event) => setToDate(event.target.value)}
              />
              <button
                className="button button-ghost button-small"
                type="button"
                onClick={handleExport}
              >
                Exportar CSV
              </button>
            </div>
          ) : null}
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {section === "cashflow" ? (
          <section className="stats">
            <article className="stat">
              <div className="stat-label">Saldo de abertura</div>
              <div className="stat-value">
                {formatPrice(cash?.opening_balance ?? null)}
              </div>
              <div className="stat-note">Caixa + contas no início do período</div>
            </article>
            <article className="stat">
              <div className="stat-label">Entradas</div>
              <div className="stat-value">
                {formatPrice(cash?.inflows ?? null)}
              </div>
              <div className="stat-note">Recebimentos realizados</div>
            </article>
            <article className="stat">
              <div className="stat-label">Saídas</div>
              <div className="stat-value">
                {formatPrice(cash?.outflows ?? null)}
              </div>
              <div className="stat-note">Pagamentos realizados</div>
            </article>
            <article className="stat">
              <div className="stat-label">Saldo final</div>
              <div className="stat-value">
                {formatPrice(cash?.closing_balance ?? null)}
              </div>
              <div className="stat-note">Regime de caixa</div>
            </article>
          </section>
        ) : null}

        {section === "cashflow" ? (
          <div className="finance-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Fluxo de caixa</h2>
                <span className="muted-small">
                  {formatDateLabel(fromDate)} — {formatDateLabel(toDate)}
                </span>
              </div>
              {loading ? (
                <p className="table-empty">Carregando…</p>
              ) : (
                <table className="data-table finance-summary">
                  <tbody>
                    <tr>
                      <td>Abertura</td>
                      <td className="price-cell">
                        {formatPrice(cash?.opening_balance ?? null)}
                      </td>
                    </tr>
                    <tr>
                      <td>Entradas realizadas</td>
                      <td className="price-cell positive">
                        + {formatPrice(cash?.inflows ?? null)}
                      </td>
                    </tr>
                    <tr>
                      <td>Saídas realizadas</td>
                      <td className="price-cell negative">
                        − {formatPrice(cash?.outflows ?? null)}
                      </td>
                    </tr>
                    <tr>
                      <td>
                        <strong>Saldo final</strong>
                      </td>
                      <td className="price-cell">
                        <strong>
                          {formatPrice(cash?.closing_balance ?? null)}
                        </strong>
                      </td>
                    </tr>
                  </tbody>
                </table>
              )}
            </section>
          </div>
        ) : null}

        {section === "dre" ? (
          <div className="finance-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>DRE simplificada</h2>
                {dre?.tithe_enabled ? (
                  <span className="pill pill-active">Dízimo ativo</span>
                ) : null}
              </div>
              {loading || !dre ? (
                <p className="table-empty">Carregando…</p>
              ) : (
                <table className="data-table finance-summary">
                  <tbody>
                    {dreRows.map(([label, value, negative]) => (
                      <tr key={String(label)}>
                        <td>{label}</td>
                        <td
                          className={`price-cell ${
                            negative
                              ? "negative"
                              : value === dre.net_profit
                                ? "positive"
                                : ""
                          }`}
                        >
                          {negative ? "− " : ""}
                          {formatPrice(String(value))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>
        ) : null}

        {section === "accounts" ? (
          <div className="admin-grid finance-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Contas e saldos</h2>
                <span className="muted-small">{balances.length} conta(s)</span>
              </div>
              {balances.length === 0 ? (
                <p className="table-empty">Nenhuma conta cadastrada.</p>
              ) : (
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Conta</th>
                      <th>Tipo</th>
                      <th>Saldo inicial</th>
                      <th>Saldo atual</th>
                    </tr>
                  </thead>
                  <tbody>
                    {balances.map((account) => (
                      <tr key={account.account_id}>
                        <td>
                          <strong>{account.name}</strong>
                        </td>
                        <td>{account.type === "CASH" ? "Caixa" : "Banco"}</td>
                        <td className="price-cell">
                          {formatPrice(account.initial_balance)}
                        </td>
                        <td className="price-cell">
                          {formatPrice(account.balance)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className="panel">
              <div className="panel-title">
                <h2>Nova conta</h2>
              </div>
              <form onSubmit={handleCreateAccount}>
                <div className="field">
                  <label htmlFor="account-name">Nome</label>
                  <input
                    id="account-name"
                    value={accountName}
                    onChange={(event) => setAccountName(event.target.value)}
                    required
                  />
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="account-type">Tipo</label>
                    <select
                      id="account-type"
                      value={accountType}
                      onChange={(event) =>
                        setAccountType(event.target.value as "CASH" | "BANK")
                      }
                    >
                      <option value="CASH">Caixa</option>
                      <option value="BANK">Banco</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="account-balance">Saldo inicial (R$)</label>
                    <input
                      id="account-balance"
                      value={initialBalance}
                      onChange={(event) =>
                        setInitialBalance(event.target.value)
                      }
                    />
                  </div>
                </div>
                <button className="button" type="submit" disabled={saving}>
                  {saving ? "Salvando…" : "Criar conta"}
                </button>
              </form>
            </section>
          </div>
        ) : null}

        {section === "entries" ? (
          <div className="admin-grid finance-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Lançamentos</h2>
                <span className="muted-small">{entries.length} no período</span>
              </div>
            {entries.length === 0 ? (
              <p className="table-empty">Nenhum lançamento no período.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Competência</th>
                      <th>Descrição</th>
                      <th>Categoria</th>
                      <th>Valor</th>
                      <th>Status</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {entries.map((entry) => (
                      <tr key={entry.id}>
                        <td>{formatDateLabel(entry.competence_date)}</td>
                        <td>
                          <strong>{entry.description}</strong>
                          {entry.cash_date ? (
                            <div className="muted-small">
                              caixa {formatDateLabel(entry.cash_date)}
                            </div>
                          ) : null}
                        </td>
                        <td className="muted-small">
                          {CATEGORY_LABEL[entry.category]}
                        </td>
                        <td
                          className={`price-cell ${
                            entry.type === "INCOME" ? "positive" : "negative"
                          }`}
                        >
                          {entry.type === "INCOME" ? "+" : "−"}{" "}
                          {formatPrice(entry.amount)}
                        </td>
                        <td>
                          <span
                            className={`pill ${
                              entry.status === "PAID" ? "pill-active" : ""
                            }`}
                          >
                            {entry.status === "PAID" ? "Realizado" : "Pendente"}
                          </span>
                        </td>
                        <td>
                          {entry.status === "PENDING" ? (
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              onClick={() => markPaid(entry)}
                            >
                              Baixar
                            </button>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-title">
              <h2>Novo lançamento</h2>
            </div>
            <form onSubmit={handleCreateEntry}>
              <div className="field">
                <label htmlFor="entry-account">Conta</label>
                <select
                  id="entry-account"
                  value={entryAccount}
                  onChange={(event) => setEntryAccount(event.target.value)}
                  required
                >
                  <option value="">Selecione…</option>
                  {accounts.map((account) => (
                    <option key={account.id} value={account.id}>
                      {account.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="entry-type">Tipo</label>
                  <select
                    id="entry-type"
                    value={entryType}
                    onChange={(event) => {
                      const type = event.target.value as FinancialEntryType;
                      setEntryType(type);
                      setEntryCategory(
                        type === "INCOME" ? "SERVICE" : "RENT",
                      );
                    }}
                  >
                    <option value="INCOME">Entrada</option>
                    <option value="EXPENSE">Saída</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="entry-category">Categoria</label>
                  <select
                    id="entry-category"
                    value={entryCategory}
                    onChange={(event) =>
                      setEntryCategory(
                        event.target.value as FinancialCategory,
                      )
                    }
                  >
                    {categories.map((category) => (
                      <option key={category} value={category}>
                        {CATEGORY_LABEL[category]}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="field">
                <label htmlFor="entry-description">Descrição</label>
                <input
                  id="entry-description"
                  value={entryDescription}
                  onChange={(event) => setEntryDescription(event.target.value)}
                  required
                />
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="entry-amount">Valor (R$)</label>
                  <input
                    id="entry-amount"
                    value={entryAmount}
                    onChange={(event) => setEntryAmount(event.target.value)}
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="entry-competence">Competência</label>
                  <input
                    id="entry-competence"
                    type="date"
                    value={entryCompetence}
                    onChange={(event) => setEntryCompetence(event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="entry-status">Status</label>
                  <select
                    id="entry-status"
                    value={entryStatus}
                    onChange={(event) =>
                      setEntryStatus(event.target.value as "PENDING" | "PAID")
                    }
                  >
                    <option value="PAID">Realizado</option>
                    <option value="PENDING">Pendente</option>
                  </select>
                </div>
                {entryStatus === "PAID" ? (
                  <div className="field">
                    <label htmlFor="entry-cash">Data de caixa</label>
                    <input
                      id="entry-cash"
                      type="date"
                      value={entryCashDate}
                      onChange={(event) => setEntryCashDate(event.target.value)}
                    />
                  </div>
                ) : null}
              </div>
              <button className="button" type="submit" disabled={saving}>
                {saving ? "Salvando…" : "Registrar lançamento"}
              </button>
            </form>
          </section>
        </div>
        ) : null}

        {section === "commissions" ? (
          <>
            <div className="admin-grid finance-grid">
              <section className="panel">
                <div className="panel-title">
                  <h2>Comissões apuradas</h2>
                  <span className="muted-small">
                    Total {formatPrice(commissions?.total ?? null)}
                  </span>
                </div>
                <p className="muted-small commission-hint">
                  Cálculo automático sobre atendimentos concluídos. As regras
                  por profissional ficam em{" "}
                  <a href="/equipe">Equipe &amp; Comissões</a>.
                </p>
                {!commissions || commissions.items.length === 0 ? (
                  <p className="table-empty">
                    Nenhum atendimento concluído no período.
                  </p>
                ) : (
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Profissional</th>
                        <th>Atendimentos</th>
                        <th>Receita</th>
                        <th>Comissão</th>
                      </tr>
                    </thead>
                    <tbody>
                      {commissions.items.map((item) => (
                        <tr key={item.collaborator_id}>
                          <td>
                            <strong>{item.collaborator_name}</strong>
                          </td>
                          <td>{item.completed_appointments}</td>
                          <td className="price-cell">
                            {formatPrice(item.gross_revenue)}
                          </td>
                          <td className="price-cell">
                            {formatPrice(item.commission_amount)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </section>

              <section className="panel">
                <div className="panel-title">
                  <h2>Registrar comissão</h2>
                </div>
                <form onSubmit={handleCreateCommission}>
                  <div className="field">
                    <label htmlFor="commission-account">Conta/caixa</label>
                    <select
                      id="commission-account"
                      value={entryAccount}
                      onChange={(event) => setEntryAccount(event.target.value)}
                      required
                    >
                      <option value="">Selecione…</option>
                      {accounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="commission-collaborator">
                      Profissional (opcional)
                    </label>
                    <select
                      id="commission-collaborator"
                      value={commissionCollaborator}
                      onChange={(event) =>
                        setCommissionCollaborator(event.target.value)
                      }
                    >
                      <option value="">Sem vínculo / outro</option>
                      {(commissions?.items ?? []).map((item) => (
                        <option
                          key={item.collaborator_id}
                          value={item.collaborator_id}
                        >
                          {item.collaborator_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="commission-description">
                      Descrição (opcional)
                    </label>
                    <input
                      id="commission-description"
                      value={commissionDescription}
                      onChange={(event) =>
                        setCommissionDescription(event.target.value)
                      }
                      placeholder="Ex.: comissão do atendimento de hoje"
                    />
                  </div>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="commission-amount">Valor (R$)</label>
                      <input
                        id="commission-amount"
                        value={commissionAmount}
                        onChange={(event) =>
                          setCommissionAmount(event.target.value)
                        }
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="commission-competence">
                        Competência
                      </label>
                      <input
                        id="commission-competence"
                        type="date"
                        value={commissionCompetence}
                        onChange={(event) =>
                          setCommissionCompetence(event.target.value)
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="commission-status">Status</label>
                      <select
                        id="commission-status"
                        value={commissionStatus}
                        onChange={(event) =>
                          setCommissionStatus(
                            event.target.value as "PENDING" | "PAID",
                          )
                        }
                      >
                        <option value="PAID">Pago</option>
                        <option value="PENDING">Pendente</option>
                      </select>
                    </div>
                    {commissionStatus === "PAID" ? (
                      <div className="field">
                        <label htmlFor="commission-cash">Data de caixa</label>
                        <input
                          id="commission-cash"
                          type="date"
                          value={commissionCashDate}
                          onChange={(event) =>
                            setCommissionCashDate(event.target.value)
                          }
                        />
                      </div>
                    ) : null}
                  </div>
                  <button className="button" type="submit" disabled={saving}>
                    {saving ? "Lançando…" : "Lançar comissão"}
                  </button>
                </form>
              </section>
            </div>

            <div className="finance-grid">
              <section className="panel">
                <div className="panel-title">
                  <h2>Comissões lançadas no período</h2>
                  <span className="muted-small">
                    {commissionEntries.length} lançamento(s)
                  </span>
                </div>
                {commissionEntries.length === 0 ? (
                  <p className="table-empty">
                    Nenhuma comissão lançada no período.
                  </p>
                ) : (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Competência</th>
                          <th>Descrição</th>
                          <th>Valor</th>
                          <th>Status</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {commissionEntries.map((entry) => (
                          <tr key={entry.id}>
                            <td>{formatDateLabel(entry.competence_date)}</td>
                            <td>
                              <strong>{entry.description}</strong>
                              {entry.cash_date ? (
                                <div className="muted-small">
                                  caixa {formatDateLabel(entry.cash_date)}
                                </div>
                              ) : null}
                            </td>
                            <td className="price-cell negative">
                              − {formatPrice(entry.amount)}
                            </td>
                            <td>
                              <span
                                className={`pill ${
                                  entry.status === "PAID" ? "pill-active" : ""
                                }`}
                              >
                                {entry.status === "PAID"
                                  ? "Pago"
                                  : "Pendente"}
                              </span>
                            </td>
                            <td>
                              {entry.status === "PENDING" ? (
                                <button
                                  className="button button-ghost button-small"
                                  type="button"
                                  onClick={() => markPaid(entry)}
                                >
                                  Baixar
                                </button>
                              ) : null}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </section>
            </div>
          </>
        ) : null}

        {section === "sales" ? (
          <div className="finance-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Valor líquido por venda</h2>
                <span className="muted-small">
                  Líquido {formatPrice(sales?.net_total ?? null)}
                </span>
              </div>
              {!sales || sales.items.length === 0 ? (
                <p className="table-empty">
                  Nenhuma venda concluída no período.
                </p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Horário</th>
                        <th>Cliente</th>
                        <th>Bruto</th>
                        <th>Líquido</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sales.items.map((item) => (
                        <tr key={item.appointment_id}>
                          <td className="muted-small">
                            {formatTime(item.starts_at)}
                          </td>
                          <td>
                            <strong>{item.client_name}</strong>
                            <div className="muted-small">
                              {item.service_name}
                            </div>
                          </td>
                          <td className="price-cell">
                            {formatPrice(item.gross_amount)}
                          </td>
                          <td className="price-cell">
                            {formatPrice(item.net_amount)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
