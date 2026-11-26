import { Platform } from "react-native";

import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
  type TokenPair,
} from "./auth";

const fallbackUrl =
  Platform.OS === "android"
    ? "http://10.0.2.2:8010"
    : "http://127.0.0.1:8010";

export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? fallbackUrl;

export type Me = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "COLLABORATOR";
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
  subscription_id: string | null;
};

export type Client = {
  id: string;
  full_name: string;
  phone: string;
  email: string | null;
  score: number;
  is_blocked: boolean;
};

export type Attachment = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  created_at: string;
};

export type MedicalRecord = {
  id: string;
  client_id: string;
  title: string;
  notes: string;
  created_by: string | null;
  created_at: string;
  attachments: Attachment[];
};

export type UserSummary = {
  id: string;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  commission_percentage: string | null;
  commission_fixed: string | null;
  commission_base: string;
};

export type Commission = {
  user_id: string;
  commission_percentage: string | null;
  commission_fixed: string | null;
  commission_base: string;
};

export type TenantSettings = {
  deposit_score_threshold: number | null;
  deposit_amount_low_score: string | null;
  theme_primary_color: string;
  agent_name: string;
};

export type ScoreEventResult = {
  id: string;
  client_id: string;
  rating: "POSITIVE" | "NEGATIVE";
  score_after: number;
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

async function toApiError(response: Response): Promise<ApiError> {
  let message = `HTTP ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") message = body.detail;
  } catch {
    // Resposta sem JSON: mantém a mensagem padrão.
  }
  return new ApiError(response.status, message);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init.headers,
    },
  });
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function refreshSession(): Promise<boolean> {
  const token = await getRefreshToken();
  if (!token) return false;
  try {
    const pair = await request<TokenPair>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: token }),
    });
    await saveTokens(pair);
    return true;
  } catch {
    await clearTokens();
    return false;
  }
}

async function authenticatedRequest<T>(
  path: string,
  init: RequestInit = {},
  retried = false,
): Promise<T> {
  const token = await getAccessToken();
  if (!token) throw new ApiError(401, "Sessão expirada");
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (response.status === 401 && !retried) {
    if (await refreshSession()) {
      return authenticatedRequest<T>(path, init, true);
    }
    throw new ApiError(401, "Sessão expirada");
  }
  if (!response.ok) throw await toApiError(response);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(input: {
  tenant_slug: string;
  email: string;
  password: string;
}): Promise<void> {
  const pair = await request<TokenPair>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(input),
  });
  await saveTokens(pair);
}

export async function logout(): Promise<void> {
  const refreshToken = await getRefreshToken();
  try {
    await authenticatedRequest<void>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // Logout local deve funcionar mesmo sem rede.
  } finally {
    await clearTokens();
  }
}

export async function getMe(): Promise<Me> {
  return authenticatedRequest<Me>("/api/v1/auth/me");
}

export async function getAppointments(date: string): Promise<Appointment[]> {
  const params = new URLSearchParams({ from_date: date, to_date: date });
  return authenticatedRequest<Appointment[]>(
    `/api/v1/appointments?${params.toString()}`,
  );
}

export async function updateAppointmentStatus(
  id: string,
  status: "CONFIRMED" | "CANCELLED" | "COMPLETED" | "NO_SHOW",
): Promise<Appointment> {
  return authenticatedRequest<Appointment>(`/api/v1/appointments/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export async function getClients(): Promise<Client[]> {
  return authenticatedRequest<Client[]>("/api/v1/clients");
}

export async function getMedicalRecords(
  clientId: string,
): Promise<MedicalRecord[]> {
  return authenticatedRequest<MedicalRecord[]>(
    `/api/v1/clients/${clientId}/records`,
  );
}

export async function createMedicalRecord(
  clientId: string,
  input: { title: string; notes: string },
): Promise<MedicalRecord> {
  return authenticatedRequest<MedicalRecord>(
    `/api/v1/clients/${clientId}/records`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export async function addLgpdConsent(clientId: string): Promise<void> {
  await authenticatedRequest<unknown>(`/api/v1/clients/${clientId}/consents`, {
    method: "POST",
    body: JSON.stringify({
      terms_version: "v1",
      purposes: ["health_data", "appointment_management"],
    }),
  });
}

export async function presignAttachment(
  clientId: string,
  recordId: string,
  input: { filename: string; content_type: string; size_bytes: number },
): Promise<{ attachment_id: string; upload_url: string; expires_in: number }> {
  return authenticatedRequest(
    `/api/v1/clients/${clientId}/records/${recordId}/attachments/presign`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

export async function getAttachmentUrl(
  clientId: string,
  recordId: string,
  attachmentId: string,
): Promise<{ url: string; expires_in: number }> {
  return authenticatedRequest(
    `/api/v1/clients/${clientId}/records/${recordId}/attachments/${attachmentId}/url`,
  );
}

export async function addScoreEvent(
  clientId: string,
  rating: "POSITIVE" | "NEGATIVE",
): Promise<ScoreEventResult> {
  return authenticatedRequest<ScoreEventResult>(
    `/api/v1/clients/${clientId}/score-events`,
    {
      method: "POST",
      body: JSON.stringify({ rating }),
    },
  );
}

export async function getUsers(): Promise<UserSummary[]> {
  return authenticatedRequest<UserSummary[]>("/api/v1/users");
}

export async function getCommission(): Promise<Commission> {
  return authenticatedRequest<Commission>("/api/v1/users/me/commission");
}

export async function getTenantSettings(): Promise<TenantSettings> {
  return authenticatedRequest<TenantSettings>("/api/v1/tenants/settings");
}
