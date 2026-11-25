import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
  type TokenPair,
} from "./tokens";

export type Me = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "COLLABORATOR";
};

type LoginInput = {
  tenant_slug: string;
  email: string;
  password: string;
};

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

async function refreshTokens(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  const response = await fetch("/api/v1/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    clearTokens();
    return false;
  }

  saveTokens((await response.json()) as TokenPair);
  return true;
}

async function authenticatedRequest<T>(
  path: string,
  init: RequestInit = {},
  retried = false,
): Promise<T> {
  const accessToken = getAccessToken();
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(path, { ...init, headers, cache: "no-store" });

  if (response.status === 401 && !retried) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      return authenticatedRequest<T>(path, init, true);
    }
    clearTokens();
    throw new Error("Sessão expirada");
  }

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export async function login(input: LoginInput): Promise<void> {
  const pair = await request<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
  saveTokens(pair);
}

export async function logout(): Promise<void> {
  const refreshToken = getRefreshToken();

  try {
    await authenticatedRequest<void>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // O logout local deve funcionar mesmo se a API estiver indisponível.
  } finally {
    clearTokens();
  }
}

export async function getMe(): Promise<Me> {
  return authenticatedRequest<Me>("/api/v1/auth/me");
}
