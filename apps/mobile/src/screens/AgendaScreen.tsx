import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  Text,
  View,
} from "react-native";

import {
  ApiError,
  getAppointments,
  getUsers,
  updateAppointmentStatus,
  type Appointment,
  type Me,
} from "../api";
import {
  formatDateLabel,
  formatTime,
  shiftDate,
  todayInTenant,
} from "../format";
import { colors, STATUS_LABEL, statusTone } from "../theme";
import { ui } from "../ui";

export function AgendaScreen({ me }: { me: Me }) {
  const [date, setDate] = useState(todayInTenant());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [collaborators, setCollaborators] = useState<Map<string, string>>(
    new Map(),
  );
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isManager = me.role === "OWNER" || me.role === "ADMIN";

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      try {
        const [data, users] = await Promise.all([
          getAppointments(date),
          isManager ? getUsers() : Promise.resolve([]),
        ]);
        setAppointments(data);
        setCollaborators(
          new Map(users.map((user) => [user.id, user.full_name])),
        );
        setError(null);
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : "Falha ao carregar agenda.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [date, isManager],
  );

  useEffect(() => {
    // Fetch ao montar/trocar de data; o loading já nasce verdadeiro.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  function changeDate(nextDate: string) {
    setLoading(true);
    setError(null);
    setDate(nextDate);
  }

  const totalLabel = useMemo(
    () => `${appointments.length} agendamento(s)`,
    [appointments.length],
  );

  async function handleStatus(
    appointment: Appointment,
    status: "CONFIRMED" | "CANCELLED" | "COMPLETED" | "NO_SHOW",
  ) {
    setActionId(appointment.id);
    setError(null);
    try {
      await updateAppointmentStatus(appointment.id, status);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar status.",
      );
    } finally {
      setActionId(null);
    }
  }

  return (
    <View style={ui.screen}>
      <FlatList
        contentContainerStyle={ui.scroll}
        data={appointments}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />
        }
        ListHeaderComponent={
          <View>
            <View style={ui.header}>
              <View style={{ flex: 1 }}>
                <Text style={ui.title}>Agenda</Text>
                <Text style={ui.subtitle}>
                  {formatDateLabel(date)} · {totalLabel}
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
                <Text
                  style={{
                    color: colors.primary,
                    fontSize: 11,
                    fontWeight: "700",
                  }}
                >
                  {isManager ? "Visão total" : "Minha agenda"}
                </Text>
              </View>
            </View>

            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                gap: 8,
                marginBottom: 14,
              }}
            >
              <Pressable
                style={ui.buttonGhost}
                onPress={() => changeDate(shiftDate(date, -1))}
              >
                <Text style={ui.buttonGhostText}>←</Text>
              </Pressable>
              <Pressable
                style={[ui.buttonGhost, { flex: 1 }]}
                onPress={() => changeDate(todayInTenant())}
              >
                <Text style={ui.buttonGhostText}>{formatDateLabel(date)}</Text>
              </Pressable>
              <Pressable
                style={ui.buttonGhost}
                onPress={() => changeDate(shiftDate(date, 1))}
              >
                <Text style={ui.buttonGhostText}>→</Text>
              </Pressable>
            </View>

            {error ? <Text style={ui.error}>{error}</Text> : null}
            {loading ? (
              <ActivityIndicator style={{ marginVertical: 24 }} color={colors.primary} />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          loading ? undefined : (
            <Text style={ui.empty}>Nenhum agendamento neste dia.</Text>
          )
        }
        renderItem={({ item }) => {
          const tone = statusTone(item.status);
          const busy = actionId === item.id;
          return (
            <View style={ui.card}>
              <View style={ui.spaceBetween}>
                <View style={{ flexDirection: "row", gap: 12, flex: 1 }}>
                  <View style={{ width: 54 }}>
                    <Text
                      style={{
                        color: colors.text,
                        fontSize: 17,
                        fontWeight: "700",
                      }}
                    >
                      {formatTime(item.starts_at)}
                    </Text>
                    <Text style={{ color: colors.muted, fontSize: 11 }}>
                      {formatTime(item.ends_at)}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text
                      style={{
                        color: colors.text,
                        fontSize: 14,
                        fontWeight: "700",
                      }}
                    >
                      {item.client_name}
                      {item.subscription_id ? (
                        <Text style={{ color: colors.primary, fontSize: 10 }}>
                          {"  "}ASSINANTE
                        </Text>
                      ) : null}
                    </Text>
                    <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>
                      {item.service_name}
                    </Text>
                    {isManager ? (
                      <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
                        {collaborators.get(item.collaborator_id) ?? "Profissional"}
                      </Text>
                    ) : null}
                    {item.deposit_amount ? (
                      <Text style={{ color: colors.warning, fontSize: 11, marginTop: 2 }}>
                        Sinal R$ {item.deposit_amount}
                      </Text>
                    ) : null}
                  </View>
                </View>
                <View
                  style={{
                    backgroundColor: tone.background,
                    borderRadius: 999,
                    paddingHorizontal: 9,
                    paddingVertical: 4,
                  }}
                >
                  <Text
                    style={{
                      color: tone.color,
                      fontSize: 10,
                      fontWeight: "700",
                    }}
                  >
                    {STATUS_LABEL[item.status] ?? item.status}
                  </Text>
                </View>
              </View>

              {item.status !== "CANCELLED" &&
              item.status !== "COMPLETED" &&
              item.status !== "EXPIRED" ? (
                <View style={{ flexDirection: "row", gap: 8, marginTop: 12 }}>
                  {item.status !== "CONFIRMED" ? (
                    <Pressable
                      disabled={busy}
                      onPress={() => handleStatus(item, "CONFIRMED")}
                      style={[ui.buttonGhost, { borderColor: colors.success }]}
                    >
                      <Text style={[ui.buttonGhostText, { color: colors.success }]}>
                        {busy ? "..." : "Confirmar"}
                      </Text>
                    </Pressable>
                  ) : null}
                  <Pressable
                    disabled={busy}
                    onPress={() => handleStatus(item, "COMPLETED")}
                    style={ui.buttonGhost}
                  >
                    <Text style={ui.buttonGhostText}>Concluir</Text>
                  </Pressable>
                  <Pressable
                    disabled={busy}
                    onPress={() => handleStatus(item, "CANCELLED")}
                    style={[ui.buttonGhost, { borderColor: "#fecaca" }]}
                  >
                    <Text style={[ui.buttonGhostText, { color: colors.danger }]}>
                      Cancelar
                    </Text>
                  </Pressable>
                </View>
              ) : null}
            </View>
          );
        }}
      />
    </View>
  );
}
