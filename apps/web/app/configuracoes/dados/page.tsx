"use client";

import { useState } from "react";

import { useSettings } from "@/components/settings/settings-context";
import { ApiError, getTenantExport } from "@/lib/api";
import { profileOption } from "@/lib/profiles";

export default function DataSettingsPage() {
  const { me, setError } = useSettings();
  const [exporting, setExporting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  async function handleExport() {
    setError(null);
    setNotice(null);
    setExporting(true);
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
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1>Dados &amp; LGPD</h1>
          <p>Perfil do negócio e portabilidade dos dados da clínica.</p>
        </div>
      </header>

      {notice ? <p className="public-notice">{notice}</p> : null}

      <div className="admin-grid">
        <section className="panel">
          <div className="panel-title">
            <h2>Perfil do negócio</h2>
          </div>
          <p>
            <span className="pill pill-active">
              {me ? profileOption(me.business_profile).label : "—"}
            </span>
          </p>
          <p className="muted-small">
            O perfil é definido pelo administrador do sistema no console master
            e controla os módulos clínicos exibidos.
          </p>
        </section>

        <section className="panel">
          <div className="panel-title">
            <h2>Portabilidade LGPD</h2>
          </div>
          <p className="subtitle">
            Baixe um JSON com clientes, agenda, financeiro, prontuários,
            consentimentos, créditos e catálogo.
          </p>
          {me?.role === "OWNER" ? (
            <button
              className="button"
              type="button"
              onClick={handleExport}
              disabled={exporting}
            >
              {exporting ? "Gerando…" : "Exportar dados (LGPD)"}
            </button>
          ) : (
            <p className="error">
              Exportação exclusiva do dono/gestor.
            </p>
          )}
        </section>
      </div>
    </div>
  );
}
