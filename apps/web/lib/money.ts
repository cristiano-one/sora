export function normalizeDecimal(value: string): string {
  const cleaned = value
    .replace(/R\$/gi, "")
    .replace(/\s/g, "")
    .replace(/[^0-9,.-]/g, "");
  if (!cleaned || cleaned === "-" || cleaned === "," || cleaned === ".") {
    return "0";
  }

  const lastComma = cleaned.lastIndexOf(",");
  const lastDot = cleaned.lastIndexOf(".");

  if (lastComma >= 0 && lastDot >= 0) {
    if (lastComma > lastDot) {
      return cleaned.replace(/\./g, "").replace(",", ".");
    }
    return cleaned.replace(/,/g, "");
  }

  if (lastComma >= 0) {
    const parts = cleaned.split(",");
    if (parts.length === 2) {
      return `${parts[0].replace(/\./g, "")}.${parts[1]}`;
    }
    return cleaned.replace(/,/g, "");
  }

  return cleaned;
}

export function decimalToCents(value: string): number {
  const normalized = normalizeDecimal(value);
  const negative = normalized.startsWith("-");
  const [whole = "0", fraction = ""] = normalized
    .replace("-", "")
    .split(".");
  const cents =
    Number(whole || "0") * 100 +
    Number(`${fraction}00`.slice(0, 2));
  return negative ? -cents : cents;
}
