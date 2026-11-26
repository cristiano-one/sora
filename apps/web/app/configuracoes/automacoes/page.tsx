"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function AutomationSettingsPage() {
  const { settings, saving, error, notice, save } = useSettings();
  const [birthdayCredit, setBirthdayCredit] = useState("0.00");

  useEffect(() => {
    if (settings) setBirthdayCredit(settings.birthday_credit_amount);
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({ birthday_credit_amount: birthdayCredit });
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
          <h1>Automações</h1>
          <p>
            Crédito de aniversário para aniversariantes dos próximos 7 dias.
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <section className="panel">
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
            Zero desativa a geração de créditos. A geração roda 1x por ano por
            cliente e o crédito vale 30 dias. Use a central da SORA IA para
            gerar manualmente ou o worker agendado.
          </p>
          <button className="button" type="submit" disabled={saving}>
            {saving ? "Salvando…" : "Salvar automação"}
          </button>
        </form>
      </section>
    </div>
  );
}
