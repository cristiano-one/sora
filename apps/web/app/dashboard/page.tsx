"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AppShell } from "@/components/app-shell";
import {
  getAccountBalances,
  getAiSummary,
  getAppointments,
  getCashFlow,
  getClients,
  getMe,
  getMyCommission,
  type AccountBalance,
  type AiSummary,
  type Appointment,
  type CashFlow,
  type Me,
} from "@/lib/api";
import { todayInTenant } from "@/lib/agenda";
import { sumMoney } from "@/lib/finance";
import { formatPrice } from "@/lib/public";

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

export default function DashboardPage() {
  const today = todayInTenant();
  const monthStart = `${today.slice(0, 7)}-01`;
  const [me, setMe] = useState<Me | null>(null);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [clientsCount, setClientsCount] = useState<number | null>(null);
  const [commission, setCommission] = useState("0.00");
  const [aiSummary, setAiSummary] = useState<AiSummary | null>(null);
  const [cashFlow, setCashFlow] = useState<CashFlow | null>(null);
  const [balances, setBalances] = useState<AccountBalance[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    async function load() {
      try {
        const [user, agenda, clients, mine] = await Promise.all([
          getMe(),
          getAppointments(today),
          getClients(),
          getMyCommission(monthStart, today),
        ]);
        if (!active) return;
        setMe(user);
        setAppointments(agenda);
        setClientsCount(clients.length);
        setCommission(mine.total);

        if (user.role === "OWNER" || user.role === "ADMIN") {
          const summary = await getAiSummary();
          if (active) setAiSummary(summary);
        }
        if (user.role === "OWNER") {
          const [cash, accountBalances] = await Promise.all([
            getCashFlow(monthStart, today),
            getAccountBalances(),
          ]);
          if (!active) return;
          setCashFlow(cash);
          setBalances(accountBalances);
        }
      } catch {
        if (active) {
          setError("Não foi possível carregar o painel agora.");
        }
      }
    }
    void load();
    return () => {
      active = false;
    };
  }, [monthStart, today]);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const isOwner = me?.role === "OWNER";
  const completed = appointments.filter(
    (item) => item.status === "COMPLETED",
  ).length;
  const pending = appointments.filter((item) =>
    ["SCHEDULED", "CONFIRMED", "PENDING_DEPOSIT"].includes(item.status),
  ).length;
  const totalBalance = sumMoney(balances.map((account) => account.balance));

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

        {error ? <p className="error">{error}</p> : null}

        <section className="stats">
          <article className="stat">
            <div className="stat-label">Agenda de hoje</div>
            <div className="stat-value">{appointments.length}</div>
            <div className="stat-note">
              {pending} em aberto · {completed} concluído(s)
            </div>
          </article>
          <article className="stat">
            <div className="stat-label">Clientes</div>
            <div className="stat-value">{clientsCount ?? "…"}</div>
            <div className="stat-note">Base ativa da clínica</div>
          </article>
          <article className="stat">
            <div className="stat-label">Minha comissão</div>
            <div className="stat-value">{formatPrice(commission)}</div>
            <div className="stat-note">Atendimentos concluídos no mês</div>
          </article>
          {isManager ? (
            <article className="stat">
              <div className="stat-label">Conversas SORA IA</div>
              <div className="stat-value">
                {aiSummary?.open_conversations ?? "…"}
              </div>
              <div className="stat-note">
                {aiSummary?.messages_today ?? 0} mensagem(ns) hoje
              </div>
            </article>
          ) : null}
          {isOwner ? (
            <>
              <article className="stat">
                <div className="stat-label">Entradas no mês</div>
                <div className="stat-value">
                  {cashFlow ? formatPrice(cashFlow.inflows) : "…"}
                </div>
                <div className="stat-note">
                  Caixa realizado até {today}
                </div>
              </article>
              <article className="stat">
                <div className="stat-label">Saldo em contas</div>
                <div className="stat-value">{formatPrice(totalBalance)}</div>
                <div className="stat-note">
                  {balances.length} conta(s)/caixa(s)
                </div>
              </article>
            </>
          ) : null}
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
          <Link href="/minha-comissao" className="panel panel-link">
            <h2>Minha comissão</h2>
            <p>
              Seus atendimentos concluídos, receita atendida e comissão do
              período.
            </p>
            <div className="soon">Ver comissão →</div>
          </Link>
          {isManager ? (
            <>
              <Link href="/catalogo" className="panel panel-link">
                <h2>Catálogo</h2>
                <p>
                  Serviços, pacotes, duração, buffer, custo de insumo e regra de
                  sinal.
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
              <Link href="/assinaturas/assinantes" className="panel panel-link">
                <h2>Assinaturas</h2>
                <p>
                  Clubes de recorrência, cotas e assinantes ativos da clínica.
                </p>
                <div className="soon">Abrir assinaturas →</div>
              </Link>
              <Link href="/sora-ia" className="panel panel-link">
                <h2>SORA IA</h2>
                <p>
                  Resumo diário, conversas do WhatsApp e atendimento humano.
                </p>
                <div className="soon">Abrir central →</div>
              </Link>
              {isOwner ? (
                <Link
                  href="/financeiro/fluxo-caixa"
                  className="panel panel-link"
                >
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
                  Tema da clínica, score mínimo, sinal e identidade do agente.
                </p>
                <div className="soon">Abrir configurações →</div>
              </Link>
            </>
          ) : null}
        </section>
      </div>
    </AppShell>
  );
}
