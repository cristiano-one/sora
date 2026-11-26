"use client";

import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  getMyCommission,
  getMyCommissionRule,
  type CommissionSummary,
  type MyCommissionRule,
} from "@/lib/api";
import { todayInTenant } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

const BASE_LABEL: Record<string, string> = {
  GROSS: "valor bruto do serviço",
  NET: "valor líquido (bruto − custo)",
};

export default function MyCommissionPage() {
  const today = todayInTenant();
  const [fromDate, setFromDate] = useState(`${today.slice(0, 7)}-01`);
  const [toDate, setToDate] = useState(today);
  const [summary, setSummary] = useState<CommissionSummary | null>(null);
  const [rule, setRule] = useState<MyCommissionRule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryData, ruleData] = await Promise.all([
        getMyCommission(fromDate, toDate),
        getMyCommissionRule(),
      ]);
      setSummary(summaryData);
      setRule(ruleData);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar comissão.",
      );
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    void load();
  }, [load]);

  const item = summary?.items[0] ?? null;

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Minha comissão</h1>
            <p>
              Atendimentos concluídos e comissão apurada no período selecionado.
            </p>
          </div>
        </header>

        <section className="panel finance-filter">
          <div className="field">
            <label htmlFor="commission-from">De</label>
            <input
              id="commission-from"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="commission-to">Até</label>
            <input
              id="commission-to"
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
          <button className="button" type="button" onClick={() => load()}>
            Atualizar
          </button>
        </section>

        {error ? <p className="error">{error}</p> : null}

        {rule ? (
          <section className="stats">
            <article className="stat">
              <div className="stat-label">Regra</div>
              <div className="stat-value">
                {rule.commission_percentage
                  ? `${rule.commission_percentage}%`
                  : "—"}
              </div>
              <div className="stat-note">
                {rule.commission_fixed
                  ? `+ ${formatPrice(rule.commission_fixed)} fixo`
                  : `Base: ${BASE_LABEL[rule.commission_base]}`}
              </div>
            </article>
            <article className="stat">
              <div className="stat-label">Atendimentos</div>
              <div className="stat-value">
                {item?.completed_appointments ?? 0}
              </div>
              <div className="stat-note">Concluídos no período</div>
            </article>
            <article className="stat">
              <div className="stat-label">Receita atendida</div>
              <div className="stat-value">
                {formatPrice(item?.gross_revenue ?? "0.00")}
              </div>
              <div className="stat-note">Valor bruto dos serviços</div>
            </article>
            <article className="stat">
              <div className="stat-label">Comissão</div>
              <div className="stat-value">
                {formatPrice(summary?.total ?? "0.00")}
              </div>
              <div className="stat-note">A receber/recebida no período</div>
            </article>
          </section>
        ) : null}

        <section className="panel section-gap">
          <div className="panel-title">
            <h2>Detalhamento</h2>
            <span className="muted-small">
              {fromDate} → {toDate}
            </span>
          </div>
          {loading ? (
            <p className="table-empty">Carregando…</p>
          ) : !item ? (
            <p className="table-empty">
              Nenhum atendimento concluído no período.
            </p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Profissional</th>
                    <th>Atendimentos</th>
                    <th>Receita bruta</th>
                    <th>Comissão</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>
                      <strong>{item.collaborator_name}</strong>
                    </td>
                    <td>{item.completed_appointments}</td>
                    <td className="price-cell">
                      {formatPrice(item.gross_revenue)}
                    </td>
                    <td className="price-cell price-strong">
                      {formatPrice(item.commission_amount)}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}
        </section>

        <p className="muted-small section-gap">
          A comissão considera apenas atendimentos com status concluído e é
          calculada pelo backend com base na regra cadastrada pela gestão.
        </p>
      </div>
    </AppShell>
  );
}
