"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { formatIsoDate } from "@/lib/agenda";
import {
  BUSINESS_PROFILES,
  profileOption,
  type BusinessProfile,
} from "@/lib/profiles";
import {
  getSystemTenants,
  getSystemToken,
  setSystemToken,
  systemLogin,
  systemLogout,
  updateSystemProfile,
  type SystemTenant,
} from "@/lib/system-api";

export default function SystemConsolePage() {
  const [authenticated, setAuthenticated] = useState(false);
  const [password, setPassword] = useState("");
  const [tenants, setTenants] = useState<SystemTenant[]>([]);
  const [drafts, setDrafts] = useState<Record<string, BusinessProfile>>({});
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadTenants = useCallback(async () => {
    const data = await getSystemTenants();
    setTenants(data);
    setDrafts(
      Object.fromEntries(
        data.map((tenant) => [tenant.id, tenant.business_profile]),
      ),
    );
  }, []);

  useEffect(() => {
    let active = true;
    if (!getSystemToken()) {
      setLoading(false);
      return;
    }
    loadTenants()
      .then(() => {
        if (active) setAuthenticated(true);
      })
      .catch(() => {
        if (active) setSystemToken(null);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadTenants]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await systemLogin(password);
      await loadTenants();
      setPassword("");
      setAuthenticated(true);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Falha ao autenticar.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await systemLogout();
    setAuthenticated(false);
    setTenants([]);
    setDrafts({});
  }

  async function handleSave(tenant: SystemTenant) {
    const profile = drafts[tenant.id];
    if (!profile || profile === tenant.business_profile) return;
    setSavingId(tenant.id);
    setError(null);
    setNotice(null);
    try {
      const updated = await updateSystemProfile(tenant.id, profile);
      setTenants((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setDrafts((current) => ({
        ...current,
        [tenant.id]: updated.business_profile,
      }));
      setNotice(
        `Perfil de ${tenant.name} atualizado para ${profileOption(profile).label}.`,
      );
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Falha ao salvar perfil.",
      );
    } finally {
      setSavingId(null);
    }
  }

  if (loading) {
    return (
      <main className="shell">
        <section className="card">
          <p className="subtitle">Carregando console do sistema…</p>
        </section>
      </main>
    );
  }

  if (!authenticated) {
    return (
      <main className="shell">
        <section className="card">
          <div className="brand">
            <span className="brand-mark">S</span>
            <div>
              <div className="brand-name">Sora Studio</div>
              <div className="brand-tag">Console do provedor</div>
            </div>
          </div>
          <h1>Administração do sistema</h1>
          <p className="subtitle">
            Área restrita à equipe responsável pela plataforma. Informe a senha
            master para configurar o perfil de negócio de cada empresa.
          </p>
          {error ? <p className="error">{error}</p> : null}
          <form onSubmit={handleLogin}>
            <div className="field">
              <label htmlFor="master-password">Senha master</label>
              <input
                id="master-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button className="button" type="submit">
              Entrar no console
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="system-shell">
      <header className="system-header">
        <div>
          <span className="badge">Console do provedor</span>
          <h1>Perfis de negócio</h1>
          <p className="muted-small">
            Defina o segmento de cada empresa. O perfil controla os módulos
            clínicos exibidos para todos os usuários do tenant.
          </p>
        </div>
        <button
          className="button button-ghost button-small"
          type="button"
          onClick={handleLogout}
        >
          Sair do console
        </button>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <section className="system-grid">
        {tenants.map((tenant) => {
          const selected = drafts[tenant.id] ?? tenant.business_profile;
          const option = profileOption(selected);
          return (
            <article className="panel" key={tenant.id}>
              <div className="panel-title">
                <div>
                  <h2>{tenant.name}</h2>
                  <span className="muted-small">
                    {tenant.slug} · {tenant.tax_regime} · criado em{" "}
                    {formatIsoDate(tenant.created_at)}
                  </span>
                </div>
                <span
                  className={`pill ${
                    tenant.is_active ? "pill-active" : "pill-blocked"
                  }`}
                >
                  {tenant.is_active ? "Ativa" : "Inativa"}
                </span>
              </div>

              <div className="field">
                <label htmlFor={`profile-${tenant.id}`}>
                  Perfil de negócio
                </label>
                <select
                  id={`profile-${tenant.id}`}
                  value={selected}
                  onChange={(event) =>
                    setDrafts((current) => ({
                      ...current,
                      [tenant.id]: event.target.value as BusinessProfile,
                    }))
                  }
                >
                  {BUSINESS_PROFILES.map((item) => (
                    <option key={item.value} value={item.value}>
                      {item.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="system-profile-preview">
                <strong>{option.label}</strong>
                <p>{option.description}</p>
                <span
                  className={`pill ${
                    option.medicalRecords ? "pill-active" : ""
                  }`}
                >
                  {option.medicalRecords
                    ? "Prontuário habilitado"
                    : "Sem prontuário"}
                </span>
              </div>

              <button
                className="button button-small"
                type="button"
                disabled={
                  savingId === tenant.id ||
                  selected === tenant.business_profile
                }
                onClick={() => handleSave(tenant)}
              >
                {savingId === tenant.id ? "Salvando…" : "Salvar perfil"}
              </button>
            </article>
          );
        })}
      </section>
    </main>
  );
}
