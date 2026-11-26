import { isoToTenantDate, shiftDate } from "./agenda";

export type MonthCell = {
  date: string;
  inMonth: boolean;
};

export function monthStart(date: string): string {
  return `${date.slice(0, 7)}-01`;
}

export function shiftMonth(month: string, delta: number): string {
  const parsed = new Date(`${monthStart(month)}T12:00:00Z`);
  parsed.setUTCMonth(parsed.getUTCMonth() + delta);
  return `${parsed.getUTCFullYear()}-${String(
    parsed.getUTCMonth() + 1,
  ).padStart(2, "0")}-01`;
}

export function monthLabel(month: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${monthStart(month)}T12:00:00Z`));
}

export function buildMonthCells(month: string): MonthCell[] {
  const first = monthStart(month);
  const weekday = new Date(`${first}T12:00:00Z`).getUTCDay();
  const mondayOffset = (weekday + 6) % 7;
  const gridStart = shiftDate(first, -mondayOffset);
  const cells: MonthCell[] = [];
  for (let index = 0; index < 42; index += 1) {
    const date = shiftDate(gridStart, index);
    cells.push({ date, inMonth: date.startsWith(first.slice(0, 7)) });
  }
  return cells;
}

export function monthRange(month: string): { from: string; to: string } {
  const cells = buildMonthCells(month);
  return { from: cells[0].date, to: cells[cells.length - 1].date };
}

export function monthBounds(month: string): { from: string; to: string } {
  const first = monthStart(month);
  const lastDay = new Date(
    Date.UTC(
      Number(first.slice(0, 4)),
      Number(first.slice(5, 7)),
      0,
    ),
  ).getUTCDate();
  return {
    from: first,
    to: `${first.slice(0, 8)}${String(lastDay).padStart(2, "0")}`,
  };
}

export function groupByDate<T extends { starts_at: string }>(
  items: T[],
): Record<string, T[]> {
  const groups: Record<string, T[]> = {};
  for (const item of items) {
    const date = isoToTenantDate(item.starts_at);
    groups[date] ??= [];
    groups[date].push(item);
  }
  for (const list of Object.values(groups)) {
    list.sort(
      (a, b) =>
        new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime(),
    );
  }
  return groups;
}

export function dayNumber(date: string): number {
  return Number(date.slice(8, 10));
}

export function isSameMonth(date: string, month: string): boolean {
  return date.startsWith(monthStart(month).slice(0, 7));
}
