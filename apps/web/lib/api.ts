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
  description: string | null;
  duration_minutes: number;
  buffer_minutes: number;
  price: string;
  cost: string;
  requires_deposit: boolean;
  deposit_amount: string | null;
  show_average_price: boolean;
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
  commission_percentage: string | null;
  commission_fixed: string | null;
  commission_base: string;
};

export type TenantSettings = {
  deposit_score_threshold: number | null;
  deposit_amount_low_score: string | null;
  theme_primary_color: string;
  agent_name: string;
  enable_tithe_and_offering: boolean;
  tithe_percentage: string;
  offering_amount: string;
};

export type SubscriptionPlanItem = {
  id: string;
  service_id: string;
  uses_per_cycle: number;
  min_interval_days: number | null;
  allowed_weekdays: number[] | null;
};

export type SubscriptionPlan = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  price: string;
  billing_cycle: "MONTHLY" | "QUARTERLY";
  is_active: boolean;
  items: SubscriptionPlanItem[];
};

export type ClientSubscription = {
  id: string;
  client_id: string;
  client_name: string;
  plan_id: string;
  plan_name: string;
  status: string;
  started_at: string;
  current_period_start: string;
  current_period_end: string;
  quotas: PublicQuota[];
};

export type FinancialAccount = {
  id: string;
  name: string;
  type: "CASH" | "BANK";
  initial_balance: string;
  is_active: boolean;
};

export type AccountBalance = {
  account_id: string;
  name: string;
  type: "CASH" | "BANK";
  initial_balance: string;
  balance: string;
};

export type FinancialEntryType = "INCOME" | "EXPENSE";
export type FinancialEntryStatus = "PENDING" | "PAID";
export type FinancialCategory =
  | "SERVICE"
  | "PACKAGE"
  | "SUBSCRIPTION"
  | "PRODUCT"
  | "OTHER_INCOME"
  | "TAX"
  | "CARD_FEE"
  | "SUPPLIES"
  | "COMMISSION"
  | "RENT"
  | "UTILITY"
  | "MARKETING"
  | "PAYROLL"
  | "OTHER_EXPENSE";

export type FinancialEntry = {
  id: string;
  account_id: string;
  type: FinancialEntryType;
  category: FinancialCategory;
  description: string;
  amount: string;
  competence_date: string;
  cash_date: string | null;
  status: FinancialEntryStatus;
  appointment_id: string | null;
};

export type CashFlow = {
  from_date: string;
  to_date: string;
  opening_balance: string;
  inflows: string;
  outflows: string;
  closing_balance: string;
};

export type Dre = {
  from_date: string;
  to_date: string;
  gross_revenue: string;
  deductions: string;
  costs: string;
  operating_expenses: string;
  net_profit: string;
  commissions_accrued: string;
  tithe_enabled: boolean;
  tithe_percentage: string;
  tithe_amount: string;
  offering_amount: string;
  after_tithe_and_offering: string;
};

export type CommissionSummary = {
  from_date: string;
  to_date: string;
  items: {
    collaborator_id: string;
    collaborator_name: string;
    completed_appointments: number;
    gross_revenue: string;
    commission_amount: string;
  }[];
  total: string;
};

export type SaleItem = {
  appointment_id: string;
  starts_at: string;
  client_name: string;
  service_name: string;
  collaborator_name: string;
  gross_amount: string;
  cost_amount: string;
  commission_amount: string;
  net_amount: string;
};

export type SalesSummary = {
  from_date: string;
  to_date: string;
  items: SaleItem[];
  gross_total: string;
  net_total: string;
};

export type AiMessage = {
  id: string;
  direction: "INBOUND" | "OUTBOUND";
  content: string;
  intent: string | null;
  created_at: string;
};

export type AiConversation = {
  id: string;
  client_id: string | null;
  client_name: string | null;
  phone: string;
  status: "OPEN" | "HUMAN" | "CLOSED";
  last_message: string | null;
  last_message_at: string;
};

export type AiConversationDetail = AiConversation & {
  messages: AiMessage[];
};

