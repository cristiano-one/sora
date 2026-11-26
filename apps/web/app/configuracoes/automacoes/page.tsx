"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";
import {
  ApiError,
  getAutomationRules,
  getAutomationRuns,
  runAutomations,
  updateAutomationRule,
  type AutomationRule,
  type AutomationRun,
  type AutomationTrigger,
} from "@/lib/api";
import { formatIsoDate, formatTime } from "@/lib/agenda";

const TRIGGER_LABEL: Record<AutomationTrigger, string> = {
  BOOKING_CONFIRMATION: "Confirmação imediata",
  REMINDER_24H: "Lembrete 24h",
  REMINDER_2H: "Lembrete 2h",
  POST_SERVICE: "Pós-atendimento",
  WINBACK_60D: "Recuperação 60 dias",
  BIRTHDAY: "Aniversário",
};

const STATUS_LABEL: Record<AutomationRun["status"], string> = {
  PENDING: "Pendente",
  SENT: "Enviado",
  SKIPPED: "Ignorado",
  FAILED: "Falhou",
};

type RuleDraft = {
  template: string;
  is_active: boolean;
};

export default function AutomationSettingsPage() {
  const { settings, saving, error, notice, save, setError } = useSettings();
  const [birthdayCredit, setBirthdayCredit] = useState("0.00");
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [drafts, setDrafts] = useState<Record<string, RuleDraft>>({});
  const [runs, setRuns] = useState<AutomationRun[]>([]);
  const [loadingRules, setLoadingRules] = useState(true);
  const [ruleBusy, setRuleBusy] = useState<string | null>(null);
  const [runBusy, setRunBusy] = useState(false);
  const [runNotice, setRunNotice] = useState<string | null>(null);

  useEffect(() => {
    if (settings) setBirthdayCredit(settings.birthday_credit_amount);
  }, [settings]);

  const loadAutomations = useCallback(async () => {
    setLoadingRules(true);
    try {
      const [ruleData, runData] = await Promise.all([
        getAutomationRules(),
        getAutomationRuns(),
      ]);
      setRules(ruleData);
      setRuns(runData);
      setDrafts(
        Object.fromEntries(
          ruleData.map((rule) => [
            rule.id,
            { template: rule.template, is_active: rule.is_active },
          ]),
        ),
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao carregar automações.",
      );
    } finally {
      setLoadingRules(false);
    }
  }, [setError]);

  useEffect(() => {
    void loadAutomations();
  }, [loadAutomations]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({ birthday_credit_amount: birthdayCredit });
  }

  async function handleSaveRule(rule: AutomationRule) {
    const draft = drafts[rule.id];
    if (!draft) return;
    setRuleBusy(rule.id);
    setRunNotice(null);
    setError(null);
    try {
      const updated = await updateAutomationRule(rule.id, {
        template: draft.template,
        is_active: draft.is_active,
      });
      setRules((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setRunNotice(`Automação "${updated.name}" salva.`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar automação.",
      );
    } finally {
      setRuleBusy(null);
    }
  }

  async function handleRun() {
    setRunBusy(true);
    setRunNotice(null);
    setError(null);
    try {
      const result = await runAutomations();
      await loadAutomations();
      setRunNotice(
        `${result.processed} processada(s): ${result.sent} enviada(s), ` +
          `${result.failed} falha(s), ${result.skipped} ignorada(s).`,
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao executar automações.",
      );
    } finally {
      setRunBusy(false);
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

  const ruleNames = new Map(rules.map((rule) => [rule.id, rule.name]));

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Automações</h1>
          <p>
            Confirmações, lembretes, pós-atendimento e recuperação de clientes
            pelo WhatsApp.
          </p>
        </div>
        <div className="page-actions">
          <button
            className="button button-ghost button-small"
            type="button"
            onClick={() => loadAutomations()}
          >
            Atualizar
          </button>
          <button
            className="button button-small"
            type="button"
            disabled={runBusy}
            onClick={handleRun}
          >
            {runBusy ? "Executando…" : "Executar agora"}
          </button>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}
      {runNotice ? <p className="public-notice">{runNotice}</p> : null}

      <section className="panel">
        <div className="panel-title">
          <h2>Réguas de relacionamento</h2>
          <span className="muted-small">WhatsApp</span>
        </div>
        {loadingRules ? (
          <p className="table-empty">Carregando réguas…</p>
        ) : (
          <div className="automation-rules">
            {rules.map((rule) => {
              const draft = drafts[rule.id] ?? {
                template: rule.template,
                is_active: rule.is_active,
              };
              return (
                <article className="automation-rule" key={rule.id}>
                  <div className="automation-rule-head">
                    <div>
                      <span className="landing-tag">
                        {TRIGGER_LABEL[rule.trigger]}
                      </span>
                      <h3>{rule.name}</h3>
                    </div>
                    <label className="automation-switch">
                      <input
                        type="checkbox"
                        checked={draft.is_active}
                        onChange={(event) =>
                          setDrafts((current) => ({
                            ...current,
                            [rule.id]: {
                              ...draft,
                              is_active: event.target.checked,
                            },
                          }))
                        }
                      />
                      <span>{draft.is_active ? "Ativa" : "Inativa"}</span>
                    </label>
                  </div>
                  <textarea
                    value={draft.template}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [rule.id]: {
                          ...draft,
                          template: event.target.value,
                        },
                      }))
                    }
                    rows={3}
                    maxLength={4000}
                  />
                  <div className="automation-rule-foot">
                    <span className="muted-small">
                      Variáveis: {"{first_name}"}, {"{client_name}"},{" "}
                      {"{service}"}, {"{date}"}, {"{time}"},{" "}
                      {"{collaborator}"}
                    </span>
                    <button
                      className="button button-small"
                      type="button"
                      disabled={ruleBusy === rule.id}
                      onClick={() => handleSaveRule(rule)}
                    >
                      {ruleBusy === rule.id ? "Salvando…" : "Salvar régua"}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section className="panel section-gap">
        <div className="panel-title">
          <h2>Execuções recentes</h2>
          <span className="muted-small">{runs.length}</span>
        </div>
        {runs.length === 0 ? (
          <p className="table-empty">Nenhuma execução registrada.</p>
        ) : (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Régua</th>
                  <th>Agendada</th>
                  <th>Status</th>
                  <th>Enviada</th>
                  <th>Erro</th>
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 20).map((run) => (
                  <tr key={run.id}>
                    <td>{ruleNames.get(run.rule_id) ?? "Régua"}</td>
                    <td>
                      {formatIsoDate(run.scheduled_for)}{" "}
                      {formatTime(run.scheduled_for)}
                    </td>
                    <td>
                      <span
                        className={`pill ${
                          run.status === "SENT"
                            ? "pill-active"
                            : run.status === "FAILED"
                              ? "pill-blocked"
                              : ""
                        }`}
                      >
                        {STATUS_LABEL[run.status]}
                      </span>
                    </td>
                    <td>
                      {run.sent_at
                        ? `${formatIsoDate(run.sent_at)} ${formatTime(run.sent_at)}`
                        : "—"}
                    </td>
                    <td>{run.error ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel section-gap">
        <div className="panel-title">
          <h2>Crédito de aniversário</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="birthday-credit">Valor do crédito (R$)</label>
            <input
              id="birthday-credit"
              inputMode="decimal"
              value={birthdayCredit}
              onChange={(event) => setBirthdayCredit(event.target.value)}
            />
          </div>
          <p className="muted-small">
            Zero desativa a geração. A geração roda 1x por ano por cliente e o
            crédito vale 30 dias.
          </p>
          <button className="button" type="submit" disabled={saving}>
            {saving ? "Salvando…" : "Salvar crédito"}
          </button>
        </form>
      </section>
    </div>
  );
}
