"use client";

import { useCallback, useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  confirmAdminPayment,
  getAdminPayments,
  getMe,
  type AdminPayment,
  type Me,
} from "@/lib/api";
import { formatIsoDate, formatTime } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

const STATUS_LABEL: Record<AdminPayment["status"], string> = {
  PENDING: "Pendente",
  PAID: "Pago",
  EXPIRED: "Expirado",
  CANCELLED: "Cancelado",
};

export default function PaymentsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [payments, setPayments] = useState<AdminPayment[]>([]);
  const [filter, setFilter] = useState<"PENDING" | "ALL">("PENDING");
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const status = filter === "PENDING" ? "PENDING" : undefined;
      setPayments(await getAdminPayments(status));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar cobranças.",
      );
    } finally {
      setLoading(false);
    }
  }, [filter]);

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
    if (!me) return;
    if (me.role === "COLLABORATOR") {
      setLoading(false);
      return;
    }
    void load();
  }, [load, me]);

  async function handleConfirm(payment: AdminPayment) {
    if (
      !window.confirm(
        `Confirmar manualmente o Pix de ${formatPrice(payment.amount)} ` +
          `de ${payment.client_name}?`,
      )
    ) {
      return;
    }
    setBusyId(payment.id);
    setError(null);
    setNotice(null);
    try {
      await confirmAdminPayment(payment.id);
      await load();
      setNotice("Pagamento confirmado e compromisso liberado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao confirmar pagamento.",
      );
    } finally {
      setBusyId(null);
    }
  }

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Sinais Pix</h1>
            <p>
              Acompanhe cobranças pendentes e confirme pagamentos recebidos
              fora do gateway.
            </p>
          </div>
          {isManager ? (
            <div className="page-actions">
              <button
                className={`button button-ghost button-small ${
                  filter === "PENDING" ? "button-active" : ""
                }`}
                type="button"
                onClick={() => setFilter("PENDING")}
              >
                Pendentes
              </button>
              <button
                className={`button button-ghost button-small ${
                  filter === "ALL" ? "button-active" : ""
                }`}
                type="button"
                onClick={() => setFilter("ALL")}
              >
                Todas
              </button>
            </div>
          ) : null}
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me && !isManager ? (
          <p className="error">Acesso restrito a gestores e administradores.</p>
        ) : (
          <section className="panel">
            <div className="panel-title">
              <h2>Cobranças</h2>
              <span className="muted-small">{payments.length}</span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : payments.length === 0 ? (
              <p className="table-empty">
                Nenhuma cobrança {filter === "PENDING" ? "pendente" : ""}.
              </p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Cliente</th>
                      <th>Origem</th>
                      <th>Valor</th>
                      <th>Status</th>
                      <th>Criada</th>
                      <th>Expira/Pago</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((payment) => (
                      <tr key={payment.id}>
                        <td>
                          <strong>{payment.client_name}</strong>
                          <div className="muted-small">
                            {payment.provider}
                          </div>
                        </td>
                        <td>
                          {payment.appointment_id
                            ? "Sinal de agendamento"
                            : payment.subscription_id
                              ? "Assinatura"
                              : "Cobrança"}
                        </td>
                        <td className="price-cell">
                          {formatPrice(payment.amount)}
                        </td>
                        <td>
                          <span
                            className={`pill ${
                              payment.status === "PAID"
                                ? "pill-active"
                                : payment.status === "PENDING"
                                  ? "pill-blocked"
                                  : ""
                            }`}
                          >
                            {STATUS_LABEL[payment.status]}
                          </span>
                        </td>
                        <td>{formatIsoDate(payment.created_at)}</td>
                        <td>
                          {formatIsoDate(
                            payment.paid_at ?? payment.expires_at,
                          )}{" "}
                          {formatTime(payment.paid_at ?? payment.expires_at)}
                        </td>
                        <td>
                          {payment.status === "PENDING" ? (
                            <button
                              className="button button-small"
                              type="button"
                              disabled={busyId === payment.id}
                              onClick={() => handleConfirm(payment)}
                            >
                              {busyId === payment.id
                                ? "Confirmando…"
                                : "Confirmar Pix"}
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
        )}
      </div>
    </AppShell>
  );
}
