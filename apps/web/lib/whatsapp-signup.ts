export type EmbeddedSignupMessage = {
  event: string;
  wabaId: string | null;
  phoneNumberId: string | null;
  errorMessage: string | null;
  currentStep: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null
    ? (value as Record<string, unknown>)
    : null;
}

function asId(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

/**
 * Extrai o evento pós-login do Embedded Signup enviado pelo SDK do Facebook
 * via `window.postMessage` (`type: "WA_EMBEDDED_SIGNUP"`).
 */
export function parseEmbeddedSignupMessage(
  raw: unknown,
): EmbeddedSignupMessage | null {
  let value: unknown = raw;
  if (typeof value === "string") {
    try {
      value = JSON.parse(value);
    } catch {
      return null;
    }
  }
  const message = asRecord(value);
  if (!message || message.type !== "WA_EMBEDDED_SIGNUP") return null;
  const event = typeof message.event === "string" ? message.event : "";
  if (!event) return null;
  const data = asRecord(message.data) ?? {};
  return {
    event,
    wabaId: asId(data.waba_id),
    phoneNumberId: asId(data.phone_number_id),
    errorMessage:
      typeof data.error_message === "string" ? data.error_message : null,
    currentStep:
      typeof data.current_step === "string" ? data.current_step : null,
  };
}

/** Aceita somente origens HTTPS do domínio facebook.com (inclui subdomínios). */
export function isFacebookOrigin(origin: string): boolean {
  try {
    const url = new URL(origin);
    return (
      url.protocol === "https:" &&
      (url.hostname === "facebook.com" ||
        url.hostname.endsWith(".facebook.com"))
    );
  } catch {
    return false;
  }
}
