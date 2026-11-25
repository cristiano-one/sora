"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { login } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [tenantSlug, setTenantSlug] = useState("demo");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login({ tenant_slug: tenantSlug, email, password });
      router.push("/dashboard");
    } catch {
      setError("Credenciais inválidas. Confira clínica, e-mail e senha.");
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
            <div className="brand-tag">Painel de gestão</div>
          </div>
        </div>

        <h1>Entrar no painel</h1>
        <p className="subtitle">
          Acesse com o slug da sua clínica. Este é um preview do fluxo real de
          autenticação (JWT + refresh no Redis).
        </p>

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="tenant">Clínica (slug)</label>
            <input
              id="tenant"
              value={tenantSlug}
              onChange={(event) => setTenantSlug(event.target.value)}
              placeholder="ex.: minha-clinica"
              autoComplete="organization"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="email">E-mail</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="voce@clinica.com"
              autoComplete="email"
              required
            />
          </div>

          <div className="field">
            <label htmlFor="password">Senha</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="••••••••"
              autoComplete="current-password"
              required
            />
          </div>

          <button className="button" type="submit" disabled={loading}>
            {loading ? "Entrando…" : "Entrar"}
          </button>

          {error ? <p className="error">{error}</p> : null}
        </form>

        <p className="hint">
          Demo local: <code>demo</code> · <code>demo@example.com</code> ·{" "}
          <code>demo12345</code>
        </p>
      </section>
    </main>
  );
}
