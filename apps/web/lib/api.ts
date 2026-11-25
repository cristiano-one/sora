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

export type Service = {
  id: string;
  name: string;
  duration_minutes: number;
  buffer_minutes: number;
  price: string;
  is_active: boolean;
};

export type Client = {
  id: string;
  full_name: string;
  phone: string;
  email: string | null;
  score: number;
  is_blocked: boolean;
};

export type UserSummary = {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
};

export type Appointment = {
  id: string;
  tenant_id: string;
  collaborator_id: string;
  client_id: string;
  service_id: string;
  client_name: string;
  service_name: string;
  starts_at: string;
  ends_at: string;
  status: string;
  deposit_amount: string | null;
};

export type Availability = {
  collaborator_id: string;
  service_id: string;
  date: string;
  duration_minutes: number;
  buffer_minutes: number;
  available: boolean;
  available_slots: string[];
};

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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
    throw new ApiError(response.status, `HTTP ${response.status}`);
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

export async function getServices(): Promise<Service[]> {
  return authenticatedRequest<Service[]>("/api/v1/services");
}

export async function getClients(): Promise<Client[]> {
  return authenticatedRequest<Client[]>("/api/v1/clients");
}

export async function getUsers(): Promise<UserSummary[]> {
  return authenticatedRequest<UserSummary[]>("/api/v1/users");
}

export async function getAppointments(
  date: string,
  collaboratorId?: string,
): Promise<Appointment[]> {
  const params = new URLSearchParams({ from_date: date, to_date: date });
  if (collaboratorId) params.set("collaborator_id", collaboratorId);
  return authenticatedRequest<Appointment[]>(
    `/api/v1/appointments?${params.toString()}`,
  );
}

export async function getAvailability(
  serviceId: string,
  date: string,
  collaboratorId?: string,
): Promise<Availability> {
  const params = new URLSearchParams({ service_id: serviceId, date });
  if (collaboratorId) params.set("collaborator_id", collaboratorId);
  return authenticatedRequest<Availability>(
    `/api/v1/agenda/availability?${params.toString()}`,
  );
}

type CreateAppointmentInput = {
  client_id: string;
  service_id: string;
  collaborator_id?: string;
  starts_at: string;
};

export async function createAppointment(
  input: CreateAppointmentInput,
): Promise<Appointment> {
  return authenticatedRequest<Appointment>("/api/v1/appointments", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function cancelAppointment(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/appointments/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status: "CANCELLED" }),
  });
}
