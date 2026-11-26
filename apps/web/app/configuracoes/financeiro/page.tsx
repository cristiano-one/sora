"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function FinanceSettingsPage() {
  const { me, settings, saving, error, notice, save } = useSettings();
  const [enableTithe, setEnableTithe] = useState(false);
  const [tithePercentage, setTithePercentage] = useState("10.00");
  const [offeringAmount, setOfferingAmount] = useState("0.00");

  useEffect(() => {
    if (!settings) return;
    setEnableTithe(settings.enable_tithe_and_offering);
    setTithePercentage(settings.tithe_percentage);
    setOfferingAmount(settings.offering_amount);
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({
      enable_tithe_and_offering: enableTithe,
      tithe_percentage: tithePercentage,
      offering_amount: offeringAmount,
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
          <h1>Financeiro</h1>
          <p>
            Provisão opcional de dízimo e oferta exibida na DRE e no painel
            financeiro.
          </p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      {me?.role !== "OWNER" ? (
        <p className="error">
          A configuração de dízimo e oferta é exclusiva do dono/gestor.
        </p>
      ) : (
        <section className="panel">
          <div className="panel-title">
            <h2>Dízimo &amp; oferta</h2>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="checkbox-field">
              <input
                id="enable-tithe"
                type="checkbox"
                checked={enableTithe}
                onChange={(event) => setEnableTithe(event.target.checked)}
              />
              <label htmlFor="enable-tithe">
                Ativar controle de dízimo e oferta
              </label>
            </div>

            {enableTithe ? (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="tithe-percentage">Dízimo (%)</label>
                  <input
                    id="tithe-percentage"
                    inputMode="decimal"
                    value={tithePercentage}
                    onChange={(event) =>
                      setTithePercentage(event.target.value)
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="offering-amount">Oferta fixa (R$)</label>
                  <input
                    id="offering-amount"
                    inputMode="decimal"
                    value={offeringAmount}
                    onChange={(event) => setOfferingAmount(event.target.value)}
                  />
                </div>
              </div>
            ) : null}

            <p className="muted-small">
              A DRE só mostra as linhas de dízimo/oferta quando a flag estiver
              ativa. O card de entregas fica em Financeiro → Dízimo &amp; oferta.
            </p>
            <button className="button" type="submit" disabled={saving}>
              {saving ? "Salvando…" : "Salvar financeiro"}
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
