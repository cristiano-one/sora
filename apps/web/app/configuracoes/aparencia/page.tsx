"use client";

import { useEffect, useState, type FormEvent } from "react";

import { useSettings } from "@/components/settings/settings-context";

export default function AppearanceSettingsPage() {
  const { settings, saving, error, notice, save } = useSettings();
  const [themeColor, setThemeColor] = useState("#4f46e5");

  useEffect(() => {
    if (settings) setThemeColor(settings.theme_primary_color);
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await save({ theme_primary_color: themeColor });
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
          <h1>Aparência</h1>
          <p>Cor principal aplicada ao painel e ao link público da clínica.</p>
        </div>
      </header>

      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="public-notice">{notice}</p> : null}

      <div className="admin-grid">
        <section className="panel">
          <div className="panel-title">
            <h2>Tema do sistema</h2>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="theme-color">Cor primária</label>
              <div className="color-row">
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
            <button className="button" type="submit" disabled={saving}>
              {saving ? "Salvando…" : "Salvar aparência"}
            </button>
          </form>
        </section>

        <section className="panel">
          <div className="panel-title">
            <h2>Prévia</h2>
          </div>
          <div className="theme-preview" style={{ background: themeColor }}>
            <span>Sora Studio</span>
            <strong>Agende seu horário</strong>
            <small>O tema também é aplicado ao link público.</small>
          </div>
        </section>
      </div>
    </div>
  );
}
