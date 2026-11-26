"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";
import {
  ApiError,
  testAiProvider,
  type AiProviderTestResult,
  type TenantSettingsUpdate,
} from "@/lib/api";

export default function AgentSettingsPage() {
  const { settings, saving, error, notice, save, me } = useSettings();
  const [agentName, setAgentName] = useState("Sora");
  const [agentTone, setAgentTone] = useState("acolhedor");
  const [agentWelcome, setAgentWelcome] = useState("");
  const [agentKnowledge, setAgentKnowledge] = useState("");
  const [agentCancellation, setAgentCancellation] = useState("");
  const [agentAddress, setAgentAddress] = useState("");
  const [agentUpsell, setAgentUpsell] = useState("");
  const [aiProvider, setAiProvider] = useState<"mock" | "groq">("mock");
  const [aiModel, setAiModel] = useState("llama-3.3-70b-versatile");
  const [aiKey, setAiKey] = useState("");
  const [clearKey, setClearKey] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<AiProviderTestResult | null>(
    null,
  );
  const [testError, setTestError] = useState<string | null>(null);
  const isOwner = me?.role === "OWNER";

  useEffect(() => {
    if (!settings) return;
    setAgentName(settings.agent_name);
    setAgentTone(settings.agent_tone);
    setAgentWelcome(settings.agent_welcome_message ?? "");
    setAgentKnowledge(settings.agent_knowledge ?? "");
    setAgentCancellation(settings.agent_cancellation_policy ?? "");
    setAgentAddress(settings.agent_address_info ?? "");
    setAgentUpsell(settings.agent_upsell ?? "");
    setAiProvider(settings.ai_provider);
    setAiModel(settings.ai_model);
    setAiKey("");
    setClearKey(false);
    setTestResult(null);
    setTestError(null);
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const changes: TenantSettingsUpdate = {
      agent_name: agentName.trim(),
      agent_tone: agentTone,
      agent_welcome_message: agentWelcome.trim() || null,
      agent_knowledge: agentKnowledge.trim() || null,
      agent_cancellation_policy: agentCancellation.trim() || null,
      agent_address_info: agentAddress.trim() || null,
      agent_upsell: agentUpsell.trim() || null,
    };
    if (isOwner) {
      changes.ai_model = aiModel.trim();
      if (clearKey) {
        changes.ai_provider = "mock";
        changes.clear_ai_api_key = true;
      } else {
        changes.ai_provider = aiProvider;
        if (aiKey.trim()) changes.ai_api_key = aiKey.trim();
      }
    }
    const saved = await save(changes);
    if (saved) {
      setAiKey("");
      setClearKey(false);
    }
  }

  async function handleTestProvider() {
    setTesting(true);
    setTestResult(null);
    setTestError(null);
    try {
      setTestResult(await testAiProvider());
    } catch (err) {
      setTestError(
        err instanceof ApiError
          ? err.message
          : "Falha ao testar a conexão com a Groq.",
      );
    } finally {
      setTesting(false);
    }
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
            respostas do atendente virtual, além do provedor de IA.
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <section className="panel">
        <form onSubmit={handleSubmit}>
          <div className="panel-title">
            <div>
              <h2>Provedor de IA</h2>
              <span className="muted-small">
                A Groq reescreve a resposta; preços, links e privacidade
                continuam no motor determinístico da Sora.
              </span>
            </div>
            <span
              className={`pill ${
                aiProvider === "groq" ? "pill-active" : "pill-muted"
              }`}
            >
              {aiProvider === "groq" ? "groq" : "determinístico"}
            </span>
          </div>

          {!isOwner ? (
            <p className="muted-small">
              Somente o proprietário pode alterar o provedor e a chave de IA.
            </p>
          ) : null}

          <div className="form-grid">
            <div className="field">
              <label htmlFor="ai-provider">Provedor</label>
              <select
                id="ai-provider"
                value={aiProvider}
                onChange={(event) =>
                  setAiProvider(event.target.value as "mock" | "groq")
                }
                disabled={!isOwner}
              >
                <option value="mock">Determinístico (sem custo)</option>
                <option value="groq">Groq</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="ai-model">Modelo</label>
              <input
                id="ai-model"
                value={aiModel}
                onChange={(event) => setAiModel(event.target.value)}
                placeholder="llama-3.3-70b-versatile"
                maxLength={100}
                disabled={!isOwner || aiProvider === "mock"}
              />
            </div>
          </div>

          {aiProvider === "groq" ? (
            <>
              <div className="field">
                <label htmlFor="ai-key">Chave da Groq</label>
                <input
                  id="ai-key"
                  type="password"
                  value={aiKey}
                  onChange={(event) => setAiKey(event.target.value)}
                  placeholder={
                    settings.ai_key_configured
                      ? "•••••••• (chave salva)"
                      : "gsk_..."
                  }
                  maxLength={300}
                  autoComplete="new-password"
                  disabled={!isOwner}
                />
                <span className="muted-small">
                  A chave fica cifrada no banco e nunca é retornada pela API.
                  A mensagem do cliente é enviada à Groq; use com base legal
                  de tratamento de dados.
                </span>
              </div>
              <div className="whatsapp-actions">
                <button
                  className="button"
                  type="button"
                  onClick={handleTestProvider}
                  disabled={
                    testing || !isOwner || !settings.ai_key_configured
                  }
                >
                  {testing ? "Testando…" : "Testar conexão"}
                </button>
                {settings.ai_key_configured ? (
                  <label className="checkbox-line">
                    <input
                      type="checkbox"
                      checked={clearKey}
                      onChange={(event) => {
                        setClearKey(event.target.checked);
                        if (event.target.checked) setAiProvider("mock");
                      }}
                      disabled={!isOwner}
                    />
                    Remover chave salva
                  </label>
                ) : null}
              </div>
              {!settings.ai_key_configured ? (
                <p className="muted-small">
                  Salve a chave antes de testar a conexão.
                </p>
              ) : null}
              {testResult ? (
                <p className="public-notice">
                  Groq OK · {testResult.model} · {testResult.latency_ms} ms ·
                  resposta “{testResult.reply}”
                </p>
              ) : null}
              {testError ? <p className="error">{testError}</p> : null}
            </>
          ) : (
            <>
              <p className="muted-small">
                Modo sem custo: respostas determinísticas, sem enviar dados a
                provedores externos.
              </p>
              {settings.ai_key_configured ? (
                <label className="checkbox-line">
                  <input
                    type="checkbox"
                    checked={clearKey}
                    onChange={(event) => setClearKey(event.target.checked)}
                    disabled={!isOwner}
                  />
                  Remover chave da Groq salva
                </label>
              ) : null}
            </>
          )}

          <hr className="settings-divider" />

          <div className="panel-title">
            <div>
              <h2>Persona e conhecimento</h2>
              <span className="muted-small">
                Usados tanto no modo determinístico quanto na Groq.
              </span>
            </div>
          </div>

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
            {saving ? "Salvando…" : "Salvar agente e IA"}
          </button>
        </form>
      </section>
    </div>
  );
}
