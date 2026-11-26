"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createPayroll,
  deletePayroll,
  getFinancialAccounts,
  getMe,
  getPayroll,
  getUsers,
  updatePayroll,
  type FinancialAccount,
  type Me,
  type PayrollEntry,
  type PayrollKind,
  type UserSummary,
} from "@/lib/api";
import { formatDateOnly, todayInTenant } from "@/lib/agenda";
import { sumMoney } from "@/lib/finance";
import { formatPrice } from "@/lib/public";

const KIND_LABEL: Record<PayrollKind, string> = {
  SALARY: "Salário",
  ADVANCE: "Adiantamento",
  PRO_LABORE: "Pró-labore",
  COMMISSION_PAYOUT: "Repasse de comissão",
};

export default function PayrollPage() {
  const today = todayInTenant();
  const [fromDate, setFromDate] = useState(`${today.slice(0, 7)}-01`);
  const [toDate, setToDate] = useState(today);
  const [me, setMe] = useState<Me | null>(null);
  const [entries, setEntries] = useState<PayrollEntry[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [accounts, setAccounts] = useState<FinancialAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editing, setEditing] = useState<PayrollEntry | null>(null);

  const [userId, setUserId] = useState("");
  const [kind, setKind] = useState<PayrollKind>("SALARY");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("0.00");
  const [competence, setCompetence] = useState(today);
  const [status, setStatus] = useState<"PENDING" | "PAID">("PENDING");
  const [cashDate, setCashDate] = useState(today);
  const [accountId, setAccountId] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setEntries(await getPayroll(fromDate, toDate));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar folha.",
      );
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    let active = true;
    Promise.all([
      getMe(),
      getUsers(),
      getFinancialAccounts(),
      getPayroll(fromDate, toDate),
    ])
      .then(([user, userData, accountData, payrollData]) => {
        if (!active) return;
        setMe(user);
        setUsers(userData.filter((item) => item.is_active));
        setAccounts(accountData.filter((item) => item.is_active));
        setEntries(payrollData);
        setAccountId(accountData[0]?.id ?? "");
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar folha.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [fromDate, toDate]);

  function resetForm() {
    setEditing(null);
    setUserId("");
    setKind("SALARY");
    setDescription("");
    setAmount("0.00");
    setCompetence(today);
    setStatus("PENDING");
    setCashDate(today);
    setAccountId(accounts[0]?.id ?? "");
  }

  function startEdit(entry: PayrollEntry) {
    setEditing(entry);
    setUserId(entry.user_id);
    setKind(entry.kind);
    setDescription(entry.description);
    setAmount(entry.amount);
    setCompetence(entry.competence_date);
    setStatus(entry.status);
    setCashDate(entry.cash_date ?? today);
    setAccountId("");
    setError(null);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!editing && !userId) {
      setError("Selecione o profissional.");
      return;
    }
    if (status === "PAID" && (!editing || editing.status === "PENDING")) {
      if (!cashDate) {
        setError("Informe a data de pagamento.");
        return;
      }
      if (!accountId) {
        setError("Selecione a conta de saída.");
        return;
      }
    }
    setSaving(true);
    try {
      if (editing) {
        await updatePayroll(editing.id, {
          kind,
          description: description.trim(),
          amount,
          competence_date: competence,
          status,
          cash_date: status === "PAID" ? cashDate : null,
          ...(accountId ? { account_id: accountId } : {}),
        });
      } else {
        await createPayroll({
          user_id: userId,
          kind,
          description: description.trim(),
          amount,
          competence_date: competence,
          status,
          cash_date: status === "PAID" ? cashDate : null,
          account_id: status === "PAID" ? accountId : null,
        });
      }
      resetForm();
      await load();
      setNotice("Verba de folha salva.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar verba.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(entry: PayrollEntry) {
    if (!window.confirm(`Excluir "${entry.description}" da folha?`)) return;
    setError(null);
    try {
      await deletePayroll(entry.id);
      if (editing?.id === entry.id) resetForm();
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir verba.",
      );
    }
  }

  const isOwner = me?.role === "OWNER";
  const paidTotal = sumMoney(
    entries.filter((item) => item.status === "PAID").map((item) => item.amount),
  );
  const pendingTotal = sumMoney(
    entries
      .filter((item) => item.status === "PENDING")
      .map((item) => item.amount),
  );

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Folha &amp; pró-labore</h1>
            <p>
              Salários, adiantamentos, pró-labore e repasses de comissão,
              integrados ao caixa quando pagos.
            </p>
          </div>
        </header>

        <section className="panel finance-filter">
          <div className="field">
            <label htmlFor="payroll-from">De</label>
            <input
              id="payroll-from"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="payroll-to">Até</label>
            <input
              id="payroll-to"
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
          <button className="button" type="button" onClick={() => load()}>
            Atualizar
          </button>
          <span className="pill pill-active">
            Pago: {formatPrice(paidTotal)}
          </span>
          <span className="pill">Pendente: {formatPrice(pendingTotal)}</span>
        </section>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me && !isOwner ? (
          <p className="error">Acesso exclusivo do dono/gestor.</p>
        ) : (
          <div className="admin-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Verbas do período</h2>
                <span className="muted-small">{entries.length}</span>
              </div>
              {loading ? (
                <p className="table-empty">Carregando…</p>
              ) : entries.length === 0 ? (
                <p className="table-empty">
                  Nenhuma verba lançada neste período.
                </p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Profissional</th>
                        <th>Tipo</th>
                        <th>Descrição</th>
                        <th>Competência</th>
                        <th>Valor</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {entries.map((entry) => (
                        <tr key={entry.id}>
                          <td>
                            <strong>{entry.user_name}</strong>
                          </td>
                          <td>{KIND_LABEL[entry.kind]}</td>
                          <td>{entry.description}</td>
                          <td>{formatDateOnly(entry.competence_date)}</td>
                          <td className="price-cell">
                            {formatPrice(entry.amount)}
                          </td>
                          <td>
                            <span
                              className={`pill ${
                                entry.status === "PAID"
                                  ? "pill-active"
                                  : "pill-blocked"
                              }`}
                            >
                              {entry.status === "PAID" ? "Pago" : "Pendente"}
                            </span>
                            {entry.status === "PAID" && entry.cash_date ? (
                              <div className="muted-small">
                                {formatDateOnly(entry.cash_date)}
                              </div>
                            ) : null}
                          </td>
                          <td>
                            <div className="row-actions">
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => startEdit(entry)}
                              >
                                Editar
                              </button>
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                onClick={() => handleDelete(entry)}
                              >
                                Excluir
                              </button>
                            </div>
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
                <h2>{editing ? "Editar verba" : "Nova verba"}</h2>
                {editing ? (
                  <button
                    className="button button-ghost button-small"
                    type="button"
                    onClick={resetForm}
                  >
                    Cancelar edição
                  </button>
                ) : null}
              </div>
              <form onSubmit={handleSave}>
                <div className="field">
                  <label htmlFor="payroll-user">Profissional</label>
                  <select
                    id="payroll-user"
                    value={userId}
                    onChange={(event) => setUserId(event.target.value)}
                    disabled={Boolean(editing)}
                    required={!editing}
                  >
                    <option value="">Selecione…</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.full_name} · {user.role}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="payroll-kind">Tipo</label>
                  <select
                    id="payroll-kind"
                    value={kind}
                    onChange={(event) =>
                      setKind(event.target.value as PayrollKind)
                    }
                  >
                    {Object.entries(KIND_LABEL).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="payroll-description">Descrição</label>
                  <input
                    id="payroll-description"
                    value={description}
                    onChange={(event) => setDescription(event.target.value)}
                    required
                    maxLength={2000}
                  />
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="payroll-amount">Valor (R$)</label>
                    <input
                      id="payroll-amount"
                      inputMode="decimal"
                      value={amount}
                      onChange={(event) => setAmount(event.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="payroll-competence">Competência</label>
                    <input
                      id="payroll-competence"
                      type="date"
                      value={competence}
                      onChange={(event) => setCompetence(event.target.value)}
                      required
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="payroll-status">Status</label>
                  <select
                    id="payroll-status"
                    value={status}
                    onChange={(event) =>
                      setStatus(event.target.value as "PENDING" | "PAID")
                    }
                  >
                    <option value="PENDING">Previsto/pendente</option>
                    <option value="PAID">Pago</option>
                  </select>
                </div>
                {status === "PAID" ? (
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="payroll-cash">Data do pagamento</label>
                      <input
                        id="payroll-cash"
                        type="date"
                        value={cashDate}
                        onChange={(event) => setCashDate(event.target.value)}
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="payroll-account">Conta de saída</label>
                      <select
                        id="payroll-account"
                        value={accountId}
                        onChange={(event) => setAccountId(event.target.value)}
                        required={
                          !editing || editing.status === "PENDING"
                        }
                      >
                        <option value="">
                          {editing?.status === "PAID"
                            ? "Manter conta atual"
                            : "Selecione…"}
                        </option>
                        {accounts.map((account) => (
                          <option key={account.id} value={account.id}>
                            {account.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                ) : null}
                <button className="button" type="submit" disabled={saving}>
                  {saving
                    ? "Salvando…"
                    : editing
                      ? "Salvar alterações"
                      : "Lançar verba"}
                </button>
                <p className="muted-small">
                  Ao marcar como pago, uma despesa de folha é criada
                  automaticamente no financeiro e entra no caixa/DRE.
                </p>
              </form>
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
