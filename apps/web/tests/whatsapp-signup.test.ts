import { describe, expect, it } from "vitest";

import {
  isFacebookOrigin,
  parseEmbeddedSignupMessage,
} from "../lib/whatsapp-signup";

describe("parseEmbeddedSignupMessage", () => {
  it("extrai waba e phone_number_id de uma mensagem FINISH", () => {
    const parsed = parseEmbeddedSignupMessage(
      JSON.stringify({
        type: "WA_EMBEDDED_SIGNUP",
        event: "FINISH",
        data: {
          waba_id: "123456789",
          phone_number_id: "987654321",
        },
      }),
    );
    expect(parsed).toEqual({
      event: "FINISH",
      wabaId: "123456789",
      phoneNumberId: "987654321",
      errorMessage: null,
      currentStep: null,
    });
  });

  it("aceita objeto e evento CANCEL sem dados", () => {
    const parsed = parseEmbeddedSignupMessage({
      type: "WA_EMBEDDED_SIGNUP",
      event: "CANCEL",
      data: {},
    });
    expect(parsed).toEqual({
      event: "CANCEL",
      wabaId: null,
      phoneNumberId: null,
      errorMessage: null,
      currentStep: null,
    });
  });

  it("ignora mensagens de outros tipos e JSON inválido", () => {
    expect(
      parseEmbeddedSignupMessage({
        type: "OTHER_EVENT",
        event: "FINISH",
        data: { waba_id: "1" },
      }),
    ).toBeNull();
    expect(parseEmbeddedSignupMessage("{invalido")).toBeNull();
    expect(parseEmbeddedSignupMessage(null)).toBeNull();
  });
});

describe("isFacebookOrigin", () => {
  it("aceita somente HTTPS do domínio facebook.com", () => {
    expect(isFacebookOrigin("https://www.facebook.com")).toBe(true);
    expect(isFacebookOrigin("https://web.facebook.com")).toBe(true);
    expect(isFacebookOrigin("https://business.facebook.com")).toBe(true);
    expect(isFacebookOrigin("http://www.facebook.com")).toBe(false);
    expect(isFacebookOrigin("https://evilfacebook.com")).toBe(false);
    expect(isFacebookOrigin("https://facebook.com.evil.dev")).toBe(false);
    expect(isFacebookOrigin("")).toBe(false);
  });
});
