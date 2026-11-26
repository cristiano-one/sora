"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createTitheDelivery,
  deleteTitheDelivery,
  getMe,
  getTitheSummary,
  type Me,
  type TitheSummary,
} from "@/lib/api";
import { formatDateOnly, todayInTenant } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

export default function TithePage() {
  const today = todayInTenant();
  const [fromDate, setFromDate] = useState(`${today.slice(0, 7)}-01`);
  const [toDate, setToDate] = useState(today);
  const [me, setMe] = useState<Me | null>(null);
  const [summary, setSummary] = useState<TitheSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [titheAmount, setTitheAmount] = useState("0.00");
  const [offeringAmount, setOfferingAmount] = useState("0.00");
  const [competence, setCompetence] = useState(today);
  const [note, setNote] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTitheSummary(fromDate, toDate);
      setSummary(data);
      setTitheAmount(data.pending_tithe);
      setOfferingAmount(data.pending_offering);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao carregar dízimo e oferta.",
      );
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    let active = true;
    getMe()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        if (active) setError("Sessão expirada.");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (me?.role === "OWNER") void load();
    else if (me) setLoading(false);
  }, [load, me]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await createTitheDelivery({
        competence_date: competence,
        tithe_amount: titheAmount,
        offering_amount: offeringAmount,
        note: note.trim() || null,
      });
      setNote("");
      await load();
      setNotice("Entrega registrada.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao registrar entrega.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: string) {
    if (!window.confirm("Excluir esta entrega?")) return;
    setError(null);
    try {
      await deleteTitheDelivery(id);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir entrega.",
      );
    }
  }

  const dre = summary?.dre;
  const isOwner = me?.role === "OWNER";

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Dízimo &amp; oferta</h1>
            <p>
              Provisão calculada pela DRE, entregas realizadas e saldo a
              entregar no período.
            </p>
          </div>
        </header>

        <section className="panel finance-filter">
          <div className="field">
            <label htmlFor="tithe-from">De</label>
            <input
              id="tithe-from"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="tithe-to">Até</label>
            <input
              id="tithe-to"
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
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me && !isOwner ? (
          <p className="error">Acesso exclusivo do dono/gestor.</p>
        ) : loading ? (
          <p className="table-empty">Carregando…</p>
        ) : dre && !dre.tithe_enabled ? (
          <section className="panel">
            <h2>Dízimo e oferta desativados</h2>
            <p className="subtitle">
              Ative a opção em Configurações para calcular a provisão e
              registrar entregas.
            </p>
            <Link
              className="button button-ghost button-small"
              href="/configuracoes"
            >
              Abrir configurações
            </Link>
          </section>
        ) : dre && summary ? (
          <>
            <section className="stats">
              <article className="stat">
                <div className="stat-label">Lucro líquido</div>
                <div className="stat-value">
                  {formatPrice(dre.net_profit)}
                </div>
                <div className="stat-note">
                  Base de {dre.tithe_percentage}% para o dízimo
                </div>
              </article>
              <article className="stat">
                <div className="stat-label">Provisão dízimo</div>
                <div className="stat-value">
                  {formatPrice(dre.tithe_amount)}
                </div>
                <div className="stat-note">
                  Entregue {formatPrice(summary.delivered_tithe)}
                </div>
              </article>
              <article className="stat">
                <div className="stat-label">Provisão oferta</div>
                <div className="stat-value">
                  {formatPrice(dre.offering_amount)}
                </div>
                <div className="stat-note">
                  Entregue {formatPrice(summary.delivered_offering)}
                </div>
              </article>
              <article className="stat">
                <div className="stat-label">A entregar</div>
                <div className="stat-value">
                  {formatPrice(summary.pending_tithe)} +{" "}
                  {formatPrice(summary.pending_offering)}
                </div>
                <div className="stat-note">Dízimo + oferta pendentes</div>
              </article>
            </section>

            <div className="admin-grid section-gap">
              <section className="panel">
                <div className="panel-title">
                  <h2>Entregas</h2>
                  <span className="muted-small">
                    {summary.deliveries.length}
                  </span>
                </div>
                {summary.deliveries.length === 0 ? (
                  <p className="table-empty">Nenhuma entrega registrada.</p>
                ) : (
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Competência</th>
                          <th>Dízimo</th>
                          <th>Oferta</th>
                          <th>Observação</th>
                          <th />
                        </tr>
                      </thead>
                      <tbody>
                        {summary.deliveries.map((delivery) => (
                          <tr key={delivery.id}>
                            <td>
                              {formatDateOnly(delivery.competence_date)}
                            </td>
                            <td className="price-cell">
                              {formatPrice(delivery.tithe_amount)}
                            </td>
                            <td className="price-cell">
                              {formatPrice(delivery.offering_amount)}
                            </td>
                            <td>{delivery.note ?? "—"}</td>
                            <td>
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                onClick={() => handleDelete(delivery.id)}
                              >
                                Excluir
                              </button>
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
                  <h2>Registrar entrega</h2>
                </div>
                <form onSubmit={handleSubmit}>
                  <div className="field">
                    <label htmlFor="tithe-competence">Competência</label>
                    <input
                      id="tithe-competence"
                      type="date"
                      value={competence}
                      onChange={(event) =>
                        setCompetence(event.target.value)
                      }
                      required
                    />
                  </div>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="tithe-value">Dízimo (R$)</label>
                      <input
                        id="tithe-value"
                        inputMode="decimal"
                        value={titheAmount}
                        onChange={(event) =>
                          setTitheAmount(event.target.value)
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="offering-value">Oferta (R$)</label>
                      <input
                        id="offering-value"
                        inputMode="decimal"
                        value={offeringAmount}
                        onChange={(event) =>
                          setOfferingAmount(event.target.value)
                        }
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label htmlFor="tithe-note">Observação</label>
                    <input
                      id="tithe-note"
                      value={note}
                      onChange={(event) => setNote(event.target.value)}
                      maxLength={2000}
                    />
                  </div>
                  <button className="button" type="submit" disabled={saving}>
                    {saving ? "Registrando…" : "Registrar entrega"}
                  </button>
                </form>
              </section>
            </div>
          </>
        ) : null}
      </div>
    </AppShell>
  );
}
