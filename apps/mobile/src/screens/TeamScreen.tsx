import { useEffect, useState } from "react";
import { ActivityIndicator, FlatList, Text, View } from "react-native";

import { ApiError, getUsers, type UserSummary } from "../api";
import { formatPrice } from "../format";
import { colors, ROLE_LABEL } from "../theme";
import { ui } from "../ui";

function commissionLabel(user: UserSummary): string {
  const parts: string[] = [];
  if (user.commission_percentage) parts.push(`${user.commission_percentage}%`);
  if (user.commission_fixed) parts.push(`fixo ${formatPrice(user.commission_fixed)}`);
  if (parts.length === 0) return "Sem comissão";
  return `${parts.join(" + ")} · ${user.commission_base === "GROSS" ? "bruto" : "líquido"}`;
}

export function TeamScreen() {
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    getUsers()
      .then((data) => {
        if (active) setUsers(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar equipe.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <View style={ui.screen}>
      <FlatList
        contentContainerStyle={ui.scroll}
        data={users}
        keyExtractor={(item) => item.id}
        ListHeaderComponent={
          <View>
            <View style={ui.header}>
              <View style={{ flex: 1 }}>
                <Text style={ui.title}>Equipe</Text>
                <Text style={ui.subtitle}>
                  Profissionais, papéis e regras de comissão.
                </Text>
              </View>
            </View>
            {error ? <Text style={ui.error}>{error}</Text> : null}
            {loading ? (
              <ActivityIndicator style={{ marginVertical: 24 }} color={colors.primary} />
            ) : null}
          </View>
        }
        ListEmptyComponent={
          loading ? undefined : <Text style={ui.empty}>Nenhum usuário encontrado.</Text>
        }
        renderItem={({ item }) => (
          <View style={ui.card}>
            <View style={ui.spaceBetween}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: colors.text, fontSize: 14, fontWeight: "700" }}>
                  {item.full_name}
                </Text>
                <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
                  {item.email}
                </Text>
              </View>
              <Text
                style={{
                  color: item.is_active ? colors.success : colors.muted,
                  fontSize: 11,
                  fontWeight: "700",
                }}
              >
                {item.is_active ? "Ativo" : "Inativo"}
              </Text>
            </View>
            <View
              style={{
                flexDirection: "row",
                justifyContent: "space-between",
                marginTop: 10,
                gap: 10,
              }}
            >
              <Text style={{ color: colors.primary, fontSize: 12, fontWeight: "700" }}>
                {ROLE_LABEL[item.role] ?? item.role}
              </Text>
              <Text style={{ color: colors.muted, fontSize: 11, flexShrink: 1, textAlign: "right" }}>
                {commissionLabel(item)}
              </Text>
            </View>
          </View>
        )}
      />
    </View>
  );
}
