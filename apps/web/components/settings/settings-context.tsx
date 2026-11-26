"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import {
  ApiError,
  getMe,
  getTenantSettings,
  updateTenantSettings,
  type Me,
  type TenantSettings,
  type TenantSettingsUpdate,
} from "@/lib/api";

type SettingsContextValue = {
  me: Me | null;
  settings: TenantSettings | null;
  loading: boolean;
  saving: boolean;
  error: string | null;
  notice: string | null;
  save: (changes: TenantSettingsUpdate) => Promise<TenantSettings | null>;
  setError: (value: string | null) => void;
};

const SettingsContext = createContext<SettingsContextValue | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<Me | null>(null);
  const [settings, setSettings] = useState<TenantSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getMe()
      .then(async (user) => {
        if (!active) return;
        setMe(user);
        if (user.role !== "OWNER" && user.role !== "ADMIN") return;
        const data = await getTenantSettings();
        if (active) setSettings(data);
      })
      .catch((err) => {
        if (!active) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "Falha ao carregar configurações.",
        );
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const save = useCallback(
    async (changes: TenantSettingsUpdate) => {
      setSaving(true);
      setError(null);
      setNotice(null);
      try {
        const saved = await updateTenantSettings(changes);
        setSettings(saved);
        setNotice("Configurações salvas.");
        window.dispatchEvent(
          new CustomEvent<string>("sora-theme", {
            detail: saved.theme_primary_color,
          }),
        );
        return saved;
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Falha ao salvar configurações.",
        );
        return null;
      } finally {
        setSaving(false);
      }
    },
    [],
  );

  return (
    <SettingsContext.Provider
      value={{
        me,
        settings,
        loading,
        saving,
        error,
        notice,
        save,
        setError,
      }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const value = useContext(SettingsContext);
  if (!value) {
    throw new Error("useSettings deve ser usado dentro de SettingsProvider");
  }
  return value;
}
