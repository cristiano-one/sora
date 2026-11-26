"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { ApiError, forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [tenantSlug, setTenantSlug] = useState("");
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);
    try {
      const result = await forgotPassword({
        tenant_slug: tenantSlug.trim(),
        email: email.trim(),
      });
      setMessage(result.message);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível solicitar a recuperação.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="shell">
      <section className="card">
        <div className="brand">
          <span className="brand-mark">S</span>
          <div>
            <div className="brand-name">Sora Studio</div>
            <div className="brand-tag">Recuperar senha</div>
          </div>
        </div>
        <h1>Esqueceu a senha?</h1>
        <p className="subtitle">
          Informe a clínica e seu e-mail. Enviaremos um link válido por 30
          minutos.
        </p>

        {error ? <p className="error">{error}</p> : null}
        {message ? <p className="public-notice">{message}</p> : null}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="forgot-tenant">Clínica (slug)</label>
            <input
              id="forgot-tenant"
              value={tenantSlug}
              onChange={(event) => setTenantSlug(event.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="forgot-email">E-mail</label>
            <input
              id="forgot-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Enviando…" : "Enviar link"}
          </button>
        </form>

        <p className="muted-small">
          <Link href="/login">Voltar para o login</Link>
        </p>
      </section>
    </main>
  );
}
