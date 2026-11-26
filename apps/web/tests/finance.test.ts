import { describe, expect, it } from "vitest";

import { buildDreRows, sumMoney } from "../lib/finance";
import type { Dre } from "../lib/api";

const baseDre: Dre = {
  from_date: "2026-11-01",
  to_date: "2026-11-30",
  gross_revenue: "1000.00",
  deductions: "10.00",
  costs: "20.00",
  operating_expenses: "100.00",
  net_profit: "870.00",
  commissions_accrued: "50.00",
  tithe_enabled: false,
  tithe_percentage: "10.00",
  tithe_amount: "0.00",
  offering_amount: "0.00",
  after_tithe_and_offering: "870.00",
};

describe("DRE rows", () => {  it("oculta dízimo, oferta e pós-dízimo quando desativado", () => {
    const labels = buildDreRows(baseDre).map((row) => row.label);
    expect(labels).not.toContain("Dízimo");
    expect(labels).not.toContain("Oferta");
    expect(labels).not.toContain("Após dízimo/oferta");
    expect(labels).toContain("(=) Lucro líquido");
  });

  it("mostra as linhas quando o dízimo está ativo", () => {
    const rows = buildDreRows({
      ...baseDre,
      tithe_enabled: true,
      tithe_amount: "87.00",
      offering_amount: "20.00",
      after_tithe_and_offering: "763.00",
    });
    const labels = rows.map((row) => row.label);
    expect(labels).toContain("Dízimo");
    expect(labels).toContain("Oferta");
    expect(labels).toContain("Após dízimo/oferta");
  });

  it("destaca apenas o lucro líquido", () => {
    const highlighted = buildDreRows(baseDre).filter((row) => row.highlight);
    expect(highlighted).toHaveLength(1);
    expect(highlighted[0].label).toBe("(=) Lucro líquido");
    expect(highlighted[0].value).toBe("870.00");
  });
});

describe("sumMoney", () => {
  it("soma valores decimais sem float", () => {
    expect(sumMoney(["100.10", "250.25", "-50.05"])).toBe("300.30");
  });

  it("retorna zero para lista vazia", () => {
    expect(sumMoney([])).toBe("0.00");
  });
});
