import { describe, expect, it } from "vitest";

import {
  formatTime,
  shiftDate,
  toTenantIso,
  todayInTenant,
} from "../lib/agenda";

describe("agenda helpers", () => {
  it("retorna a data de hoje no formato YYYY-MM-DD", () => {
    expect(todayInTenant()).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("avança e retrocede datas", () => {
    expect(shiftDate("2027-01-31", 1)).toBe("2027-02-01");
    expect(shiftDate("2027-01-01", -1)).toBe("2026-12-31");
  });

  it("formata o horário no fuso da clínica", () => {
    expect(formatTime("2027-01-11T13:00:00Z")).toBe("10:00");
  });

  it("converte data/hora da clínica para ISO UTC", () => {
    expect(toTenantIso("2027-01-11", "10:00")).toBe(
      "2027-01-11T13:00:00.000Z",
    );
  });
});
