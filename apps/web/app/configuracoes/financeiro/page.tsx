"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function FinanceSettingsPage() {
  const { me, settings, saving, error, notice, save } = useSettings();
  const [enableTithe, setEnableTithe] = useState(false);
  const [tithePercentage, setTithePercentage] = useState("10.00");
  const [offeringAmount, setOfferingAmount] = useState("0.00");
  const [fiscalEnabled, setFiscalEnabled] = useState(false);
  const [fiscalProvider, setFiscalProvider] = useState("mock");
  const [fiscalMunicipality, setFiscalMunicipality] = useState("");
  const [fiscalServiceCode, setFiscalServiceCode] = useState("");
  const [fiscalEmail, setFiscalEmail] = useState("");

  useEffect(() => {
    if (!settings) return;
    setEnableTithe(settings.enable_tithe_and_offering);
    setTithePercentage(settings.tithe_percentage);
    setOfferingAmount(settings.offering_amount);
    setFiscalEnabled(settings.fiscal_enabled);
    setFiscalProvider(settings.fiscal_provider);
    setFiscalMunicipality(settings.fiscal_municipality ?? "");
    setFiscalServiceCode(settings.fiscal_service_code ?? "");
    setFiscalEmail(settings.fiscal_email ?? "");
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({
      enable_tithe_and_offering: enableTithe,
      tithe_percentage: tithePercentage,
      offering_amount: offeringAmount,
      fiscal_enabled: fiscalEnabled,
      fiscal_provider: fiscalProvider,
      fiscal_municipality: fiscalMunicipality.trim() || null,
      fiscal_service_code: fiscalServiceCode.trim() || null,
      fiscal_email: fiscalEmail.trim() || null,
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
            <div className="panel-title section-gap">
              <h2>NFS-e</h2>
            </div>
            <div className="checkbox-field">
              <input
                id="fiscal-enabled"
                type="checkbox"
                checked={fiscalEnabled}
                onChange={(event) => setFiscalEnabled(event.target.checked)}
              />
              <label htmlFor="fiscal-enabled">
                Habilitar emissão de NFS-e
              </label>
            </div>
            {fiscalEnabled ? (
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="fiscal-provider">Provedor</label>
                  <select
                    id="fiscal-provider"
                    value={fiscalProvider}
                    onChange={(event) => setFiscalProvider(event.target.value)}
                  >
                    <option value="mock">Mock (homologação)</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="fiscal-municipality">Município</label>
                  <input
                    id="fiscal-municipality"
                    value={fiscalMunicipality}
                    onChange={(event) =>
                      setFiscalMunicipality(event.target.value)
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="fiscal-service-code">Código do serviço</label>
                  <input
                    id="fiscal-service-code"
                    value={fiscalServiceCode}
                    onChange={(event) =>
                      setFiscalServiceCode(event.target.value)
                    }
                  />
                </div>
                <div className="field">
                  <label htmlFor="fiscal-email">E-mail fiscal</label>
                  <input
                    id="fiscal-email"
                    type="email"
                    value={fiscalEmail}
                    onChange={(event) => setFiscalEmail(event.target.value)}
                  />
                </div>
              </div>
            ) : null}
            <button className="button" type="submit" disabled={saving}>
              {saving ? "Salvando…" : "Salvar financeiro"}
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
