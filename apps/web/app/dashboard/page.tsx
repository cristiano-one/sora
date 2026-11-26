"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import { getMe, type Me } from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

export default function DashboardPage() {
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    let active = true;
    getMe()
      .then((data) => {
        if (active) setMe(data);
      })
      .catch(() => {
        // O AppShell redireciona para o login em caso de sessão inválida.
      });
    return () => {
      active = false;
    };
  }, []);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const isOwner = me?.role === "OWNER";

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            {me ? (
              <span className="badge">{ROLE_LABEL[me.role] ?? me.role}</span>
            ) : null}
            <h1>Olá, {me ? me.full_name.split(" ")[0] : "bem-vindo"} 👋</h1>
            <p>Visão geral da clínica, operação e gestão em um só lugar.</p>
          </div>
        </header>

        <section className="stats">
          <article className="stat">
            <div className="stat-label">Clínica</div>
            <div className="stat-value">
              {me ? `${me.tenant_id.slice(0, 8)}…` : "…"}
            </div>
            <div className="stat-note">Tenant vinculado ao seu login</div>
          </article>
          <article className="stat">
            <div className="stat-label">Perfil</div>
            <div className="stat-value">
              {me ? ROLE_LABEL[me.role] ?? me.role : "…"}
            </div>
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
              Board do dia, disponibilidade em tempo real e anti-conflito com
              tag de assinante.
            </p>
            <div className="soon">Abrir agenda →</div>
          </Link>
          <Link href="/clientes" className="panel panel-link">
            <h2>Clientes &amp; Score</h2>
            <p>
              Cadastro, score confidencial, bloqueio e histórico de
              relacionamento.
            </p>
            <div className="soon">Abrir clientes →</div>
          </Link>
          {isManager ? (
            <>
              <Link href="/catalogo" className="panel panel-link">
                <h2>Catálogo</h2>
                <p>
                  Serviços, duração, buffer, custo de insumo e regra de sinal.
                </p>
                <div className="soon">Abrir catálogo →</div>
              </Link>
              <Link href="/equipe" className="panel panel-link">
                <h2>Equipe &amp; Comissões</h2>
                <p>
                  Colaboradores, papéis e regras de comissão por atendimento.
                </p>
                <div className="soon">Abrir equipe →</div>
              </Link>
              <Link href="/assinaturas" className="panel panel-link">
                <h2>Assinaturas</h2>
                <p>
                  Clubes de recorrência, cotas e assinantes ativos da clínica.
                </p>
                <div className="soon">Abrir assinaturas →</div>
              </Link>
              {isOwner ? (
                <Link href="/financeiro" className="panel panel-link">
                  <h2>Financeiro</h2>
                  <p>
                    Caixa, DRE por competência, comissões, saldos e exportação.
                  </p>
                  <div className="soon">Abrir financeiro →</div>
                </Link>
              ) : null}
              <Link href="/configuracoes" className="panel panel-link">
                <h2>Configurações</h2>
                <p>
                  Tema da clínica, score mínimo e valor do sinal para score
                  baixo.
                </p>
                <div className="soon">Abrir configurações →</div>
              </Link>
            </>
          ) : null}
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
    </AppShell>
  );
}
