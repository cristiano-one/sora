"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ApiError,
  confirmPublicCheckin,
  getPublicCheckin,
  type PublicCheckin,
} from "@/lib/api";
import { formatTime } from "@/lib/agenda";

export default function CheckinPage() {
  const params = useParams<{ slug: string; token: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const token = Array.isArray(params.token) ? params.token[0] : params.token;
  const [data, setData] = useState<PublicCheckin | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!slug || !token) {
      setError("Link de check-in inválido.");
      setLoading(false);
      return;
    }
    let active = true;
    getPublicCheckin(slug, token)
      .then((result) => {
        if (active) setData(result);
      })
      .catch((err) => {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "Check-in inválido ou expirado.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [slug, token]);

  async function handleCheckin() {
    if (!slug || !token) return;
    setConfirming(true);
    setError(null);
    try {
      setData(await confirmPublicCheckin(slug, token));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Não foi possível fazer check-in.",
      );
    } finally {
      setConfirming(false);
    }
  }

  if (loading) {
    return (
      <main className="public-shell">
        <div className="public-card public-card-narrow">
          <p className="subtitle">Carregando check-in…</p>
        </div>
      </main>
    );
  }

  if (!data) {
    return (
      <main className="public-shell">
        <div className="public-card public-card-narrow">
          <div className="public-success-mark public-success-muted">!</div>
          <h1>Check-in indisponível</h1>
          <p className="subtitle">
            {error ?? "Este link é inválido ou expirou."}
          </p>
        </div>
      </main>
    );
  }

  const checked = data.checked_in_at !== null;
  const blocked = !data.can_checkin && !checked;

  return (
    <main className="public-shell">
      <div className="public-card public-card-narrow checkin-card">
        <div className="brand">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-name">{data.tenant_name}</div>
            <div className="brand-tag">Check-in de chegada</div>
          </div>
        </div>

        <div className={`checkin-mark ${checked ? "checkin-mark-done" : ""}`}>
          {checked ? "✓" : "⌂"}
        </div>
        <h1>
          {checked
            ? `Tudo certo, ${data.client_name}!`
            : `Olá, ${data.client_name}!`}
        </h1>
        <p className="subtitle">
          {checked
            ? "Sua chegada foi registrada. A equipe já foi avisada."
            : blocked
              ? "Este atendimento não está disponível para check-in."
              : "Confirme sua chegada para avisarmos a equipe."}
        </p>

        <dl className="public-summary checkin-summary">
          <div>
            <dt>Serviço</dt>
            <dd>{data.service_name}</dd>
          </div>
          <div>
            <dt>Profissional</dt>
            <dd>{data.collaborator_name}</dd>
          </div>
          <div>
            <dt>Horário</dt>
            <dd>
              {formatTime(data.starts_at)}–{formatTime(data.ends_at)}
            </dd>
          </div>
        </dl>

        {error ? <p className="error">{error}</p> : null}

        {checked ? (
          <p className="public-notice">
            Check-in realizado às {formatTime(data.checked_in_at!)}.
          </p>
        ) : data.can_checkin ? (
          <button
            className="button"
            type="button"
            onClick={handleCheckin}
            disabled={confirming}
          >
            {confirming ? "Confirmando…" : "Confirmar que cheguei"}
          </button>
        ) : null}
      </div>
    </main>
  );
}
