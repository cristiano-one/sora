import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  Text,
  View,
} from "react-native";

import {
  ApiError,
  getAppointments,
  getClients,
  getMyCommission,
  type Appointment,
  type Me,
} from "../api";
import { formatDateLabel, formatPrice, formatTime, todayInTenant } from "../format";
import { supportsMedicalRecords } from "../profiles";
import { colors, ROLE_LABEL, statusTone } from "../theme";
import { ui } from "../ui";

export function HomeScreen({
  me,
  onOpenAgenda,
  onOpenClients,
  onOpenProfile,
}: {
  me: Me;
  onOpenAgenda: () => void;
  onOpenClients: () => void;
  onOpenProfile: () => void;
}) {
  const today = todayInTenant();
  const monthStart = `${today.slice(0, 7)}-01`;
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [clientsCount, setClientsCount] = useState(0);
  const [commission, setCommission] = useState("0.00");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (refresh = false) => {
      if (refresh) setRefreshing(true);
      try {
        const [agenda, clients, mine] = await Promise.all([
          getAppointments(today),
          getClients(),
          getMyCommission(monthStart, today),
        ]);
        setAppointments(agenda);
        setClientsCount(clients.length);
        setCommission(mine.total);
        setError(null);
      } catch (err) {
        setError(
          err instanceof ApiError ? err.message : "Falha ao carregar resumo.",
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [monthStart, today],
  );

  useEffect(() => {
    // Carga inicial do resumo.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const completed = appointments.filter(
    (item) => item.status === "COMPLETED",
  ).length;
  const checkedIn = appointments.filter((item) => item.checked_in_at).length;
  const next = appointments
    .filter(
      (item) =>
        !["CANCELLED", "EXPIRED", "NO_SHOW"].includes(item.status),
    )
    .slice(0, 4);

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
          <Text style={{ color: colors.primary, fontSize: 11, fontWeight: "700" }}>
            {ROLE_LABEL[me.role] ?? me.role} · {formatDateLabel(today)}
          </Text>
          <Text style={ui.title}>Olá, {me.full_name.split(" ")[0]}</Text>
          <Text style={ui.subtitle}>
            Seu resumo de hoje e os próximos atendimentos.
          </Text>
        </View>
        <View
          style={{
            width: 44,
            height: 44,
            borderRadius: 15,
            backgroundColor: colors.primarySoft,
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Text style={{ color: colors.primary, fontSize: 16, fontWeight: "800" }}>
            {me.full_name
              .split(" ")
              .slice(0, 2)
              .map((part) => part[0])
              .join("")
              .toUpperCase()}
          </Text>
        </View>
      </View>

      {error ? <Text style={ui.error}>{error}</Text> : null}

      {loading ? (
        <ActivityIndicator color={colors.primary} />
      ) : (
        <>
          <View style={{ flexDirection: "row", gap: 8, marginBottom: 14 }}>
            <View style={[ui.card, { flex: 1, marginBottom: 0 }]}>
              <Text style={{ color: colors.muted, fontSize: 9 }}>HOJE</Text>
              <Text style={{ color: colors.text, fontSize: 24, fontWeight: "800" }}>
                {appointments.length}
              </Text>
              <Text style={{ color: colors.muted, fontSize: 9 }}>
                {completed} concluído(s)
              </Text>
            </View>
            <View style={[ui.card, { flex: 1, marginBottom: 0 }]}>
              <Text style={{ color: colors.muted, fontSize: 9 }}>CHEGARAM</Text>
              <Text style={{ color: colors.text, fontSize: 24, fontWeight: "800" }}>
                {checkedIn}
              </Text>
              <Text style={{ color: colors.muted, fontSize: 9 }}>
                check-in digital
              </Text>
            </View>
            <View style={[ui.card, { flex: 1, marginBottom: 0 }]}>
              <Text style={{ color: colors.muted, fontSize: 9 }}>COMISSÃO</Text>
              <Text
                style={{ color: colors.success, fontSize: 17, fontWeight: "800" }}
              >
                {formatPrice(commission)}
              </Text>
              <Text style={{ color: colors.muted, fontSize: 9 }}>no mês</Text>
            </View>
          </View>

          <View style={{ flexDirection: "row", gap: 8, marginBottom: 18 }}>
            <Pressable
              onPress={onOpenAgenda}
              style={[ui.button, { flex: 1 }]}
            >
              <Text style={ui.buttonText}>Abrir agenda</Text>
            </Pressable>
            <Pressable
              onPress={onOpenClients}
              style={[ui.buttonGhost, { flex: 1 }]}
            >
              <Text style={ui.buttonGhostText}>Clientes</Text>
            </Pressable>
            <Pressable
              onPress={onOpenProfile}
              style={[ui.buttonGhost, { flex: 1 }]}
            >
              <Text style={ui.buttonGhostText}>Perfil</Text>
            </Pressable>
          </View>

          <Text style={ui.sectionTitle}>Próximos atendimentos</Text>
          {next.length === 0 ? (
            <Text style={ui.empty}>
              Nenhum atendimento restante hoje. Aproveite para revisar sua
              comissão ou cadastrar clientes.
            </Text>
          ) : (
            next.map((appointment) => {
              const tone = statusTone(appointment.status);
              return (
                <View
                  key={appointment.id}
                  style={[ui.card, { flexDirection: "row", gap: 10 }]}
                >
                  <View
                    style={{
                      width: 48,
                      borderRadius: 12,
                      backgroundColor: colors.primarySoft,
                      alignItems: "center",
                      justifyContent: "center",
                      paddingVertical: 8,
                    }}
                  >
                    <Text
                      style={{
                        color: colors.primary,
                        fontSize: 12,
                        fontWeight: "800",
                      }}
                    >
                      {formatTime(appointment.starts_at)}
                    </Text>
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text
                      style={{
                        color: colors.text,
                        fontSize: 13,
                        fontWeight: "700",
                      }}
                    >
                      {appointment.client_name}
                    </Text>
                    <Text style={{ color: colors.muted, fontSize: 11 }}>
                      {appointment.service_name}
                    </Text>
                    <View
                      style={{
                        flexDirection: "row",
                        flexWrap: "wrap",
                        gap: 6,
                        marginTop: 6,
                      }}
                    >
                      <Text
                        style={{
                          backgroundColor: tone.background,
                          color: tone.color,
                          borderRadius: 999,
                          paddingHorizontal: 7,
                          paddingVertical: 2,
                          fontSize: 9,
                          fontWeight: "700",
                        }}
                      >
                        {appointment.status}
                      </Text>
                      {appointment.checked_in_at ? (
                        <Text
                          style={{
                            backgroundColor: "#d1fae5",
                            color: colors.success,
                            borderRadius: 999,
                            paddingHorizontal: 7,
                            paddingVertical: 2,
                            fontSize: 9,
                            fontWeight: "700",
                          }}
                        >
                          Chegou
                        </Text>
                      ) : null}
                    </View>
                  </View>
                </View>
              );
            })
          )}

          <View style={[ui.card, { marginTop: 10 }]}>
            <Text style={{ color: colors.text, fontSize: 13, fontWeight: "700" }}>
              {clientsCount} cliente(s) na base
            </Text>
            <Text style={{ color: colors.muted, fontSize: 11, marginTop: 3 }}>
              {supportsMedicalRecords(me.business_profile)
                ? "Seu perfil usa prontuário e ficha clínica."
                : "Seu perfil usa ficha comercial, sem prontuário clínico."}
            </Text>
          </View>
        </>
      )}
    </ScrollView>
  );
}
