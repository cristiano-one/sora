"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { getMe, logout, type Me } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

export default function DashboardPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let active = true;

    getMe()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        if (active) router.replace("/login");
      });

    return () => {
      active = false;
    };
  }, [router]);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }, [router]);

  if (!me) {
    return (
      <main className="shell">
        <div className="card">
          <p className="subtitle">Carregando painel…</p>
        </div>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <div className="dashboard-inner">
        <header className="topbar">
          <div className="greeting">
            <span className="badge">{ROLE_LABEL[me.role] ?? me.role}</span>
            <h1>Olá, {me.full_name.split(" ")[0]} 👋</h1>
            <p>Bem-vindo ao preview do painel da Sora Studio.</p>
          </div>
          <div className="topbar-actions">
            <Link className="button button-ghost" href="/agenda">
              Agenda
            </Link>
            <button
              className="button button-ghost"
              type="button"
              onClick={handleLogout}
            >
              Sair
            </button>
          </div>
        </header>

        <section className="stats">
          <article className="stat">
            <div className="stat-label">Clínica</div>
            <div className="stat-value">{me.tenant_id.slice(0, 8)}…</div>
            <div className="stat-note">Tenant vinculado ao seu login</div>
          </article>
          <article className="stat">
            <div className="stat-label">Perfil</div>
            <div className="stat-value">{ROLE_LABEL[me.role] ?? me.role}</div>
            <div className="stat-note">RBAC aplicado no backend</div>
          </article>
          <article className="stat">
            <div className="stat-label">Sessão</div>
            <div className="stat-value">Ativa</div>
            <div className="stat-note">JWT + refresh no Redis</div>
          </article>
        </section>

        <section className="grid">
          <Link href="/agenda" className="panel panel-link">
            <h2>Agenda</h2>
            <p>
              Visão do dia por profissional, com validação de duração e sinal
              Pix.
            </p>
            <div className="soon">Abrir agenda →</div>
          </Link>
          <article className="panel">
            <h2>Clientes &amp; Score</h2>
            <p>
              Cadastro, prontuário multimídia e score confidencial do cliente.
            </p>
            <div className="soon">Passos 5–8 da Fase 1</div>
          </article>
          <article className="panel">
            <h2>Financeiro</h2>
            <p>
              Caixa do dia, DRE, comissões e contas — com acesso por papel.
            </p>
            <div className="soon">Fase 4</div>
          </article>
          <article className="panel">
            <h2>SORA IA</h2>
            <p>Atendente no WhatsApp e copiloto de voz/texto no App.</p>
            <div className="soon">Fase 5</div>
          </article>
        </section>
      </div>
    </main>
  );
}
