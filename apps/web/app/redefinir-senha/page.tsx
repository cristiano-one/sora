"use client";

import Link from "next/link";
import { useEffect, useState, type FormEvent } from "react";

import { ApiError, resetPassword } from "@/lib/api";

export default function ResetPasswordPage() {
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
      await resetPassword({
        tenant_slug: tenantSlug,
        token,
        new_password: password,
      });
      setDone(true);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível redefinir a senha.",
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
            <div className="brand-tag">Nova senha</div>
          </div>
        </div>
        <h1>Definir nova senha</h1>

        {done ? (
          <>
            <p className="public-notice">
              Senha alterada. Todas as sessões antigas foram encerradas.
            </p>
            <Link className="button" href="/login">
              Entrar com a nova senha
            </Link>
          </>
        ) : (
          <>
            <p className="subtitle">
              Crie uma senha com pelo menos 8 caracteres.
            </p>
            {error ? <p className="error">{error}</p> : null}
            {!token ? (
              <p className="error">
                Link inválido. Solicite uma nova recuperação de senha.
              </p>
            ) : (
              <form onSubmit={handleSubmit}>
                <div className="field">
                  <label htmlFor="reset-password">Nova senha</label>
                  <input
                    id="reset-password"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    minLength={8}
                    autoComplete="new-password"
                    required
                  />
                </div>
                <div className="field">
                  <label htmlFor="reset-confirm">Confirmar senha</label>
                  <input
                    id="reset-confirm"
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
                  {loading ? "Salvando…" : "Salvar nova senha"}
                </button>
              </form>
            )}
          </>
        )}

        <p className="muted-small">
          <Link href="/login">Voltar para o login</Link>
        </p>
      </section>
    </main>
  );
}
