"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  cancelSaleInvoice,
  getMe,
  getSaleInvoice,
  issueSaleInvoice,
  listSales,
  type FiscalInvoice,
  type Me,
  type Sale,
  type SaleStatus,
} from "@/lib/api";
import { formatIsoDate, todayInTenant } from "@/lib/agenda";
import { sumMoney } from "@/lib/finance";
import { formatPrice } from "@/lib/public";

const STATUS_LABEL: Record<SaleStatus, string> = {
  OPEN: "Aberta",
  PAID: "Paga",
  CANCELLED: "Cancelada",
};

const PAYMENT_LABEL: Record<string, string> = {
  PIX: "Pix",
  CASH: "Dinheiro",
  CARD: "Cartão",
  BOLETO: "Boleto",
  TRANSFER: "Transferência",
  OTHER: "Outro",
};

export default function SalesHistoryPage() {
  const today = todayInTenant();
  const [me, setMe] = useState<Me | null>(null);
  const [fromDate, setFromDate] = useState(`${today.slice(0, 7)}-01`);
  const [toDate, setToDate] = useState(today);
  const [sales, setSales] = useState<Sale[]>([]);
  const [invoices, setInvoices] = useState<Record<string, FiscalInvoice>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listSales(fromDate, toDate);
      setSales(data);
      const paid = data.filter((sale) => sale.status === "PAID");
      const results = await Promise.allSettled(
        paid.map(async (sale) => ({
          saleId: sale.id,
          invoice: await getSaleInvoice(sale.id),
        })),
      );
      const map: Record<string, FiscalInvoice> = {};
      for (const result of results) {
        if (result.status === "fulfilled") {
          map[result.value.saleId] = result.value.invoice;
        }
      }
      setInvoices(map);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar comandas.",
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
    if (me?.role === "OWNER" || me?.role === "ADMIN") void load();
    else if (me) setLoading(false);
  }, [load, me]);

  async function handleIssue(sale: Sale) {
    setBusyId(sale.id);
    setError(null);
    setNotice(null);
    try {
      const invoice = await issueSaleInvoice(sale.id);
      setInvoices((current) => ({ ...current, [sale.id]: invoice }));
      setNotice(`NFS-e ${invoice.number} emitida.`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao emitir NFS-e.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function handleCancel(sale: Sale) {
    if (!window.confirm("Cancelar a NFS-e desta comanda?")) return;
    setBusyId(sale.id);
    setError(null);
    setNotice(null);
    try {
      const invoice = await cancelSaleInvoice(sale.id);
      setInvoices((current) => ({ ...current, [sale.id]: invoice }));
      setNotice(`NFS-e ${invoice.number} cancelada.`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao cancelar NFS-e.",
      );
    } finally {
      setBusyId(null);
    }
  }

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const paidTotal = sumMoney(
    sales
      .filter((sale) => sale.status === "PAID")
      .map((sale) => sale.total),
  );

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Comandas</h1>
            <p>
              Histórico de comandas, pagamentos e emissão de NFS-e.
            </p>
          </div>
          <Link className="button button-ghost button-small" href="/agenda">
            Abrir agenda
          </Link>
        </header>

        <section className="panel finance-filter">
          <div className="field">
            <label htmlFor="sales-from">De</label>
            <input
              id="sales-from"
              type="date"
              value={fromDate}
              onChange={(event) => setFromDate(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="sales-to">Até</label>
            <input
              id="sales-to"
              type="date"
              value={toDate}
              onChange={(event) => setToDate(event.target.value)}
            />
          </div>
          <button className="button" type="button" onClick={() => load()}>
            Atualizar
          </button>
          <span className="pill pill-active">
            Pagas: {formatPrice(paidTotal)}
          </span>
        </section>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me && !isManager ? (
          <p className="error">Acesso restrito a gestores.</p>
        ) : (
          <section className="panel">
            <div className="panel-title">
              <h2>Comandas do período</h2>
              <span className="muted-small">{sales.length}</span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : sales.length === 0 ? (
              <p className="table-empty">Nenhuma comanda no período.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Data</th>
                      <th>Cliente</th>
                      <th>Profissional</th>
                      <th>Total</th>
                      <th>Pagamento</th>
                      <th>Status</th>
                      <th>NFS-e</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {sales.map((sale) => {
                      const invoice = invoices[sale.id];
                      return (
                        <tr key={sale.id}>
                          <td>{formatIsoDate(sale.created_at)}</td>
                          <td>
                            <strong>{sale.client_name}</strong>
                            <div className="muted-small">
                              {sale.items.length} item(ns)
                            </div>
                          </td>
                          <td>{sale.collaborator_name ?? "—"}</td>
                          <td className="price-cell">
                            {formatPrice(sale.total)}
                          </td>
                          <td>
                            {sale.payment_method
                              ? PAYMENT_LABEL[sale.payment_method] ??
                                sale.payment_method
                              : "—"}
                          </td>
                          <td>
                            <span
                              className={`pill ${
                                sale.status === "PAID"
                                  ? "pill-active"
                                  : sale.status === "OPEN"
                                    ? "pill-blocked"
                                    : ""
                              }`}
                            >
                              {STATUS_LABEL[sale.status]}
                            </span>
                          </td>
                          <td>
                            {invoice ? (
                              <>
                                <strong>{invoice.number}</strong>
                                <div className="muted-small">
                                  {invoice.status}
                                </div>
                              </>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td>
                            {sale.status === "PAID" ? (
                              invoice && invoice.status === "ISSUED" ? (
                                <button
                                  className="button button-ghost button-small button-danger"
                                  type="button"
                                  disabled={busyId === sale.id}
                                  onClick={() => handleCancel(sale)}
                                >
                                  Cancelar NFS-e
                                </button>
                              ) : !invoice ? (
                                <button
                                  className="button button-ghost button-small"
                                  type="button"
                                  disabled={busyId === sale.id}
                                  onClick={() => handleIssue(sale)}
                                >
                                  {busyId === sale.id
                                    ? "Emitindo…"
                                    : "Emitir NFS-e"}
                                </button>
                              ) : null
                            ) : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        )}
      </div>
    </AppShell>
  );
}
