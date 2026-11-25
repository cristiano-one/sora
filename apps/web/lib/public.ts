export function parseMagicToken(search: string): string | null {
  const token = new URLSearchParams(search).get("t")?.trim();
  return token ? token : null;
}

export function formatPrice(value: string | null): string | null {
  if (value === null) return null;
  const [integer, fraction = ""] = value.split(".");
  const cents = fraction.padEnd(2, "0").slice(0, 2);
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `R$ ${grouped},${cents}`;
}
