"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  getMe,
  getTenantExport,
  getTenantSettings,
  updateTenantSettings,
  type Me,
} from "@/lib/api";
import { profileOption } from "@/lib/profiles";

export default function SettingsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [threshold, setThreshold] = useState("");
  const [depositAmount, setDepositAmount] = useState("");
  const [themeColor, setThemeColor] = useState("#4f46e5");
  const [agentName, setAgentName] = useState("Sora");
  const [agentTone, setAgentTone] = useState("acolhedor");
  const [agentWelcome, setAgentWelcome] = useState("");
  const [agentKnowledge, setAgentKnowledge] = useState("");
  const [agentCancellation, setAgentCancellation] = useState("");
  const [agentAddress, setAgentAddress] = useState("");
  const [agentUpsell, setAgentUpsell] = useState("");
  const [enableTithe, setEnableTithe] = useState(false);
  const [tithePercentage, setTithePercentage] = useState("10.00");
  const [offeringAmount, setOfferingAmount] = useState("0.00");
  const [birthdayCredit, setBirthdayCredit] = useState("0.00");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const isOwner = me?.role === "OWNER";

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getTenantSettings()])
      .then(([user, data]) => {
        if (!active) return;
        setMe(user);
        setThreshold(
          data.deposit_score_threshold === null
            ? ""
            : String(data.deposit_score_threshold),
        );
        setDepositAmount(data.deposit_amount_low_score ?? "");
        setThemeColor(data.theme_primary_color);
        setAgentName(data.agent_name);
        setAgentTone(data.agent_tone);
        setAgentWelcome(data.agent_welcome_message ?? "");
        setAgentKnowledge(data.agent_knowledge ?? "");
        setAgentCancellation(data.agent_cancellation_policy ?? "");
        setAgentAddress(data.agent_address_info ?? "");
        setAgentUpsell(data.agent_upsell ?? "");
        setEnableTithe(data.enable_tithe_and_offering);
        setTithePercentage(data.tithe_percentage);
        setOfferingAmount(data.offering_amount);
        setBirthdayCredit(data.birthday_credit_amount);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Falha ao carregar configurações.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      const saved = await updateTenantSettings({
        deposit_score_threshold:
          threshold.trim() === "" ? null : Number(threshold),
        deposit_amount_low_score:
          depositAmount.trim() === "" ? null : depositAmount.trim(),
        theme_primary_color: themeColor,
        agent_name: agentName.trim(),
        agent_tone: agentTone,
        agent_welcome_message: agentWelcome.trim() || null,
        agent_knowledge: agentKnowledge.trim() || null,
        agent_cancellation_policy: agentCancellation.trim() || null,
        agent_address_info: agentAddress.trim() || null,
        agent_upsell: agentUpsell.trim() || null,
        enable_tithe_and_offering: enableTithe,
        tithe_percentage: tithePercentage,
        offering_amount: offeringAmount,
        birthday_credit_amount: birthdayCredit,
      });
      setThreshold(
        saved.deposit_score_threshold === null
          ? ""
          : String(saved.deposit_score_threshold),
      );
      setDepositAmount(saved.deposit_amount_low_score ?? "");
      setThemeColor(saved.theme_primary_color);
      setAgentName(saved.agent_name);
      setAgentTone(saved.agent_tone);
      setAgentWelcome(saved.agent_welcome_message ?? "");
      setAgentKnowledge(saved.agent_knowledge ?? "");
      setAgentCancellation(saved.agent_cancellation_policy ?? "");
      setAgentAddress(saved.agent_address_info ?? "");
      setAgentUpsell(saved.agent_upsell ?? "");
      setEnableTithe(saved.enable_tithe_and_offering);
      setTithePercentage(saved.tithe_percentage);
      setOfferingAmount(saved.offering_amount);
      setBirthdayCredit(saved.birthday_credit_amount);
      setNotice("Configurações salvas.");
      window.dispatchEvent(
        new CustomEvent<string>("sora-theme", {
          detail: saved.theme_primary_color,
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao salvar configurações.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    setError(null);
    setNotice(null);
    try {
      const data = await getTenantExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json;charset=utf-8",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sora-dados-${new Date().toISOString().slice(0, 10)}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setNotice("Exportação LGPD gerada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao exportar dados.",
      );
    }
  }

  if (!isManager && me) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">Apenas dono ou administrador acessa esta área.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Configurações</h1>
            <p>
              Tema da clínica, score mínimo para sinal e identidade do agente.
            </p>
          </div>
          {isOwner ? (
            <div className="page-actions">
              <button
                className="button button-ghost button-small"
                type="button"
                onClick={handleExport}
              >
                Exportar dados (LGPD)
              </button>
            </div>
          ) : null}
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me ? (
          <p className="muted-small">
            Perfil do negócio:{" "}
            <strong>{profileOption(me.business_profile).label}</strong>{" "}
            (definido pelo administrador do sistema).
          </p>
        ) : null}

        <div className="admin-grid">
          <section className="panel">
            <div className="panel-title">
              <h2>Sinal por score</h2>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : (
              <form onSubmit={handleSubmit}>
                <p className="subtitle">
                  Se o score do cliente ficar abaixo do limite, o agendamento
                  passa a exigir sinal. O motivo nunca é revelado ao cliente.
                </p>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="score-threshold">
                      Score mínimo (vazio = desativado)
                    </label>
                    <input
                      id="score-threshold"
                      type="number"
                      min={0}
                      max={100}
                      value={threshold}
                      onChange={(event) => setThreshold(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="score-deposit">Valor do sinal (R$)</label>
                    <input
                      id="score-deposit"
                      value={depositAmount}
                      onChange={(event) =>
                        setDepositAmount(event.target.value)
                      }
                      placeholder="50.00"
                    />
                  </div>
                </div>

                <div className="panel-title theme-title">
                  <h2>Dízimo e oferta</h2>
                </div>
                <div className="checkbox-field">
                  <input
                    id="enable-tithe"
                    type="checkbox"
                    checked={enableTithe}
                    onChange={(event) => setEnableTithe(event.target.checked)}
                  />
                  <label htmlFor="enable-tithe">
                    Ativar provisão de dízimo e oferta na DRE
                  </label>
                </div>
                {enableTithe ? (
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="tithe-percentage">Dízimo (%)</label>
                      <input
                        id="tithe-percentage"
                        value={tithePercentage}
                        onChange={(event) =>
                          setTithePercentage(event.target.value)
                        }
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="offering-amount">Oferta (R$)</label>
                      <input
                        id="offering-amount"
                        value={offeringAmount}
                        onChange={(event) =>
                          setOfferingAmount(event.target.value)
                        }
                      />
                    </div>
                  </div>
                ) : null}

                <div className="panel-title theme-title">
                  <h2>Crédito de aniversário</h2>
                </div>
                <div className="field">
                  <label htmlFor="birthday-credit">
                    Valor do crédito (R$ · 0 desativa)
                  </label>
                  <input
                    id="birthday-credit"
                    value={birthdayCredit}
                    onChange={(event) => setBirthdayCredit(event.target.value)}
                  />
                </div>
                <p className="muted-small">
                  A SORA IA gera o crédito 7 dias antes do aniversário, uma vez
                  por ano, com validade de 30 dias.
                </p>

                <div className="panel-title theme-title">
                  <h2>Tema e identidade</h2>
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="theme-color">Cor primária</label>
                    <div className="color-field">
                      <input
                        id="theme-color"
                        type="color"
                        value={themeColor}
                        onChange={(event) => setThemeColor(event.target.value)}
                      />
                      <input
                        aria-label="Código da cor"
                        value={themeColor}
                        onChange={(event) => setThemeColor(event.target.value)}
                        maxLength={7}
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label htmlFor="agent-name">Nome do agente</label>
                    <input
                      id="agent-name"
                      value={agentName}
                      onChange={(event) => setAgentName(event.target.value)}
                      maxLength={100}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="agent-tone">Tom de voz</label>
                    <select
                      id="agent-tone"
                      value={agentTone}
                      onChange={(event) => setAgentTone(event.target.value)}
                    >
                      <option value="acolhedor">Acolhedor</option>
                      <option value="formal">Formal</option>
                      <option value="descontraido">Descontraído</option>
                      <option value="direto">Direto e objetivo</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="agent-welcome">Saudação personalizada</label>
                    <textarea
                      id="agent-welcome"
                      value={agentWelcome}
                      onChange={(event) => setAgentWelcome(event.target.value)}
                      rows={3}
                      maxLength={3000}
                      placeholder="Ex.: Oi! Aqui é a Bia do Studio. Como posso ajudar?"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="agent-knowledge">
                      Base de conhecimento e regras
                    </label>
                    <textarea
                      id="agent-knowledge"
                      value={agentKnowledge}
                      onChange={(event) =>
                        setAgentKnowledge(event.target.value)
                      }
                      rows={4}
                      maxLength={5000}
                      placeholder="Endereço, serviços, convênios, observações do negócio…"
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="agent-cancellation">
                      Política de cancelamento e atraso
                    </label>
                    <textarea
                      id="agent-cancellation"
                      value={agentCancellation}
                      onChange={(event) =>
                        setAgentCancellation(event.target.value)
                      }
                      rows={3}
                      maxLength={3000}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="agent-address">
                      Endereço e estacionamento
                    </label>
                    <textarea
                      id="agent-address"
                      value={agentAddress}
                      onChange={(event) => setAgentAddress(event.target.value)}
                      rows={3}
                      maxLength={3000}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="agent-upsell">Sugestão de upsell</label>
                    <textarea
                      id="agent-upsell"
                      value={agentUpsell}
                      onChange={(event) => setAgentUpsell(event.target.value)}
                      rows={2}
                      maxLength={1000}
                      placeholder="Ex.: Ao agendar corte, sugerir hidratação."
                    />
                  </div>
                </div>

                <button className="button" type="submit" disabled={saving}>
                  {saving ? "Salvando…" : "Salvar configurações"}
                </button>
              </form>
            )}
          </section>

          <section className="panel">
            <div className="panel-title">
              <h2>Prévia do tema</h2>
            </div>
            <div
              className="theme-preview"
              style={{ background: themeColor }}
            >
              <span>Sora Studio</span>
              <strong>Agende seu horário</strong>
              <small>O tema também é aplicado ao link público.</small>
            </div>
            <p className="muted-small theme-note">
              O agente é usado nas mensagens da SORA IA quando o canal for
              ativado.
            </p>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
