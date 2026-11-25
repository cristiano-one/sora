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
  subscription_id: string | null;
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

export type PublicService = {
  id: string;
  name: string;
  duration_minutes: number;
  price: string | null;
};

export type PublicProfessional = {
  id: string;
  full_name: string;
};

export type PublicPlanItem = {
  service_id: string;
  service_name: string;
  uses_per_cycle: number;
  min_interval_days: number | null;
  allowed_weekdays: number[] | null;
};

export type PublicPlan = {
  id: string;
  name: string;
  description: string | null;
  price: string;
  billing_cycle: "MONTHLY" | "QUARTERLY";
  items: PublicPlanItem[];
};

export type PublicQuota = {
  service_id: string;
  service_name: string;
  uses_per_cycle: number;
  used: number;
  remaining: number;
  min_interval_days: number | null;
  allowed_weekdays: number[] | null;
};

export type PublicPayment = {
  id: string;
  amount: string;
  status: "PENDING" | "PAID" | "EXPIRED" | "CANCELLED";
  pix_copy_paste: string;
  qr_code_data_uri: string;
  expires_at: string;
};

export type PublicPaymentConfirm = PublicPayment & {
  appointment_status: string | null;
  subscription_status: string | null;
};

export type PublicSubscription = {
  status: "PENDING_PAYMENT" | "ACTIVE" | "CANCELLED" | "EXPIRED";
  plan_id: string;
  plan_name: string;
  current_period_start: string;
  current_period_end: string;
  quotas: PublicQuota[];
  payment: PublicPayment | null;
};

export type PublicContext = {
  tenant_name: string;
  tenant_slug: string;
  client_name: string | null;
  theme_primary_color: string;
  services: PublicService[];
  professionals: PublicProfessional[];
  plans: PublicPlan[];
  subscription: PublicSubscription | null;
};

export type PublicAppointment = {
  id: string;
  starts_at: string;
  ends_at: string;
  status: string;
  service_name: string;
  collaborator_name: string;
  deposit_amount: string | null;
  used_subscription: boolean;
  payment: PublicPayment | null;
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

async function toApiError(response: Response): Promise<ApiError> {
  let message = `HTTP ${response.status}`;
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") message = body.detail;
  } catch {
    // Resposta sem corpo JSON: mantém a mensagem padrão.
  }
  return new ApiError(response.status, message);
}

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
    throw await toApiError(response);
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
    throw await toApiError(response);
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

export async function getPublicContext(
  slug: string,
  token: string,
): Promise<PublicContext> {
  const params = new URLSearchParams({ t: token });
  return request<PublicContext>(
    `/api/v1/public/${encodeURIComponent(slug)}/context?${params.toString()}`,
  );
}

export async function getPublicAvailability(
  slug: string,
  token: string,
  serviceId: string,
  collaboratorId: string,
  date: string,
): Promise<Availability> {
  const params = new URLSearchParams({
    t: token,
    service_id: serviceId,
    collaborator_id: collaboratorId,
    date,
  });
  return request<Availability>(
    `/api/v1/public/${encodeURIComponent(slug)}/availability?${params.toString()}`,
  );
}

type PublicAppointmentInput = {
  token: string;
  service_id: string;
  collaborator_id: string;
  starts_at: string;
  full_name: string;
};

export async function createPublicAppointment(
  slug: string,
  input: PublicAppointmentInput,
): Promise<PublicAppointment> {
  const params = new URLSearchParams({ t: input.token });
  return request<PublicAppointment>(
    `/api/v1/public/${encodeURIComponent(slug)}/appointments?${params.toString()}`,
    {
      method: "POST",
      body: JSON.stringify({
        service_id: input.service_id,
        collaborator_id: input.collaborator_id,
        starts_at: input.starts_at,
        full_name: input.full_name,
      }),
    },
  );
}

export async function createPublicSubscription(
  slug: string,
  input: { token: string; plan_id: string; full_name?: string },
): Promise<PublicSubscription> {
  const params = new URLSearchParams({ t: input.token });
  return request<PublicSubscription>(
    `/api/v1/public/${encodeURIComponent(slug)}/subscriptions?${params.toString()}`,
    {
      method: "POST",
      body: JSON.stringify({
        plan_id: input.plan_id,
        full_name: input.full_name,
      }),
    },
  );
}

export async function getPublicPayment(
  slug: string,
  token: string,
  paymentId: string,
): Promise<PublicPaymentConfirm> {
  const params = new URLSearchParams({ t: token });
  return request<PublicPaymentConfirm>(
    `/api/v1/public/${encodeURIComponent(slug)}/payments/${encodeURIComponent(paymentId)}?${params.toString()}`,
  );
}

export async function confirmMockPublicPayment(
  slug: string,
  token: string,
  paymentId: string,
): Promise<PublicPaymentConfirm> {
  const params = new URLSearchParams({ t: token });
  return request<PublicPaymentConfirm>(
    `/api/v1/public/${encodeURIComponent(slug)}/payments/${encodeURIComponent(paymentId)}/mock-confirm?${params.toString()}`,
    { method: "POST" },
  );
}
