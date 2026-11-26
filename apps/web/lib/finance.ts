import type { Dre } from "./api";

export type DreRow = {
  label: string;
  value: string;
  negative: boolean;
  highlight: boolean;
};

export function sumMoney(values: string[]): string {
  let cents = 0n;
  for (const value of values) {
    const trimmed = value.trim();
    const negative = trimmed.startsWith("-");
    const normalized = trimmed.replace(/[^0-9.]/g, "");
    const [whole = "0", fraction = ""] = normalized.split(".");
    const amount =
      BigInt(whole || "0") * 100n +
      BigInt(`${fraction}00`.slice(0, 2));
    cents += negative ? -amount : amount;
  }
  const sign = cents < 0n ? "-" : "";
  const absolute = cents < 0n ? -cents : cents;
  const fraction = (absolute % 100n).toString().padStart(2, "0");
  return `${sign}${absolute / 100n}.${fraction}`;
}

export function buildDreRows(dre: Dre): DreRow[] {
  const rows: DreRow[] = [
    {
      label: "Receita bruta",
      value: dre.gross_revenue,
      negative: false,
      highlight: false,
    },
    {
      label: "(-) Deduções e taxas",
      value: dre.deductions,
      negative: true,
      highlight: false,
    },
    {
      label: "(-) Custos e insumos",
      value: dre.costs,
      negative: true,
      highlight: false,
    },
    {
      label: "(-) Despesas operacionais",
      value: dre.operating_expenses,
      negative: true,
      highlight: false,
    },
    {
      label: "(=) Lucro líquido",
      value: dre.net_profit,
      negative: false,
      highlight: true,
    },
    {
      label: "Comissões apuradas",
      value: dre.commissions_accrued,
      negative: false,
      highlight: false,
    },
  ];

  if (dre.tithe_enabled) {
    rows.push(
      {
        label: "Dízimo",
        value: dre.tithe_amount,
        negative: true,
        highlight: false,
      },
      {
        label: "Oferta",
        value: dre.offering_amount,
        negative: true,
        highlight: false,
      },
      {
        label: "Após dízimo/oferta",
        value: dre.after_tithe_and_offering,
        negative: false,
        highlight: false,
      },
    );
  }

  return rows;
}
