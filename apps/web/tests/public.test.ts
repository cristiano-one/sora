import { describe, expect, it } from "vitest";

import { billingCycleLabel, formatPrice, parseMagicToken } from "../lib/public";

describe("public booking helpers", () => {
  it("extrai o token do link mágico", () => {
    expect(parseMagicToken("?t=abc123")).toBe("abc123");
    expect(parseMagicToken("t=abc123&utm=whatsapp")).toBe("abc123");
  });

  it("rejeita token ausente ou vazio", () => {
    expect(parseMagicToken("")).toBeNull();
    expect(parseMagicToken("?utm=whatsapp")).toBeNull();
    expect(parseMagicToken("?t=%20")).toBeNull();
  });

  it("formata preço em reais sem usar float", () => {
    expect(formatPrice("120.00")).toBe("R$ 120,00");
    expect(formatPrice("1234.5")).toBe("R$ 1.234,50");
    expect(formatPrice("0.00")).toBe("R$ 0,00");
    expect(formatPrice(null)).toBeNull();
  });

  it("rotula o ciclo do plano", () => {
    expect(billingCycleLabel("MONTHLY")).toBe("por mês");
    expect(billingCycleLabel("QUARTERLY")).toBe("por trimestre");
  });
});
