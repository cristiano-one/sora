import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";

import {
  ApiError,
  getCommission,
  logout,
  type Commission,
  type Me,
} from "../api";
import { formatPrice } from "../format";
import { colors, ROLE_LABEL } from "../theme";
import { ui } from "../ui";

function commissionText(commission: Commission | null): string {
  if (!commission) return "Carregando…";
  const parts: string[] = [];
  if (commission.commission_percentage) {
    parts.push(`${commission.commission_percentage}%`);
  }
  if (commission.commission_fixed) {
    parts.push(`fixo ${formatPrice(commission.commission_fixed)}`);
  }
  if (parts.length === 0) return "Sem comissão configurada";
  const base = commission.commission_base === "GROSS" ? "bruto" : "líquido";
  return `${parts.join(" + ")} sobre o ${base}`;
}

export function ProfileScreen({
  me,
  onLoggedOut,
}: {
  me: Me;
  onLoggedOut: () => void;
}) {
  const [commission, setCommission] = useState<Commission | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    getCommission()
      .then((data) => {
        if (active) setCommission(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Falha ao carregar comissão.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleLogout() {
    setBusy(true);
    try {
      await logout();
    } finally {
      setBusy(false);
      onLoggedOut();
    }
  }

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.scroll}>
      <View style={ui.header}>
        <View style={{ flex: 1 }}>
          <Text style={ui.title}>Perfil</Text>
          <Text style={ui.subtitle}>Sua sessão e seus ganhos.</Text>
        </View>
      </View>

      <View style={ui.card}>
        <Text style={{ color: colors.text, fontSize: 20, fontWeight: "700" }}>
          {me.full_name}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4 }}>
          {me.email}
        </Text>
        <View
          style={{
            alignSelf: "flex-start",
            backgroundColor: colors.primarySoft,
            borderRadius: 999,
            paddingHorizontal: 10,
            paddingVertical: 4,
            marginTop: 10,
          }}
        >
          <Text style={{ color: colors.primary, fontSize: 11, fontWeight: "700" }}>
            {ROLE_LABEL[me.role] ?? me.role}
          </Text>
        </View>
      </View>

      <View style={ui.card}>
        <Text style={ui.sectionTitle}>Minha comissão</Text>
        <Text style={{ color: colors.text, fontSize: 16, fontWeight: "700" }}>
          {commissionText(commission)}
        </Text>
        <Text style={{ color: colors.muted, fontSize: 11, marginTop: 6 }}>
          A comissão detalhada por atendimento será exibida no módulo
          financeiro.
        </Text>
        {error ? <Text style={ui.error}>{error}</Text> : null}
      </View>

      <View style={ui.card}>
        <Text style={ui.sectionTitle}>Clínica</Text>
        <Text style={{ color: colors.muted, fontSize: 12 }}>
          Tenant: {me.tenant_id.slice(0, 8)}…
        </Text>
        <Text style={{ color: colors.muted, fontSize: 12, marginTop: 4 }}>
          Sora Studio Mobile · v0.1.0
        </Text>
      </View>

      <Pressable
        accessibilityRole="button"
        disabled={busy}
        onPress={handleLogout}
        style={[
          ui.buttonGhost,
          { borderColor: "#fecaca", marginTop: 4 },
          busy ? ui.buttonDisabled : null,
        ]}
      >
        <Text style={[ui.buttonGhostText, { color: colors.danger }]}>
          {busy ? "Saindo…" : "Sair da conta"}
        </Text>
      </Pressable>
    </ScrollView>
  );
}
