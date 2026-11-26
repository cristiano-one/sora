import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  addScoreEvent,
  ApiError,
  getClients,
  type Client,
} from "../api";
import { ClientRecordScreen } from "./ClientRecordScreen";
import { colors } from "../theme";
import { ui } from "../ui";

export function ClientsScreen() {
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedClient, setSelectedClient] = useState<Client | null>(null);

  const load = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    try {
      setClients(await getClients());
      setError(null);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao carregar clientes.",
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    // Fetch inicial; o loading já nasce verdadeiro.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return clients;
    return clients.filter(
      (client) =>
        client.full_name.toLowerCase().includes(term) ||
        client.phone.toLowerCase().includes(term),
    );
  }, [clients, search]);

  async function handleScore(
    client: Client,
    rating: "POSITIVE" | "NEGATIVE",
  ) {
    setActionId(client.id);
    setError(null);
    try {
      const result = await addScoreEvent(client.id, rating);
      setClients((current) =>
        current.map((item) =>
          item.id === client.id ? { ...item, score: result.score_after } : item,
        ),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao registrar score.",
      );
    } finally {
      setActionId(null);
    }
  }

  if (selectedClient) {
    return (
      <ClientRecordScreen
        client={selectedClient}
        onBack={() => setSelectedClient(null)}
      />
    );
  }

  return (
    <View style={ui.screen}>
      <FlatList
        contentContainerStyle={ui.scroll}
        data={filtered}
        keyExtractor={(item) => item.id}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={() => load(true)} />
        }
        ListHeaderComponent={
          <View>
            <View style={ui.header}>
              <View style={{ flex: 1 }}>
                <Text style={ui.title}>Clientes</Text>
                <Text style={ui.subtitle}>
                  Avaliação pós-atendimento e score confidencial.
                </Text>
              </View>
            </View>
            <TextInput
              style={ui.input}
              value={search}
              onChangeText={setSearch}
              placeholder="Buscar por nome ou telefone"
              placeholderTextColor="#94a3b8"
            />
            {error ? <Text style={ui.error}>{error}</Text> : null}
            {loading ? (
              <ActivityIndicator style={{ marginVertical: 24 }} color={colors.primary} />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          loading ? undefined : (
            <Text style={ui.empty}>Nenhum cliente encontrado.</Text>
          )
        }
        renderItem={({ item }) => {
          const busy = actionId === item.id;
          return (
            <View style={ui.card}>
              <View style={ui.spaceBetween}>
                <View style={{ flex: 1 }}>
                  <Text
                    style={{
                      color: colors.text,
                      fontSize: 14,
                      fontWeight: "700",
                    }}
                  >
                    {item.full_name}
                  </Text>
                  <Text style={{ color: colors.muted, fontSize: 12, marginTop: 2 }}>
                    {item.phone}
                  </Text>
                  {item.email ? (
                    <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
                      {item.email}
                    </Text>
                  ) : null}
                </View>
                <View style={{ alignItems: "flex-end", gap: 6 }}>
                  <View
                    style={{
                      backgroundColor: colors.primarySoft,
                      borderRadius: 999,
                      paddingHorizontal: 10,
                      paddingVertical: 4,
                    }}
                  >
                    <Text
                      style={{
                        color: colors.primary,
                        fontSize: 12,
                        fontWeight: "700",
                      }}
                    >
                      Score {item.score}
                    </Text>
                  </View>
                  {item.is_blocked ? (
                    <Text style={{ color: colors.danger, fontSize: 11, fontWeight: "700" }}>
                      Bloqueado
                    </Text>
                  ) : null}
                </View>
              </View>

              <View
                style={{
                  flexDirection: "row",
                  flexWrap: "wrap",
                  gap: 8,
                  marginTop: 12,
                }}
              >
                <Pressable
                  onPress={() => setSelectedClient(item)}
                  style={[ui.buttonGhost, { borderColor: colors.primary }]}
                >
                  <Text style={[ui.buttonGhostText, { color: colors.primary }]}>
                    Prontuário
                  </Text>
                </Pressable>
                <Pressable
                  disabled={busy}
                  onPress={() => handleScore(item, "POSITIVE")}
                  style={[ui.buttonGhost, { borderColor: "#a7f3d0" }]}
                >
                  <Text style={[ui.buttonGhostText, { color: colors.success }]}>
                    +5 positivo
                  </Text>
                </Pressable>
                <Pressable
                  disabled={busy}
                  onPress={() => handleScore(item, "NEGATIVE")}
                  style={[ui.buttonGhost, { borderColor: "#fecaca" }]}
                >
                  <Text style={[ui.buttonGhostText, { color: colors.danger }]}>
                    −10 negativo
                  </Text>
                </Pressable>
              </View>
            </View>
          );
        }}
      />
    </View>
  );
}
