import { describe, expect, it } from "vitest";

import { decimalToCents, normalizeDecimal } from "../lib/money";

describe("normalizeDecimal", () => {
  it("converte vírgula brasileira para ponto", () => {
    expect(normalizeDecimal("20,00")).toBe("20.00");
    expect(normalizeDecimal("1,5")).toBe("1.5");
    expect(normalizeDecimal("R$ 1.234,56")).toBe("1234.56");
  });

  it("mantém valores com ponto", () => {
    expect(normalizeDecimal("20.00")).toBe("20.00");
    expect(normalizeDecimal("1,234.56")).toBe("1234.56");
  });

  it("trata entradas vazias ou parciais", () => {
    expect(normalizeDecimal("")).toBe("0");
    expect(normalizeDecimal(",")).toBe("0");
    expect(normalizeDecimal("0,0")).toBe("0.0");
  });

  it("converte para centavos sem float", () => {
    expect(decimalToCents("20,00")).toBe(2000);
    expect(decimalToCents("R$ 1.234,56")).toBe(123456);
    expect(decimalToCents("1,5")).toBe(150);
  });
});
