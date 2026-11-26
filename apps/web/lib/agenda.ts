export const TENANT_TIME_ZONE = "America/Sao_Paulo";

export function todayInTenant(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TENANT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

export function shiftDate(date: string, days: number): string {
  const parsed = new Date(`${date}T12:00:00Z`);
  parsed.setUTCDate(parsed.getUTCDate() + days);
  return parsed.toISOString().slice(0, 10);
}

export function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: TENANT_TIME_ZONE,
  }).format(new Date(iso));
}

export function formatDateLabel(date: string): string {
  const parsed = new Date(`${date}T12:00:00Z`);
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    timeZone: "UTC",
  }).format(parsed);
}

export function formatIsoDate(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: TENANT_TIME_ZONE,
  }).format(new Date(iso));
}

export function isoToTenantDate(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: TENANT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function isoToTenantTime(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: TENANT_TIME_ZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(iso));
}

export function formatDateOnly(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T12:00:00Z`));
}

export function toTenantIso(date: string, time: string): string {
  return new Date(`${date}T${time}:00-03:00`).toISOString();
}
