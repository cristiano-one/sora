import type { BusinessProfile } from "./profiles";

export type SystemTenant = {
  id: string;
  name: string;
  slug: string;
  tax_regime: "MEI" | "COMPLETE";
  business_profile: BusinessProfile;
  is_active: boolean;
  created_at: string;
};

const TOKEN_KEY = "sora-system-token";

export function getSystemToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.sessionStorage.getItem(TOKEN_KEY);
}

export function setSystemToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.sessionStorage.setItem(TOKEN_KEY, token);
  else window.sessionStorage.removeItem(TOKEN_KEY);
}

async function systemRequest<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getSystemToken();
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-System-Token": token } : {}),
      ...init.headers,
    },
    cache: "no-store",
  });
  if (!response.ok) {
    let message = "Falha no console do sistema";
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Mantém a mensagem padrão.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function systemLogin(password: string): Promise<void> {
  const data = await fetch("/api/v1/system/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    cache: "no-store",
  });
  if (!data.ok) {
    let message = "Senha master inválida";
    try {
      const body = (await data.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Mantém a mensagem padrão.
    }
    throw new Error(message);
  }
  const body = (await data.json()) as { token: string };
  setSystemToken(body.token);
}

export async function systemLogout(): Promise<void> {
  try {
    await systemRequest<void>("/api/v1/system/logout", { method: "POST" });
  } finally {
    setSystemToken(null);
  }
}

export async function getSystemTenants(): Promise<SystemTenant[]> {
  return systemRequest<SystemTenant[]>("/api/v1/system/tenants");
}

export async function updateSystemProfile(
  tenantId: string,
  profile: BusinessProfile,
): Promise<SystemTenant> {
  return systemRequest<SystemTenant>(
    `/api/v1/system/tenants/${tenantId}/profile`,
    {
      method: "PATCH",
      body: JSON.stringify({ business_profile: profile }),
    },
  );
}
