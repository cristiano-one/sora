import { describe, expect, it } from "vitest";

import {
  buildMonthCells,
  dayNumber,
  groupByDate,
  monthBounds,
  monthLabel,
  monthRange,
  monthStart,
  shiftMonth,
} from "../lib/agenda-calendar";

describe("agenda calendar", () => {
  it("normaliza o início do mês e navega entre meses", () => {
    expect(monthStart("2026-11-26")).toBe("2026-11-01");
    expect(shiftMonth("2026-12-01", 1)).toBe("2027-01-01");
    expect(shiftMonth("2026-01-01", -1)).toBe("2025-12-01");
    expect(monthLabel("2026-11-01").toLowerCase()).toContain("novembro");
  });

  it("monta grade de 42 dias começando na segunda-feira", () => {
    const cells = buildMonthCells("2026-11-01");
    expect(cells).toHaveLength(42);
    expect(cells[0].date).toBe("2026-10-26");
    expect(cells[41].date).toBe("2026-12-06");
    expect(cells.filter((cell) => cell.inMonth)).toHaveLength(30);
    expect(cells[0].inMonth).toBe(false);
  });

  it("calcula o intervalo completo da grade", () => {
    expect(monthRange("2026-11-01")).toEqual({
      from: "2026-10-26",
      to: "2026-12-06",
    });
  });

  it("limita a consulta ao mês corrente (máximo 31 dias)", () => {
    expect(monthBounds("2026-11-01")).toEqual({
      from: "2026-11-01",
      to: "2026-11-30",
    });
    expect(monthBounds("2026-02-01")).toEqual({
      from: "2026-02-01",
      to: "2026-02-28",
    });
  });

  it("agrupa e ordena atendimentos pela data do tenant", () => {
    const grouped = groupByDate([
      {
        id: "b",
        starts_at: "2026-11-26T13:00:00-03:00",
      },
      {
        id: "a",
        starts_at: "2026-11-26T09:00:00-03:00",
      },
      {
        id: "c",
        starts_at: "2026-11-27T10:00:00-03:00",
      },
    ]);
    expect(grouped["2026-11-26"].map((item) => item.id)).toEqual(["a", "b"]);
    expect(grouped["2026-11-27"]).toHaveLength(1);
  });

  it("extrai o dia do calendário", () => {
    expect(dayNumber("2026-11-01")).toBe(1);
    expect(dayNumber("2026-11-26")).toBe(26);
  });
});
