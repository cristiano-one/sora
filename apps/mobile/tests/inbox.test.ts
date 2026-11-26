import { describe, expect, it } from "vitest";

import type { AiConversation, Me } from "../src/api";
import {
  canAccessInbox,
  conversationPreview,
  conversationStatusLabel,
  conversationTitle,
  formatPhone,
} from "../src/inbox";

const baseConversation: AiConversation = {
  id: "c1",
  client_id: null,
  client_name: null,
  phone: "11999998888",
  status: "OPEN",
  needs_approval: false,
  approval_note: null,
  last_message: "Oi, quero agendar",
  last_message_at: "2026-11-26T12:00:00Z",
  last_intent: "booking",
};

function user(overrides: Partial<Me>): Me {
  return {
    id: "u1",
    tenant_id: "t1",
    email: "u@example.com",
    full_name: "User",
    role: "COLLABORATOR",
    business_profile: "AESTHETICS",
    can_manage_ai_inbox: false,
    ...overrides,
  };
}

describe("inbox helpers", () => {
  it("libera inbox para gestor, admin ou permissão explícita", () => {
    expect(canAccessInbox(user({ role: "OWNER" }))).toBe(true);
    expect(canAccessInbox(user({ role: "ADMIN" }))).toBe(true);
    expect(canAccessInbox(user({ can_manage_ai_inbox: true }))).toBe(true);
    expect(canAccessInbox(user({}))).toBe(false);
  });

  it("formata telefone brasileiro e usa nome do cliente quando existe", () => {
    expect(formatPhone("11999998888")).toBe("(11) 99999-8888");
    expect(formatPhone("1133334444")).toBe("(11) 3333-4444");
    expect(conversationTitle(baseConversation)).toBe("(11) 99999-8888");
    expect(
      conversationTitle({ ...baseConversation, client_name: "Ana" }),
    ).toBe("Ana");
  });

  it("resume status e última mensagem", () => {
    expect(conversationPreview(baseConversation)).toBe("Oi, quero agendar");
    expect(conversationStatusLabel(baseConversation)).toBe("SORA IA");
    expect(
      conversationStatusLabel({ ...baseConversation, needs_approval: true }),
    ).toBe("Aprovação");
    expect(
      conversationStatusLabel({ ...baseConversation, status: "HUMAN" }),
    ).toBe("Humano");
    expect(conversationPreview({ ...baseConversation, last_message: null })).toBe(
      "Sem mensagens ainda.",
    );
  });
});

describe("sortConversations", () => {
  it("prioriza aprovações, depois humano, abertas e encerradas", async () => {
    const { sortConversations } = await import("../src/inbox");
    const items: AiConversation[] = [
      { ...baseConversation, id: "closed", status: "CLOSED" },
      { ...baseConversation, id: "open", status: "OPEN" },
      { ...baseConversation, id: "human", status: "HUMAN" },
      { ...baseConversation, id: "approval", needs_approval: true },
    ];
    expect(sortConversations(items).map((item) => item.id)).toEqual([
      "approval",
      "human",
      "open",
      "closed",
    ]);
  });
});