export type AiSummary = {
  date: string;
  agent_name: string;
  open_conversations: number;
  human_conversations: number;
  messages_today: number;
  appointments_today: number;
  birthdays: {
    client_id: string;
    full_name: string;
    birth_date: string;
    days_until: number;
  }[];
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

export async function getTenantSettings(): Promise<TenantSettings> {
  return authenticatedRequest<TenantSettings>("/api/v1/tenants/settings");
}

export async function updateTenantSettings(
  changes: Partial<TenantSettings>,
): Promise<TenantSettings> {
  return authenticatedRequest<TenantSettings>("/api/v1/tenants/settings", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

type CreateClientInput = {
  full_name: string;
  phone: string;
  email?: string;
  birth_date?: string;
};

export async function createClient(input: CreateClientInput): Promise<Client> {
  return authenticatedRequest<Client>("/api/v1/clients", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

type UpdateClientInput = {
  full_name?: string;
  phone?: string;
  email?: string | null;
  birth_date?: string | null;
  score?: number;
  is_blocked?: boolean;
};

export async function updateClient(
  id: string,
  changes: UpdateClientInput,
): Promise<Client> {
  return authenticatedRequest<Client>(`/api/v1/clients/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

type CreateServiceInput = {
  name: string;
  description?: string;
  duration_minutes: number;
  buffer_minutes: number;
  price: string;
  cost: string;
  requires_deposit: boolean;
  deposit_amount?: string | null;
  show_average_price: boolean;
  is_active?: boolean;
};

export async function createService(
  input: CreateServiceInput,
): Promise<Service> {
  return authenticatedRequest<Service>("/api/v1/services", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateService(
  id: string,
  changes: Partial<CreateServiceInput>,
): Promise<Service> {
  return authenticatedRequest<Service>(`/api/v1/services/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

type CreateUserInput = {
  full_name: string;
  email: string;
  password: string;
  role: "ADMIN" | "COLLABORATOR";
  commission_percentage?: string | null;
  commission_fixed?: string | null;
  commission_base?: "GROSS" | "NET";
};

export async function createUser(input: CreateUserInput): Promise<UserSummary> {
  return authenticatedRequest<UserSummary>("/api/v1/users", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

type UpdateUserInput = {
  full_name?: string;
  is_active?: boolean;
  role?: "ADMIN" | "COLLABORATOR";
  commission_percentage?: string | null;
  commission_fixed?: string | null;
  commission_base?: "GROSS" | "NET";
};

export async function updateUser(
  id: string,
  changes: UpdateUserInput,
): Promise<UserSummary> {
  return authenticatedRequest<UserSummary>(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function getSubscriptionPlans(): Promise<SubscriptionPlan[]> {
  return authenticatedRequest<SubscriptionPlan[]>("/api/v1/subscription-plans");
}

type CreateSubscriptionPlanInput = {
  name: string;
  description?: string;
  price: string;
  billing_cycle: "MONTHLY" | "QUARTERLY";
  items: {
    service_id: string;
    uses_per_cycle: number;
    min_interval_days?: number | null;
    allowed_weekdays?: number[] | null;
  }[];
  is_active?: boolean;
};

export async function createSubscriptionPlan(
  input: CreateSubscriptionPlanInput,
): Promise<SubscriptionPlan> {
  return authenticatedRequest<SubscriptionPlan>("/api/v1/subscription-plans", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateSubscriptionPlan(
  id: string,
  changes: {
    name?: string;
    description?: string | null;
    price?: string;
    billing_cycle?: "MONTHLY" | "QUARTERLY";
    is_active?: boolean;
  },
): Promise<SubscriptionPlan> {
  return authenticatedRequest<SubscriptionPlan>(
    `/api/v1/subscription-plans/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(changes),
    },
  );
}

export async function getSubscriptions(): Promise<ClientSubscription[]> {
  return authenticatedRequest<ClientSubscription[]>("/api/v1/subscriptions");
}

export async function createClientSubscription(
  clientId: string,
  planId: string,
): Promise<ClientSubscription> {
  return authenticatedRequest<ClientSubscription>(
    `/api/v1/clients/${clientId}/subscriptions`,
    {
      method: "POST",
      body: JSON.stringify({ plan_id: planId }),
    },
  );
}

export async function cancelSubscription(
  id: string,
): Promise<ClientSubscription> {
  return authenticatedRequest<ClientSubscription>(
    `/api/v1/subscriptions/${id}/cancel`,
    { method: "POST" },
  );
}

async function authenticatedText(
  path: string,
  init: RequestInit = {},
  retried = false,
): Promise<string> {
  const accessToken = getAccessToken();
  const headers = new Headers(init.headers);
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  const response = await fetch(path, { ...init, headers, cache: "no-store" });
  if (response.status === 401 && !retried) {
    if (await refreshTokens()) return authenticatedText(path, init, true);
    clearTokens();
    throw new ApiError(401, "Sessão expirada");
  }
  if (!response.ok) throw await toApiError(response);
  return response.text();
}

export async function getFinancialAccounts(): Promise<FinancialAccount[]> {
  return authenticatedRequest<FinancialAccount[]>("/api/v1/finance/accounts");
}

export async function createFinancialAccount(input: {
  name: string;
  type: "CASH" | "BANK";
  initial_balance: string;
}): Promise<FinancialAccount> {
  return authenticatedRequest<FinancialAccount>("/api/v1/finance/accounts", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getAccountBalances(): Promise<AccountBalance[]> {
  return authenticatedRequest<AccountBalance[]>(
    "/api/v1/finance/accounts/balances",
  );
}

export async function getFinancialEntries(
  fromDate: string,
  toDate: string,
): Promise<FinancialEntry[]> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<FinancialEntry[]>(
    `/api/v1/finance/entries?${params.toString()}`,
  );
}

export async function createFinancialEntry(input: {
  account_id: string;
  type: FinancialEntryType;
  category: FinancialCategory;
  description: string;
  amount: string;
  competence_date: string;
  cash_date: string | null;
  status: FinancialEntryStatus;
}): Promise<FinancialEntry> {
  return authenticatedRequest<FinancialEntry>("/api/v1/finance/entries", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateFinancialEntry(
  id: string,
  changes: Partial<{
    account_id: string;
    category: FinancialCategory;
    description: string;
    amount: string;
    competence_date: string;
    cash_date: string | null;
    status: FinancialEntryStatus;
  }>,
): Promise<FinancialEntry> {
  return authenticatedRequest<FinancialEntry>(
    `/api/v1/finance/entries/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(changes),
    },
  );
}

export async function getCashFlow(
  fromDate: string,
  toDate: string,
): Promise<CashFlow> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<CashFlow>(
    `/api/v1/finance/cash-flow?${params.toString()}`,
  );
}

export async function getDre(
  fromDate: string,
  toDate: string,
): Promise<Dre> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<Dre>(`/api/v1/finance/dre?${params.toString()}`);
}

export async function getCommissions(
  fromDate: string,
  toDate: string,
): Promise<CommissionSummary> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<CommissionSummary>(
    `/api/v1/finance/commissions?${params.toString()}`,
  );
}

export async function getSales(
  fromDate: string,
  toDate: string,
): Promise<SalesSummary> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<SalesSummary>(
    `/api/v1/finance/sales?${params.toString()}`,
  );
}

export async function getFinanceCsv(
  fromDate: string,
  toDate: string,
): Promise<string> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedText(`/api/v1/finance/export?${params.toString()}`);
}

export async function getAiSummary(date?: string): Promise<AiSummary> {
  const params = new URLSearchParams();
  if (date) params.set("date", date);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return authenticatedRequest<AiSummary>(`/api/v1/ai/summary${suffix}`);
}

export async function getAiConversations(): Promise<AiConversation[]> {
  return authenticatedRequest<AiConversation[]>("/api/v1/ai/conversations");
}

export async function getAiConversation(
  id: string,
): Promise<AiConversationDetail> {
  return authenticatedRequest<AiConversationDetail>(
    `/api/v1/ai/conversations/${id}`,
  );
}

export async function takeoverAiConversation(
  id: string,
): Promise<AiConversationDetail> {
  return authenticatedRequest<AiConversationDetail>(
    `/api/v1/ai/conversations/${id}/takeover`,
    { method: "POST" },
  );
}

export async function sendAiConversationMessage(
  id: string,
  content: string,
): Promise<AiMessage> {
  return authenticatedRequest<AiMessage>(
    `/api/v1/ai/conversations/${id}/messages`,
    { method: "POST", body: JSON.stringify({ content }) },
  );
}

export async function closeAiConversation(
  id: string,
): Promise<AiConversationDetail> {
  return authenticatedRequest<AiConversationDetail>(
    `/api/v1/ai/conversations/${id}/close`,
    { method: "POST" },
  );
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
