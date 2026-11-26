"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { acceptInvite, ApiError } from "@/lib/api";

export default function AcceptInvitePage() {
  const [tenantSlug, setTenantSlug] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setTenantSlug(params.get("tenant") ?? "");
    setToken(params.get("token") ?? "");
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      await acceptInvite({
        tenant_slug: tenantSlug,
        token,
        new_password: password,
      });
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível aceitar o convite.",
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
            <div className="brand-tag">Convite da equipe</div>
          </div>
        </div>
        <h1>Bem-vindo à equipe</h1>

        {done ? (
          <>
            <p className="public-notice">
              Convite aceito e senha definida. Você já pode entrar.
            </p>
            <Link className="button" href="/login">
              Entrar no painel
            </Link>
          </>
        ) : (
          <>
            <p className="subtitle">
              Defina sua senha inicial para acessar o painel e o app.
            </p>
            {error ? <p className="error">{error}</p> : null}
            {!token ? (
              <p className="error">
                Convite inválido ou expirado. Peça um novo à gestão.
              </p>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="field">
                  <label htmlFor="invite-password">Senha</label>
                  <input
                    id="invite-password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    autoComplete="new-password"
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="invite-confirm">Confirmar senha</label>
                  <input
                    id="invite-confirm"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) =>
                      setConfirmPassword(event.target.value)
                    }
                    minLength={8}
                    autoComplete="new-password"
                    required
                  />
                </div>
                <button className="button" type="submit" disabled={loading}>
                  {loading ? "Ativando…" : "Aceitar convite"}
                </button>
              </form>
            )}
          </>
        )}
      </section>
    </main>
  );
}
