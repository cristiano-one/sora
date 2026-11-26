"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { ApiError, createTenant, login } from "@/lib/api";
import {
  BUSINESS_PROFILES,
  profileOption,
  type BusinessProfile,
} from "@/lib/profiles";

function slugify(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 100);
}

export default function SignupPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [taxRegime, setTaxRegime] = useState<"MEI" | "COMPLETE">("MEI");
  const [businessProfile, setBusinessProfile] =
    useState<BusinessProfile>("AESTHETICS");
  const [ownerName, setOwnerName] = useState("");
  const [ownerEmail, setOwnerEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("As senhas não conferem.");
      return;
    }
    setLoading(true);
    try {
      const tenant = await createTenant({
        name: name.trim(),
        slug: slug || slugify(name),
        tax_regime: taxRegime,
        business_profile: businessProfile,
        owner_full_name: ownerName.trim(),
        owner_email: ownerEmail.trim(),
        owner_password: password,
      });
      await login({
        tenant_slug: tenant.slug,
        email: ownerEmail.trim(),
        password,
      });
      router.push("/dashboard");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível criar o negócio.",
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
            <div className="brand-tag">Criar minha conta</div>
          </div>
        </div>

        <h1>Comece agora</h1>
        <p className="subtitle">
          Cadastre seu negócio e o usuário dono/gestor. Você escolhe o tipo de
          negócio e já entra no painel em seguida.
        </p>

        {error ? <p className="error">{error}</p> : null}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="clinic-name">Nome do negócio</label>
            <input
              id="clinic-name"
              value={name}
              onChange={(event) => {
                setName(event.target.value);
                if (!slug) setSlug(slugify(event.target.value));
              }}
              required
              maxLength={255}
            />
          </div>
          <div className="field">
            <label htmlFor="clinic-slug">Slug (URL)</label>
            <input
              id="clinic-slug"
              value={slug}
              onChange={(event) => setSlug(slugify(event.target.value))}
              placeholder="minha-clinica"
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
              minLength={3}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="tax-regime">Regime tributário</label>
            <select
              id="tax-regime"
              value={taxRegime}
              onChange={(event) =>
                setTaxRegime(event.target.value as "MEI" | "COMPLETE")
              }
            >
              <option value="MEI">MEI (simplificado)</option>
              <option value="COMPLETE">Completo</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="business-profile">Tipo de negócio</label>
            <select
              id="business-profile"
              value={businessProfile}
              onChange={(event) =>
                setBusinessProfile(event.target.value as BusinessProfile)
              }
              required
            >
              {BUSINESS_PROFILES.map((profile) => (
                <option key={profile.value} value={profile.value}>
                  {profile.label}
                </option>
              ))}
            </select>
            <p className="muted-small">
              {profileOption(businessProfile).description}
            </p>
          </div>
          <div className="field">
            <label htmlFor="owner-name">Seu nome</label>
            <input
              id="owner-name"
              value={ownerName}
              onChange={(event) => setOwnerName(event.target.value)}
              required
              maxLength={255}
            />
          </div>
          <div className="field">
            <label htmlFor="owner-email">Seu e-mail</label>
            <input
              id="owner-email"
              type="email"
              value={ownerEmail}
              onChange={(event) => setOwnerEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="signup-password">Senha</label>
            <input
              id="signup-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={8}
              autoComplete="new-password"
              required
            />
          </div>
          <div className="field">
            <label htmlFor="signup-confirm">Confirmar senha</label>
            <input
              id="signup-confirm"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              minLength={8}
              autoComplete="new-password"
              required
            />
          </div>
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Criando conta…" : "Criar conta e entrar"}
          </button>
        </form>

        <p className="muted-small">
          Já tem conta? <Link href="/login">Entrar no painel</Link>
        </p>
      </section>
    </main>
  );
}
