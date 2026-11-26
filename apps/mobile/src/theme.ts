export const colors = {
  primary: "#4f46e5",
  primaryDark: "#4338ca",
  primarySoft: "#eef2ff",
  bg: "#f8fafc",
  surface: "#ffffff",
  text: "#0f172a",
  muted: "#64748b",
  border: "#e2e8f0",
  danger: "#dc2626",
  success: "#047857",
  warning: "#b45309",
};

export const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

export const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: "Agendado",
  PENDING_DEPOSIT: "Aguardando sinal",
  CONFIRMED: "Confirmado",
  CANCELLED: "Cancelado",
  EXPIRED: "Expirado",
  COMPLETED: "Concluído",
  NO_SHOW: "Faltou",
};

export function statusTone(status: string): {
  background: string;
  color: string;
} {
  if (status === "CONFIRMED" || status === "COMPLETED") {
    return { background: "#ecfdf5", color: colors.success };
  }
  if (status === "PENDING_DEPOSIT") {
    return { background: "#fffbeb", color: colors.warning };
  }
  if (status === "CANCELLED" || status === "EXPIRED") {
    return { background: "#f1f5f9", color: colors.muted };
  }
  if (status === "NO_SHOW") {
    return { background: "#fef2f2", color: colors.danger };
  }
  return { background: colors.primarySoft, color: colors.primary };
}
