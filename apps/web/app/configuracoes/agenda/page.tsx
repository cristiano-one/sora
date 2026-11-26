"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function AgendaSettingsPage() {
  const { settings, saving, error, notice, save } = useSettings();
  const [threshold, setThreshold] = useState("");
  const [depositAmount, setDepositAmount] = useState("");

  useEffect(() => {
    if (!settings) return;
    setThreshold(
      settings.deposit_score_threshold === null
        ? ""
        : String(settings.deposit_score_threshold),
    );
    setDepositAmount(settings.deposit_amount_low_score ?? "");
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({
      deposit_score_threshold:
        threshold.trim() === "" ? null : Number(threshold),
      deposit_amount_low_score:
        depositAmount.trim() === "" ? null : depositAmount.trim(),
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
          <h1>Agenda &amp; score</h1>
          <p>
            Regras de sinal para clientes com score baixo. O motivo nunca é
            revelado ao cliente.
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <section className="panel">
        <div className="panel-title">
          <h2>Sinal por score</h2>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="score-threshold">Score mínimo</label>
              <input
                id="score-threshold"
                type="number"
                min={0}
                max={100}
                value={threshold}
                onChange={(event) => setThreshold(event.target.value)}
                placeholder="Ex.: 70"
              />
            </div>
            <div className="field">
              <label htmlFor="score-deposit">Sinal para score baixo (R$)</label>
              <input
                id="score-deposit"
                inputMode="decimal"
                value={depositAmount}
                onChange={(event) => setDepositAmount(event.target.value)}
                placeholder="Ex.: 50.00"
              />
            </div>
          </div>
          <p className="muted-small">
            Deixe os dois campos vazios para desativar a exigência por score.
            Serviços com sinal próprio continuam usando a regra do catálogo.
          </p>
          <button className="button" type="submit" disabled={saving}>
            {saving ? "Salvando…" : "Salvar agenda e score"}
          </button>
        </form>
      </section>
    </div>
  );
}
