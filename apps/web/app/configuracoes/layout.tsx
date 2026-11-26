"use client";

import type { ReactNode } from "react";

import { AppShell } from "@/components/app-shell";
import {
  SettingsProvider,
  useSettings,
} from "@/components/settings/settings-context";

function SettingsLayoutInner({ children }: { children: ReactNode }) {
  const { me, loading } = useSettings();
  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  if (loading || !me) {
    return (
      <AppShell>
        <div className="page">
          <p className="table-empty">Carregando configurações…</p>
        </div>
      </AppShell>
    );
  }

  if (!isManager) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">
            Acesso restrito a gestores e administradores.
          </p>
        </div>
      </AppShell>
    );
  }

  return <AppShell>{children}</AppShell>;
}

export default function SettingsLayout({ children }: { children: ReactNode }) {
  return (
    <SettingsProvider>
      <SettingsLayoutInner>{children}</SettingsLayoutInner>
    </SettingsProvider>
  );
}
