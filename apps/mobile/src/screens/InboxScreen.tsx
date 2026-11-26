import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  ApiError,
  approveAiConversation,
  closeAiConversation,
  getAiCheckins,
  getAiConversation,
  getAiConversations,
  getAiSummary,
  sendAiConversationMessage,
  takeoverAiConversation,
  type AiCheckin,
  type AiConversation,
  type AiConversationDetail,
  type AiSummary,
  type Me,
} from "../api";
import {
  conversationPreview,
  conversationStatusLabel,
  conversationStatusTone,
  conversationTitle,
  sortConversations,
} from "../inbox";
import {
  formatDateLabel,
  formatTime,
  TENANT_TIME_ZONE,
  todayInTenant,
} from "../format";
import { colors } from "../theme";
import { ui } from "../ui";

function lastMessageLabel(iso: string): string {
  const day = new Intl.DateTimeFormat("en-CA", {
    timeZone: TENANT_TIME_ZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
  if (day === todayInTenant()) return formatTime(iso);
  return formatDateLabel(day);
}

function SummaryCard({
  label,
  value,
  note,
}: {
  label: string;
  value: number;
  note: string;
}) {
  return (
    <View style={[ui.card, { flex: 1, minWidth: "45%", marginBottom: 0 }]}>
      <Text style={{ color: colors.muted, fontSize: 9, fontWeight: "700" }}>
        {label}
      </Text>
      <Text
        style={{
          color: colors.text,
          fontSize: 24,
          fontWeight: "800",
          marginTop: 2,
        }}
      >
        {value}
      </Text>
      <Text style={{ color: colors.muted, fontSize: 9 }}>{note}</Text>
    </View>
  );
}

function MessageBubble({
  direction,
  content,
  createdAt,
}: {
  direction: "INBOUND" | "OUTBOUND";
  content: string;
  createdAt: string;
}) {
  const outbound = direction === "OUTBOUND";
  return (
    <View
      style={{
        alignSelf: outbound ? "flex-end" : "flex-start",
        maxWidth: "88%",
        marginBottom: 8,
      }}
    >
      <View
        style={{
          backgroundColor: outbound ? colors.primarySoft : colors.surface,
          borderColor: outbound ? "#c7d2fe" : colors.border,
          borderWidth: 1,
          borderRadius: 14,
          paddingHorizontal: 12,
          paddingVertical: 9,
        }}
      >
        <Text
          style={{
            color: colors.text,
            fontSize: 13,
            lineHeight: 19,
          }}
        >
          {content}
        </Text>
      </View>
      <Text
        style={{
          color: colors.muted,
          fontSize: 9,
          marginTop: 3,
          textAlign: outbound ? "right" : "left",
        }}
      >
        {formatTime(createdAt)}
      </Text>
    </View>
  );
}

export function InboxScreen({ me }: { me: Me }) {
  const today = todayInTenant();
  const [summary, setSummary] = useState<AiSummary | null>(null);
  const [conversations, setConversations] = useState<AiConversation[]>([]);
  const [checkins, setCheckins] = useState<AiCheckin[]>([]);
  const [selected, setSelected] = useState<AiConversationDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reply, setReply] = useState("");
  const sortedConversations = useMemo(
    () => sortConversations(conversations),
    [conversations],
  );

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      try {
        const [data, items, agenda] = await Promise.all([
          getAiSummary(today),
          getAiConversations(),
          getAiCheckins(today),
        ]);
        setSummary(data);
        setConversations(items);
        setCheckins(agenda);
        setError(null);
      } catch (err) {
        setError(
          err instanceof ApiError
            ? err.message
            : "Falha ao carregar o atendimento.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [today],
  );

  useEffect(() => {
    // Carga inicial do inbox.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function applyDetail(detail: AiConversationDetail) {
    setSelected(detail);
    setConversations((current) =>
      current.map((item) =>
        item.id === detail.id
          ? {
              ...item,
              status: detail.status,
              needs_approval: detail.needs_approval,
              approval_note: detail.approval_note,
              last_message: detail.last_message,
              last_message_at: detail.last_message_at,
            }
          : item,
      ),
    );
  }

  async function openConversation(id: string) {
    setDetailLoading(true);
    setError(null);
    setSelected(null);
    try {
      setSelected(await getAiConversation(id));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao abrir a conversa.",
      );
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshDetail(id: string) {
    applyDetail(await getAiConversation(id));
  }

  async function handleTakeover() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      applyDetail(await takeoverAiConversation(selected.id));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao assumir a conversa.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleApprove() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      applyDetail(await approveAiConversation(selected.id));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao aprovar a exceção.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleClose() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      applyDetail(await closeAiConversation(selected.id));
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao encerrar a conversa.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function handleSend() {
    if (!selected || !reply.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await sendAiConversationMessage(selected.id, reply.trim());
      setReply("");
      await refreshDetail(selected.id);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao enviar a mensagem.",
      );
    } finally {
      setBusy(false);
    }
  }

  function confirmClose() {
    Alert.alert(
      "Encerrar conversa",
      "A SORA IA não continuará respondendo até o cliente voltar a falar.",
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Encerrar",
          style: "destructive",
          onPress: () => void handleClose(),
        },
      ],
    );
  }

  if (detailLoading) {
    return (
      <View style={[ui.screen, { padding: 18 }]}>
        <ActivityIndicator color={colors.primary} />
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 8 }}>
          Abrindo conversa…
        </Text>
      </View>
    );
  }

  if (selected) {
    const tone = conversationStatusTone(selected);
    return (
      <KeyboardAvoidingView
        style={ui.screen}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={ui.scroll}>
          <Pressable
            onPress={() => {
              setSelected(null);
              setError(null);
              void load();
            }}
            style={{ marginBottom: 12 }}
          >
            <Text style={{ color: colors.primary, fontSize: 13, fontWeight: "700" }}>
              ← Voltar ao atendimento
            </Text>
          </Pressable>

          <View style={ui.header}>
            <View style={{ flex: 1 }}>
              <Text style={ui.title}>{conversationTitle(selected)}</Text>
              <Text style={ui.subtitle}>{selected.phone}</Text>
            </View>
            <Text
              style={{
                backgroundColor: tone.background,
                color: tone.color,
                borderRadius: 999,
                paddingHorizontal: 9,
                paddingVertical: 4,
                fontSize: 10,
                fontWeight: "700",
              }}
            >
              {conversationStatusLabel(selected)}
            </Text>
          </View>

          {error ? <Text style={ui.error}>{error}</Text> : null}

          {selected.needs_approval ? (
            <View
              style={{
                backgroundColor: "#fffbeb",
                borderColor: "#fde68a",
                borderWidth: 1,
                borderRadius: 12,
                padding: 12,
                marginBottom: 12,
              }}
            >
              <Text style={{ color: colors.warning, fontSize: 11, fontWeight: "700" }}>
                APROVAÇÃO PENDENTE
              </Text>
              <Text style={{ color: "#92400e", fontSize: 12, marginTop: 4 }}>
                {selected.approval_note ?? "Cliente pediu uma exceção."}
              </Text>
            </View>
          ) : null}

          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
            {selected.status !== "HUMAN" && selected.status !== "CLOSED" ? (
              <Pressable
                onPress={handleTakeover}
                disabled={busy}
                style={[ui.button, { flexGrow: 1 }, busy ? ui.buttonDisabled : null]}
              >
                <Text style={ui.buttonText}>
                  {busy ? "Aguarde…" : "Assumir conversa"}
                </Text>
              </Pressable>
            ) : null}
            {selected.needs_approval ? (
              <Pressable
                onPress={handleApprove}
                disabled={busy}
                style={[ui.button, { flexGrow: 1 }, busy ? ui.buttonDisabled : null]}
              >
                <Text style={ui.buttonText}>Aprovar exceção</Text>
              </Pressable>
            ) : null}
            {selected.status !== "CLOSED" ? (
              <Pressable
                onPress={confirmClose}
                disabled={busy}
                style={[ui.buttonGhost, { flexGrow: 1 }]}
              >
                <Text style={ui.buttonGhostText}>Encerrar</Text>
              </Pressable>
            ) : null}
          </View>

          {selected.messages.map((message) => (
            <MessageBubble
              key={message.id}
              direction={message.direction}
              content={message.content}
              createdAt={message.created_at}
            />
          ))}

          {selected.status === "HUMAN" ? (
            <View style={{ marginTop: 14 }}>
              <Text style={ui.label}>Responder pelo WhatsApp</Text>
              <TextInput
                style={[ui.input, { minHeight: 84, textAlignVertical: "top" }]}
                value={reply}
                onChangeText={setReply}
                multiline
                maxLength={2000}
                placeholder="Digite a resposta para o cliente…"
              />
              <Pressable
                onPress={handleSend}
                disabled={busy || !reply.trim()}
                style={[
                  ui.button,
                  busy || !reply.trim() ? ui.buttonDisabled : null,
                ]}
              >
                <Text style={ui.buttonText}>
                  {busy ? "Enviando…" : "Enviar resposta"}
                </Text>
              </Pressable>
            </View>
          ) : (
            <Text style={[ui.empty, { marginTop: 14 }]}>
              {selected.status === "CLOSED"
                ? "Conversa encerrada. O cliente pode iniciar um novo atendimento."
                : "Assuma a conversa para responder manualmente."}
            </Text>
          )}
        </ScrollView>
      </KeyboardAvoidingView>
    );
  }

  return (
    <ScrollView
      style={ui.screen}
      contentContainerStyle={ui.scroll}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={() => load(true)}
          tintColor={colors.primary}
        />
      }
    >
      <View style={ui.header}>
        <View style={{ flex: 1 }}>
          <Text style={ui.title}>Atendimento</Text>
          <Text style={ui.subtitle}>
            Inbox da secretária, aprovações e clientes na recepção.
          </Text>
        </View>
        <View
          style={{
            backgroundColor: colors.primarySoft,
            borderRadius: 999,
            paddingHorizontal: 10,
            paddingVertical: 5,
          }}
        >
          <Text style={{ color: colors.primary, fontSize: 10, fontWeight: "700" }}>
            {me.role === "OWNER" || me.role === "ADMIN"
              ? "Visão total"
              : "Recepção"}
          </Text>
        </View>
      </View>

      {error ? <Text style={ui.error}>{error}</Text> : null}

      {loading ? (
        <ActivityIndicator color={colors.primary} style={{ marginVertical: 24 }} />
      ) : (
        <>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
            <SummaryCard
              label="ABERTAS"
              value={summary?.open_conversations ?? 0}
              note="SORA IA"
            />
            <SummaryCard
              label="HUMANO"
              value={summary?.human_conversations ?? 0}
              note="em atendimento"
            />
            <SummaryCard
              label="APROVAÇÕES"
              value={summary?.approvals_pending ?? 0}
              note="pendentes"
            />
            <SummaryCard
              label="MENSAGENS"
              value={summary?.messages_today ?? 0}
              note="hoje"
            />
          </View>

          <Text style={ui.sectionTitle}>Na recepção</Text>
          {checkins.length === 0 ? (
            <Text style={[ui.empty, { marginBottom: 16 }]}>
              Nenhum cliente aguardando check-in.
            </Text>
          ) : (
            checkins.map((checkin) => (
              <View
                key={checkin.appointment_id}
                style={[ui.card, { flexDirection: "row", gap: 10 }]}
              >
                <View
                  style={{
                    width: 46,
                    borderRadius: 12,
                    backgroundColor: "#ecfdf5",
                    alignItems: "center",
                    justifyContent: "center",
                    paddingVertical: 8,
                  }}
                >
                  <Text style={{ color: colors.success, fontSize: 12, fontWeight: "800" }}>
                    {formatTime(checkin.starts_at)}
                  </Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: colors.text, fontSize: 13, fontWeight: "700" }}>
                    {checkin.client_name}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 11 }}>
                    {checkin.service_name} · {checkin.collaborator_name}
                  </Text>
                  <Text style={{ color: colors.success, fontSize: 10, marginTop: 3, fontWeight: "700" }}>
                    Check-in confirmado
                  </Text>
                </View>
              </View>
            ))
          )}

          <Text style={ui.sectionTitle}>Conversas</Text>
          {sortedConversations.length === 0 ? (
            <Text style={ui.empty}>
              Nenhuma conversa ainda. Quando um cliente chamar no WhatsApp, ela
              aparece aqui.
            </Text>
          ) : (
            sortedConversations.map((conversation) => {
              const tone = conversationStatusTone(conversation);
              return (
                <Pressable
                  key={conversation.id}
                  onPress={() => void openConversation(conversation.id)}
                  style={ui.card}
                >
                  <View style={ui.spaceBetween}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: colors.text, fontSize: 14, fontWeight: "700" }}>
                        {conversationTitle(conversation)}
                      </Text>
                      <Text style={{ color: colors.muted, fontSize: 10, marginTop: 2 }}>
                        {conversation.phone}
                      </Text>
                    </View>
                    <View style={{ alignItems: "flex-end", gap: 4 }}>
                      <Text
                        style={{
                          backgroundColor: tone.background,
                          color: tone.color,
                          borderRadius: 999,
                          paddingHorizontal: 8,
                          paddingVertical: 3,
                          fontSize: 9,
                          fontWeight: "700",
                        }}
                      >
                        {conversationStatusLabel(conversation)}
                      </Text>
                      <Text style={{ color: colors.muted, fontSize: 9 }}>
                        {lastMessageLabel(conversation.last_message_at)}
                      </Text>
                    </View>
                  </View>
                  <Text
                    numberOfLines={2}
                    style={{ color: colors.muted, fontSize: 12, marginTop: 8, lineHeight: 17 }}
                  >
                    {conversationPreview(conversation)}
                  </Text>
                </Pressable>
              );
            })
          )}
        </>
      )}
    </ScrollView>
  );
}
