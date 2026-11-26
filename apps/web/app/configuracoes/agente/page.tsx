"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function AgentSettingsPage() {
  const { settings, saving, error, notice, save } = useSettings();
  const [agentName, setAgentName] = useState("Sora");
  const [agentTone, setAgentTone] = useState("acolhedor");
  const [agentWelcome, setAgentWelcome] = useState("");
  const [agentKnowledge, setAgentKnowledge] = useState("");
  const [agentCancellation, setAgentCancellation] = useState("");
  const [agentAddress, setAgentAddress] = useState("");
  const [agentUpsell, setAgentUpsell] = useState("");

  useEffect(() => {
    if (!settings) return;
    setAgentName(settings.agent_name);
    setAgentTone(settings.agent_tone);
    setAgentWelcome(settings.agent_welcome_message ?? "");
    setAgentKnowledge(settings.agent_knowledge ?? "");
    setAgentCancellation(settings.agent_cancellation_policy ?? "");
    setAgentAddress(settings.agent_address_info ?? "");
    setAgentUpsell(settings.agent_upsell ?? "");
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({
      agent_name: agentName.trim(),
      agent_tone: agentTone,
      agent_welcome_message: agentWelcome.trim() || null,
      agent_knowledge: agentKnowledge.trim() || null,
      agent_cancellation_policy: agentCancellation.trim() || null,
      agent_address_info: agentAddress.trim() || null,
      agent_upsell: agentUpsell.trim() || null,
    });
  }

  if (!settings) {
    return (
      <div className="page">
        <p className={error ? "error" : "table-empty"}>
          {error ?? "Carregando configurações…"}
        </p>
      </div>
    );
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Agente SORA IA</h1>
          <p>
            Nome, tom de voz, saudação, políticas e informações usadas nas
            respostas do atendente virtual.
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <section className="panel">
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="agent-name">Nome do agente</label>
              <input
                id="agent-name"
                value={agentName}
                onChange={(event) => setAgentName(event.target.value)}
                maxLength={100}
                required
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
            <label htmlFor="agent-knowledge">Base de conhecimento e regras</label>
            <textarea
              id="agent-knowledge"
              value={agentKnowledge}
              onChange={(event) => setAgentKnowledge(event.target.value)}
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
              onChange={(event) => setAgentCancellation(event.target.value)}
              rows={3}
              maxLength={3000}
            />
          </div>
          <div className="field">
            <label htmlFor="agent-address">Endereço e estacionamento</label>
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

          <button className="button" type="submit" disabled={saving}>
            {saving ? "Salvando…" : "Salvar agente"}
          </button>
        </form>
      </section>
    </div>
  );
}
