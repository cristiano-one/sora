import type { AiConversation, Me } from "./api";

export function canAccessInbox(me: Me): boolean {
  return (
    me.role === "OWNER" ||
    me.role === "ADMIN" ||
    me.can_manage_ai_inbox
  );
}

export function formatPhone(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 11) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 2)}) ${digits.slice(2, 6)}-${digits.slice(6)}`;
  }
  return phone;
}

export function conversationTitle(conversation: AiConversation): string {
  return conversation.client_name?.trim() || formatPhone(conversation.phone);
}

export function conversationPreview(conversation: AiConversation): string {
  return conversation.last_message?.trim() || "Sem mensagens ainda.";
}

export function conversationStatusLabel(
  conversation: AiConversation,
): string {
  if (conversation.needs_approval) return "Aprovação";
  if (conversation.status === "HUMAN") return "Humano";
  if (conversation.status === "CLOSED") return "Encerrada";
  return "SORA IA";
}

export function conversationStatusTone(conversation: AiConversation): {
  background: string;
  color: string;
} {
  if (conversation.needs_approval) {
    return { background: "#fffbeb", color: "#b45309" };
  }
  if (conversation.status === "HUMAN") {
    return { background: "#eef2ff", color: "#4f46e5" };
  }
  if (conversation.status === "CLOSED") {
    return { background: "#f1f5f9", color: "#64748b" };
  }
  return { background: "#ecfdf5", color: "#047857" };
}

function inboxPriority(conversation: AiConversation): number {
  if (conversation.needs_approval) return 0;
  if (conversation.status === "HUMAN") return 1;
  if (conversation.status === "OPEN") return 2;
  return 3;
}

export function sortConversations(
  conversations: AiConversation[],
): AiConversation[] {
  return [...conversations].sort((left, right) => {
    const priority = inboxPriority(left) - inboxPriority(right);
    if (priority !== 0) return priority;
    return (
      new Date(right.last_message_at).getTime() -
      new Date(left.last_message_at).getTime()
    );
  });
}
