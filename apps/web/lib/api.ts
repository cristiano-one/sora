import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  saveTokens,
  type TokenPair,
} from "./tokens";
import type { BusinessProfile } from "./profiles";

export type Me = {
  id: string;
  tenant_id: string;
  email: string;
  full_name: string;
  role: "OWNER" | "ADMIN" | "COLLABORATOR";
  business_profile: BusinessProfile;
  can_manage_ai_inbox: boolean;
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

export type PackageItem = {
  id: string;
  service_id: string;
  quantity: number;
};

export type Package = {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  total_price: string;
  is_active: boolean;
  items: PackageItem[];
};

export type Client = {
  id: string;
  full_name: string;
  phone: string;
  email: string | null;
  birth_date: string | null;
  address_zip: string | null;
  address_street: string | null;
  address_number: string | null;
  address_complement: string | null;
  address_neighborhood: string | null;
  address_city: string | null;
  address_state: string | null;
  notes: string | null;
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
  employment_type: "EMPLOYEE" | "PARTNER" | "MEI";
  can_manage_ai_inbox: boolean;
};

export type TenantSettings = {
  deposit_score_threshold: number | null;
  deposit_amount_low_score: string | null;
  theme_primary_color: string;
  agent_name: string;
  agent_tone: string;
  agent_welcome_message: string | null;
  agent_knowledge: string | null;
  agent_cancellation_policy: string | null;
  agent_address_info: string | null;
  agent_upsell: string | null;
  ai_provider: "mock" | "groq";
  ai_model: string;
  ai_key_configured: boolean;
  fiscal_enabled: boolean;
  fiscal_provider: string;
  fiscal_municipality: string | null;
  fiscal_service_code: string | null;
  fiscal_email: string | null;
  enable_tithe_and_offering: boolean;
  tithe_percentage: string;
  offering_amount: string;
  birthday_credit_amount: string;
};

export type TenantSettingsUpdate = Partial<TenantSettings> & {
  ai_api_key?: string;
  clear_ai_api_key?: boolean;
};

export type AiProviderTestResult = {
  ok: boolean;
  provider: string;
  model: string;
  latency_ms: number;
  reply: string;
};

export type WhatsAppConnection = {
  status: "CONNECTED" | "DISCONNECTED" | "ERROR";
  display_phone_number: string | null;
  verified_name: string | null;
  quality_rating: string | null;
  waba_id: string | null;
  phone_number_id: string | null;
  registration_status: "PENDING" | "REGISTERED" | "FAILED" | "SKIPPED";
  registration_error: string | null;
  connected_at: string | null;
  last_error: string | null;
  embedded_signup: {
    enabled: boolean;
    app_id: string | null;
    config_id: string | null;
    graph_version: string;
  };
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

export type MyCommissionRule = {
  user_id: string;
  commission_percentage: string | null;
  commission_fixed: string | null;
  commission_base: "GROSS" | "NET";
};

export type AdminPayment = {
  id: string;
  client_id: string;
  client_name: string;
  appointment_id: string | null;
  subscription_id: string | null;
  amount: string;
  status: "PENDING" | "PAID" | "EXPIRED" | "CANCELLED";
  provider: string;
  expires_at: string;
  paid_at: string | null;
  created_at: string;
};

export type InventoryItem = {  id: string;
  name: string;
  unit: string;
  quantity: string;
  min_quantity: string;
  unit_cost: string;
  is_active: boolean;
  low_stock: boolean;
  total_value: string;
  created_at: string;
};

export type StockDocumentType = "NFE" | "RECEIPT" | "OTHER";
export type StockPaymentMethod =
  | "CASH"
  | "PIX"
  | "CARD"
  | "TRANSFER"
  | "BOLETO"
  | "OTHER";

export type StockMovement = {
  id: string;
  item_id: string;
  kind: "IN" | "OUT" | "ADJUSTMENT";
  quantity: string;
  reason: string | null;
  document_type: StockDocumentType | null;
  document_number: string | null;
  document_series: string | null;
  supplier_name: string | null;
  supplier_tax_id: string | null;
  issue_date: string | null;
  total_amount: string | null;
  payment_method: StockPaymentMethod | null;
  access_key: string | null;
  created_at: string;
};

export type PayrollKind =
  | "SALARY"
  | "ADVANCE"
  | "PRO_LABORE"
  | "COMMISSION_PAYOUT";

export type PayrollEntry = {
  id: string;
  user_id: string;
  user_name: string;
  kind: PayrollKind;
  description: string;
  amount: string;
  competence_date: string;
  status: "PENDING" | "PAID";
  cash_date: string | null;
  financial_entry_id: string | null;
  created_at: string;
};

export type TitheDelivery = {
  id: string;
  competence_date: string;
  tithe_amount: string;
  offering_amount: string;
  note: string | null;
  created_at: string;
};

export type TitheSummary = {
  dre: Dre;
  deliveries: TitheDelivery[];
  delivered_tithe: string;
  delivered_offering: string;
  pending_tithe: string;
  pending_offering: string;
};

export type ClientCredit = {
  id: string;
  amount: string;
  used_amount: string;
  remaining_amount: string;
  reason: string;
  reference: string;
  expires_at: string;
  is_available: boolean;
};

export type ClientCreditUsage = {
  id: string;
  credit_id: string;
  amount: string;
  appointment_id: string | null;
  note: string | null;
  created_at: string;
};

export type SaleItemCategory = "SERVICE" | "PACKAGE" | "PRODUCT" | "OTHER";
export type SaleStatus = "OPEN" | "PAID" | "CANCELLED";
export type SalePaymentMethod =
  | "PIX"
  | "CASH"
  | "CARD"
  | "BOLETO"
  | "TRANSFER"
  | "OTHER";

export type SaleOrderItem = {
  id: string;
  service_id: string | null;
  inventory_item_id: string | null;
  category: SaleItemCategory;
  description: string;
  quantity: number;
  unit_price: string;
  cost: string;
  total: string;
};

export type Sale = {
  id: string;
  client_id: string;
  client_name: string;
  appointment_id: string | null;
  collaborator_id: string | null;
  collaborator_name: string | null;
  status: SaleStatus;
  subtotal: string;
  discount: string;
  credit_amount: string;
  total: string;
  payment_method: SalePaymentMethod | null;
  account_id: string | null;
  financial_entry_id: string | null;
  notes: string | null;
  created_at: string;
  closed_at: string | null;
  items: SaleOrderItem[];
};

export type SaleAccount = {
  id: string;
  name: string;
  type: "CASH" | "BANK";
};

export type AutomationTrigger =
  | "BOOKING_CONFIRMATION"
  | "REMINDER_24H"
  | "REMINDER_2H"
  | "POST_SERVICE"
  | "WINBACK_60D"
  | "BIRTHDAY";

export type AutomationRule = {
  id: string;
  trigger: AutomationTrigger;
  name: string;
  template: string;
  delay_minutes: number;
  is_active: boolean;
};

export type AutomationRun = {
  id: string;
  rule_id: string;
  client_id: string;
  appointment_id: string | null;
  status: "PENDING" | "SENT" | "SKIPPED" | "FAILED";
  scheduled_for: string;
  sent_at: string | null;
  error: string | null;
  created_at: string;
};

export type AutomationRunSummary = {
  processed: number;
  sent: number;
  failed: number;
  skipped: number;
};

export type FiscalInvoice = {
  id: string;
  sale_id: string;
  status: "ISSUED" | "CANCELLED" | "ERROR";
  number: string;
  provider: string;
  amount: string;
  issued_at: string;
  cancelled_at: string | null;
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
  needs_approval: boolean;
  approval_note: string | null;
  last_message: string | null;
  last_message_at: string;
  last_intent: string | null;
};

export type AiConversationDetail = AiConversation & {
  messages: AiMessage[];
};

export type WhatsAppSimulationResult = {
  conversation_id: string;
  reply: string;
  intent: string;
  status: "OPEN" | "HUMAN" | "CLOSED";
};

export type AiSummary = {
  date: string;
  agent_name: string;
  open_conversations: number;
  human_conversations: number;
  approvals_pending: number;
  messages_today: number;
  appointments_today: number;
  birthdays: {
    client_id: string;
    full_name: string;
    birth_date: string;
    days_until: number;
  }[];
};

export type BirthdayCredit = {
  id: string;
  client_id: string;
  client_name: string;
  amount: string;
  used_amount: string;
  reason: string;
  reference: string;
  expires_at: string;
};

export type BirthdayCreditRun = {
  year: string;
  created: number;
  total_amount: string;
  credits: BirthdayCredit[];
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
  checked_in_at: string | null;
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
    if (typeof body.detail === "string") {
      message = body.detail;
    } else if (Array.isArray(body.detail) && body.detail.length > 0) {
      message =
        response.status === 422
          ? "Confira os dados informados."
          : `HTTP ${response.status}`;
    }
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

export async function createTenant(input: {
  name: string;
  slug: string;
  tax_regime: "MEI" | "COMPLETE";
  business_profile:
    | "MEDICAL_CLINIC"
    | "AESTHETICS"
    | "PODOLOGY"
    | "SALON"
    | "BARBERSHOP"
    | "GENERAL";
  owner_full_name: string;
  owner_email: string;
  owner_password: string;
}): Promise<{
  id: string;
  name: string;
  slug: string;
  business_profile: string;
}> {
  return request<{
    id: string;
    name: string;
    slug: string;
    business_profile: string;
  }>("/api/v1/tenants", { method: "POST", body: JSON.stringify(input) });
}

export async function forgotPassword(input: {
  tenant_slug: string;
  email: string;
}): Promise<{ message: string }> {
  return request<{ message: string }>("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function resetPassword(input: {
  tenant_slug: string;
  token: string;
  new_password: string;
}): Promise<void> {
  await request<void>("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function acceptInvite(input: {
  tenant_slug: string;
  token: string;
  new_password: string;
}): Promise<void> {
  await request<void>("/api/v1/auth/accept-invite", {
    method: "POST",
    body: JSON.stringify(input),
  });
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

export async function getClient(id: string): Promise<Client> {
  return authenticatedRequest<Client>(`/api/v1/clients/${id}`);
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
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function addLgpdConsent(
  clientId: string,
  input: { terms_version: string; purposes: string[] },
): Promise<{ id: string; accepted_at: string; terms_version: string }> {
  return authenticatedRequest(
    `/api/v1/clients/${clientId}/consents`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function presignAttachment(
  clientId: string,
  recordId: string,
  input: { filename: string; content_type: string; size_bytes: number },
): Promise<{ attachment_id: string; upload_url: string; expires_in: number }> {
  return authenticatedRequest(
    `/api/v1/clients/${clientId}/records/${recordId}/attachments/presign`,
    { method: "POST", body: JSON.stringify(input) },
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

export async function deleteAttachment(
  clientId: string,
  recordId: string,
  attachmentId: string,
): Promise<void> {
  await authenticatedRequest<void>(
    `/api/v1/clients/${clientId}/records/${recordId}/attachments/${attachmentId}`,
    { method: "DELETE" },
  );
}

export async function getClientCredits(
  clientId: string,
): Promise<ClientCredit[]> {
  return authenticatedRequest<ClientCredit[]>(
    `/api/v1/clients/${clientId}/credits`,
  );
}

export async function getClientCreditUsages(
  clientId: string,
): Promise<ClientCreditUsage[]> {
  return authenticatedRequest<ClientCreditUsage[]>(
    `/api/v1/clients/${clientId}/credit-usages`,
  );
}

export async function applyClientCredit(
  clientId: string,
  creditId: string,
  input: { amount: string; note?: string | null; appointment_id?: string | null },
): Promise<ClientCreditUsage> {
  return authenticatedRequest<ClientCreditUsage>(
    `/api/v1/clients/${clientId}/credits/${creditId}/use`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function getSaleAccounts(): Promise<SaleAccount[]> {
  return authenticatedRequest<SaleAccount[]>("/api/v1/sales/accounts");
}

export async function createSaleFromAppointment(
  appointmentId: string,
): Promise<Sale> {
  return authenticatedRequest<Sale>(
    `/api/v1/sales/from-appointment/${appointmentId}`,
    { method: "POST" },
  );
}

export async function getSale(saleId: string): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}`);
}

export async function listSales(
  fromDate: string,
  toDate: string,
  status?: SaleStatus,
): Promise<Sale[]> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  if (status) params.set("status", status);
  return authenticatedRequest<Sale[]>(`/api/v1/sales?${params.toString()}`);
}

export async function addSaleItem(
  saleId: string,
  input: {
    service_id?: string | null;
    inventory_item_id?: string | null;
    category?: SaleItemCategory;
    description?: string | null;
    quantity?: number;
    unit_price?: string | null;
    cost?: string | null;
  },
): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}/items`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function removeSaleItem(
  saleId: string,
  itemId: string,
): Promise<Sale> {
  return authenticatedRequest<Sale>(
    `/api/v1/sales/${saleId}/items/${itemId}`,
    { method: "DELETE" },
  );
}

export async function updateSale(
  saleId: string,
  changes: { discount?: string; notes?: string | null },
): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function applySaleCredit(
  saleId: string,
  input: { credit_id: string; amount: string },
): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}/credits`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function closeSale(
  saleId: string,
  input: {
    payment_method: SalePaymentMethod;
    account_id: string;
    notes?: string | null;
  },
): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}/close`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function cancelSale(saleId: string): Promise<Sale> {
  return authenticatedRequest<Sale>(`/api/v1/sales/${saleId}/cancel`, {
    method: "POST",
  });
}

export async function getAutomationRules(): Promise<AutomationRule[]> {
  return authenticatedRequest<AutomationRule[]>("/api/v1/automations/rules");
}

export async function updateAutomationRule(
  ruleId: string,
  changes: { name?: string; template?: string; is_active?: boolean },
): Promise<AutomationRule> {
  return authenticatedRequest<AutomationRule>(
    `/api/v1/automations/rules/${ruleId}`,
    { method: "PATCH", body: JSON.stringify(changes) },
  );
}

export async function getAutomationRuns(): Promise<AutomationRun[]> {
  return authenticatedRequest<AutomationRun[]>("/api/v1/automations/runs");
}

export async function runAutomations(): Promise<AutomationRunSummary> {
  return authenticatedRequest<AutomationRunSummary>("/api/v1/automations/run", {
    method: "POST",
  });
}

export async function getSaleInvoice(
  saleId: string,
): Promise<FiscalInvoice> {
  return authenticatedRequest<FiscalInvoice>(
    `/api/v1/sales/${saleId}/invoice`,
  );
}

export async function issueSaleInvoice(
  saleId: string,
): Promise<FiscalInvoice> {
  return authenticatedRequest<FiscalInvoice>(
    `/api/v1/sales/${saleId}/invoice`,
    { method: "POST" },
  );
}

export async function cancelSaleInvoice(
  saleId: string,
): Promise<FiscalInvoice> {
  return authenticatedRequest<FiscalInvoice>(
    `/api/v1/sales/${saleId}/invoice/cancel`,
    { method: "POST" },
  );
}

export async function getUsers(): Promise<UserSummary[]> {
  return authenticatedRequest<UserSummary[]>("/api/v1/users");
}

export async function getTenantSettings(): Promise<TenantSettings> {
  return authenticatedRequest<TenantSettings>("/api/v1/tenants/settings");
}

export async function getWhatsAppConnection(): Promise<WhatsAppConnection> {
  return authenticatedRequest<WhatsAppConnection>(
    "/api/v1/whatsapp/connection",
  );
}

export async function connectWhatsApp(input: {
  code: string;
  waba_id: string;
  phone_number_id: string;
  pin: string;
}): Promise<WhatsAppConnection> {
  return authenticatedRequest<WhatsAppConnection>(
    "/api/v1/whatsapp/connection",
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function disconnectWhatsApp(): Promise<WhatsAppConnection> {
  return authenticatedRequest<WhatsAppConnection>(
    "/api/v1/whatsapp/connection",
    { method: "DELETE" },
  );
}

export async function updateTenantSettings(
  changes: TenantSettingsUpdate,
): Promise<TenantSettings> {
  return authenticatedRequest<TenantSettings>("/api/v1/tenants/settings", {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function testAiProvider(): Promise<AiProviderTestResult> {
  return authenticatedRequest<AiProviderTestResult>(
    "/api/v1/ai/provider/test",
    { method: "POST" },
  );
}

export async function getTenantExport(): Promise<Record<string, unknown>> {
  return authenticatedRequest<Record<string, unknown>>("/api/v1/tenants/export");
}

type CreateClientInput = {
  full_name: string;
  phone: string;
  email?: string;
  birth_date?: string | null;
  address_zip?: string | null;
  address_street?: string | null;
  address_number?: string | null;
  address_complement?: string | null;
  address_neighborhood?: string | null;
  address_city?: string | null;
  address_state?: string | null;
  notes?: string | null;
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
  address_zip?: string | null;
  address_street?: string | null;
  address_number?: string | null;
  address_complement?: string | null;
  address_neighborhood?: string | null;
  address_city?: string | null;
  address_state?: string | null;
  notes?: string | null;
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

export type CreatePackageInput = {
  name: string;
  description?: string | null;
  total_price: string;
  items: { service_id: string; quantity: number }[];
  is_active?: boolean;
};

type UpdatePackageInput = {
  name?: string;
  description?: string | null;
  total_price?: string;
  is_active?: boolean;
};

export async function getPackages(): Promise<Package[]> {
  return authenticatedRequest<Package[]>("/api/v1/packages");
}

export async function createPackage(
  input: CreatePackageInput,
): Promise<Package> {
  return authenticatedRequest<Package>("/api/v1/packages", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updatePackage(
  id: string,
  changes: UpdatePackageInput,
): Promise<Package> {
  return authenticatedRequest<Package>(`/api/v1/packages/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function deletePackage(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/packages/${id}`, {
    method: "DELETE",
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
  employment_type?: "EMPLOYEE" | "PARTNER" | "MEI";
  can_manage_ai_inbox?: boolean;
};

export async function createUser(input: CreateUserInput): Promise<UserSummary> {
  return authenticatedRequest<UserSummary>("/api/v1/users", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export type InviteUserInput = Omit<CreateUserInput, "password">;

export async function inviteUser(
  input: InviteUserInput,
): Promise<UserSummary> {
  return authenticatedRequest<UserSummary>("/api/v1/users/invite", {
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
  employment_type?: "EMPLOYEE" | "PARTNER" | "MEI";
  can_manage_ai_inbox?: boolean;
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

export async function deleteClient(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/clients/${id}`, {
    method: "DELETE",
  });
}

export async function deleteService(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/services/${id}`, {
    method: "DELETE",
  });
}

export async function deleteUser(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/users/${id}`, {
    method: "DELETE",
  });
}

export async function deleteSubscriptionPlan(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/subscription-plans/${id}`, {
    method: "DELETE",
  });
}

export async function deleteSubscription(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/subscriptions/${id}`, {
    method: "DELETE",
  });
}

export async function deleteFinancialAccount(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/finance/accounts/${id}`, {
    method: "DELETE",
  });
}

export async function deleteFinancialEntry(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/finance/entries/${id}`, {
    method: "DELETE",
  });
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

export async function updateFinancialAccount(
  id: string,
  changes: { name?: string; is_active?: boolean },
): Promise<FinancialAccount> {
  return authenticatedRequest<FinancialAccount>(
    `/api/v1/finance/accounts/${id}`,
    {
      method: "PATCH",
      body: JSON.stringify(changes),
    },
  );
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

export async function getMyCommission(
  fromDate: string,
  toDate: string,
): Promise<CommissionSummary> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<CommissionSummary>(
    `/api/v1/finance/my-commission?${params.toString()}`,
  );
}

export async function getMyCommissionRule(): Promise<MyCommissionRule> {
  return authenticatedRequest<MyCommissionRule>("/api/v1/users/me/commission");
}

export async function getAdminPayments(
  status?: AdminPayment["status"],
): Promise<AdminPayment[]> {
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const suffix = params.toString();
  return authenticatedRequest<AdminPayment[]>(
    `/api/v1/payments${suffix ? `?${suffix}` : ""}`,
  );
}

export async function confirmAdminPayment(
  paymentId: string,
): Promise<AdminPayment> {
  return authenticatedRequest<AdminPayment>(
    `/api/v1/payments/${paymentId}/confirm`,
    { method: "POST" },
  );
}

export type CreateInventoryItemInput = {
  name: string;
  unit: string;
  quantity: string;
  min_quantity: string;
  unit_cost: string;
  is_active?: boolean;
};

type UpdateInventoryItemInput = {
  name?: string;
  unit?: string;
  min_quantity?: string;
  unit_cost?: string;
  is_active?: boolean;
};

export async function getInventory(): Promise<InventoryItem[]> {
  return authenticatedRequest<InventoryItem[]>("/api/v1/inventory");
}

export async function createInventoryItem(
  input: CreateInventoryItemInput,
): Promise<InventoryItem> {
  return authenticatedRequest<InventoryItem>("/api/v1/inventory", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updateInventoryItem(
  id: string,
  changes: UpdateInventoryItemInput,
): Promise<InventoryItem> {
  return authenticatedRequest<InventoryItem>(`/api/v1/inventory/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function deleteInventoryItem(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/inventory/${id}`, {
    method: "DELETE",
  });
}

export async function addStockMovement(
  itemId: string,
  input: {
    kind: StockMovement["kind"];
    quantity: string;
    reason?: string | null;
    document_type?: StockDocumentType | null;
    document_number?: string | null;
    document_series?: string | null;
    supplier_name?: string | null;
    supplier_tax_id?: string | null;
    issue_date?: string | null;
    total_amount?: string | null;
    payment_method?: StockPaymentMethod | null;
    access_key?: string | null;
  },
): Promise<StockMovement> {
  return authenticatedRequest<StockMovement>(
    `/api/v1/inventory/${itemId}/movements`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function getStockMovements(
  itemId: string,
): Promise<StockMovement[]> {
  return authenticatedRequest<StockMovement[]>(
    `/api/v1/inventory/${itemId}/movements`,
  );
}

export type CreatePayrollInput = {
  user_id: string;
  kind: PayrollKind;
  description: string;
  amount: string;
  competence_date: string;
  status?: "PENDING" | "PAID";
  cash_date?: string | null;
  account_id?: string | null;
};

type UpdatePayrollInput = {
  kind?: PayrollKind;
  description?: string;
  amount?: string;
  competence_date?: string;
  status?: "PENDING" | "PAID";
  cash_date?: string | null;
  account_id?: string | null;
};

export async function getPayroll(
  fromDate: string,
  toDate: string,
): Promise<PayrollEntry[]> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<PayrollEntry[]>(
    `/api/v1/payroll?${params.toString()}`,
  );
}

export async function createPayroll(
  input: CreatePayrollInput,
): Promise<PayrollEntry> {
  return authenticatedRequest<PayrollEntry>("/api/v1/payroll", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function updatePayroll(
  id: string,
  changes: UpdatePayrollInput,
): Promise<PayrollEntry> {
  return authenticatedRequest<PayrollEntry>(`/api/v1/payroll/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function deletePayroll(id: string): Promise<void> {
  await authenticatedRequest<void>(`/api/v1/payroll/${id}`, {
    method: "DELETE",
  });
}

export async function getTitheSummary(
  fromDate: string,
  toDate: string,
): Promise<TitheSummary> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  return authenticatedRequest<TitheSummary>(
    `/api/v1/finance/tithe?${params.toString()}`,
  );
}

export async function createTitheDelivery(input: {
  competence_date: string;
  tithe_amount: string;
  offering_amount: string;
  note?: string | null;
}): Promise<TitheDelivery> {
  return authenticatedRequest<TitheDelivery>(
    "/api/v1/finance/tithe/deliveries",
    { method: "POST", body: JSON.stringify(input) },
  );
}

export async function deleteTitheDelivery(id: string): Promise<void> {
  await authenticatedRequest<void>(
    `/api/v1/finance/tithe/deliveries/${id}`,
    { method: "DELETE" },
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

export async function approveAiConversation(
  id: string,
): Promise<AiConversationDetail> {
  return authenticatedRequest<AiConversationDetail>(
    `/api/v1/ai/conversations/${id}/approve`,
    { method: "POST" },
  );
}

export async function simulateWhatsApp(input: {
  phone: string;
  text: string;
}): Promise<WhatsAppSimulationResult> {
  return authenticatedRequest<WhatsAppSimulationResult>(
    "/api/v1/ai/whatsapp/simulate",
    { method: "POST", body: JSON.stringify(input) },
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

export async function getBirthdayCredits(
  year?: string,
): Promise<BirthdayCredit[]> {
  const params = new URLSearchParams();
  if (year) params.set("year", year);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return authenticatedRequest<BirthdayCredit[]>(
    `/api/v1/ai/birthday-credits${suffix}`,
  );
}

export async function runBirthdayCredits(): Promise<BirthdayCreditRun> {
  return authenticatedRequest<BirthdayCreditRun>(
    "/api/v1/ai/birthday-credits/run",
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

export async function getAppointmentsRange(
  fromDate: string,
  toDate: string,
  collaboratorId?: string,
): Promise<Appointment[]> {
  const params = new URLSearchParams({
    from_date: fromDate,
    to_date: toDate,
  });
  if (collaboratorId) params.set("collaborator_id", collaboratorId);
  return authenticatedRequest<Appointment[]>(
    `/api/v1/appointments?${params.toString()}`,
  );
}

export async function getCheckinLink(
  appointmentId: string,
): Promise<{ url: string; token: string }> {
  return authenticatedRequest(
    `/api/v1/appointments/${appointmentId}/checkin-link`,
    { method: "POST" },
  );
}

export type PublicCheckin = {
  tenant_name: string;
  client_name: string;
  service_name: string;
  collaborator_name: string;
  starts_at: string;
  ends_at: string;
  status: string;
  checked_in_at: string | null;
  can_checkin: boolean;
};

export async function getPublicCheckin(
  slug: string,
  token: string,
): Promise<PublicCheckin> {
  return request<PublicCheckin>(
    `/api/v1/public/checkin/${encodeURIComponent(slug)}/${encodeURIComponent(token)}`,
  );
}

export async function confirmPublicCheckin(
  slug: string,
  token: string,
): Promise<PublicCheckin> {
  return request<PublicCheckin>(
    `/api/v1/public/checkin/${encodeURIComponent(slug)}/${encodeURIComponent(token)}`,
    { method: "POST" },
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

export type AppointmentUpdateInput = {
  status?:
    | "SCHEDULED"
    | "PENDING_DEPOSIT"
    | "CONFIRMED"
    | "CANCELLED"
    | "EXPIRED"
    | "COMPLETED"
    | "NO_SHOW";
  starts_at?: string;
  collaborator_id?: string;
  notes?: string | null;
};

export async function updateAppointment(
  id: string,
  changes: AppointmentUpdateInput,
): Promise<Appointment> {
  return authenticatedRequest<Appointment>(`/api/v1/appointments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export async function cancelAppointment(id: string): Promise<void> {
  await updateAppointment(id, { status: "CANCELLED" });
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
