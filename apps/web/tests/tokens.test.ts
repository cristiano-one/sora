import { beforeEach, describe, expect, it } from "vitest";

import {
  clearTokens,
  decodeJwtPayload,
  getAccessToken,
  getRefreshToken,
  isTokenExpired,
  saveTokens,
} from "../lib/tokens";

const storage = new Map<string, string>();

Object.defineProperty(window, "localStorage", {
  configurable: true,
  value: {
    clear: () => storage.clear(),
    getItem: (key: string) => storage.get(key) ?? null,
    removeItem: (key: string) => {
      storage.delete(key);
    },
    setItem: (key: string, value: string) => {
      storage.set(key, value);
    },
  },
});

function makeToken(payload: Record<string, unknown>): string {
  const encode = (value: Record<string, unknown>) =>
    window.btoa(JSON.stringify(value));

  return `${encode({ alg: "none" })}.${encode(payload)}.signature`;
}

describe("token helpers", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("salva, lê e limpa o par de tokens", () => {
    saveTokens({
      access_token: "access",
      refresh_token: "refresh",
      token_type: "bearer",
      expires_in: 900,
    });

    expect(getAccessToken()).toBe("access");
    expect(getRefreshToken()).toBe("refresh");

    clearTokens();

    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
  });

  it("decodifica o payload do JWT", () => {
    const token = makeToken({ sub: "user-1", role: "OWNER" });

    expect(decodeJwtPayload(token)).toEqual({ sub: "user-1", role: "OWNER" });
  });

  it("trata token inválido como expirado", () => {
    expect(decodeJwtPayload("invalido")).toBeNull();
    expect(isTokenExpired("invalido")).toBe(true);
  });

  it("identifica token expirado e token válido", () => {
    const now = Math.floor(Date.now() / 1000);

    expect(isTokenExpired(makeToken({ exp: now + 3600 }))).toBe(false);
    expect(isTokenExpired(makeToken({ exp: now - 10 }))).toBe(true);
  });
});
