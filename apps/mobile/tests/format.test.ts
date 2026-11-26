import { describe, expect, it } from "vitest";

import {
  formatDateLabel,
  formatIsoDate,
  formatPrice,
  formatTime,
  shiftDate,
  todayInTenant,
} from "../src/format";
import { statusTone } from "../src/theme";

describe("mobile format helpers", () => {
  it("retorna a data de hoje no fuso da clínica", () => {
    expect(todayInTenant()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("avança e retrocede datas", () => {
    expect(shiftDate("2027-01-31", 1)).toBe("2027-02-01");
    expect(shiftDate("2027-01-01", -1)).toBe("2026-12-31");
  });

  it("formata horário e data ISO no fuso da clínica", () => {
    expect(formatTime("2027-01-11T13:00:00Z")).toBe("10:00");
    expect(formatIsoDate("2027-01-11T13:00:00Z")).toBe("11/01/2027");
    expect(formatDateLabel("2027-01-11")).toContain("11");
  });

  it("formata preço sem float", () => {
    expect(formatPrice("120.00")).toBe("R$ 120,00");
    expect(formatPrice("1234.5")).toBe("R$ 1.234,50");
    expect(formatPrice(null)).toBe("—");
  });

  it("mapeia tons de status", () => {
    expect(statusTone("CONFIRMED").color).toBe("#047857");
    expect(statusTone("PENDING_DEPOSIT").color).toBe("#b45309");
    expect(statusTone("NO_SHOW").color).toBe("#dc2626");
  });
});
