import { describe, expect, it } from "vitest";

import {
  birthDateToIso,
  formatBirthDate,
  formatPhone,
  formatState,
  formatZip,
  isoToBirthDate,
  isValidBirthDate,
} from "../lib/masks";

describe("masks", () => {
  it("formata telefone fixo e celular", () => {
    expect(formatPhone("1133334444")).toBe("(11) 3333-4444");
    expect(formatPhone("11999998888")).toBe("(11) 99999-8888");
    expect(formatPhone("(11) 9")).toBe("(11) 9");
  });

  it("formata CEP", () => {
    expect(formatZip("01310100")).toBe("01310-100");
    expect(formatZip("01310-100")).toBe("01310-100");
  });

  it("formata e valida data de nascimento", () => {
    expect(formatBirthDate("01011990")).toBe("01/01/1990");
    expect(birthDateToIso("01/01/1990")).toBe("1990-01-01");
    expect(birthDateToIso("31/02/1990")).toBeNull();
    expect(isValidBirthDate("")).toBe(true);
    expect(isValidBirthDate("31/02/1990")).toBe(false);
    expect(isoToBirthDate("1990-01-01")).toBe("01/01/1990");
  });

  it("normaliza UF", () => {
    expect(formatState("sp")).toBe("SP");
    expect(formatState("s1p")).toBe("SP");
  });
});
