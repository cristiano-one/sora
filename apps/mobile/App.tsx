import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  SafeAreaView,
  StyleSheet,
  Text,
  View,
} from "react-native";
import { StatusBar } from "expo-status-bar";

import { getMe, getTenantSettings, type Me } from "./src/api";
import { hydrateTokens } from "./src/auth";
import { AgendaScreen } from "./src/screens/AgendaScreen";
import { ClientsScreen } from "./src/screens/ClientsScreen";
import { LoginScreen } from "./src/screens/LoginScreen";
import { ProfileScreen } from "./src/screens/ProfileScreen";
import { TeamScreen } from "./src/screens/TeamScreen";
import { colors } from "./src/theme";

type Tab = "agenda" | "clients" | "team" | "profile";

export default function App() {
  const [booting, setBooting] = useState(true);
  const [me, setMe] = useState<Me | null>(null);
  const [tab, setTab] = useState<Tab>("agenda");
  const [primary, setPrimary] = useState(colors.primary);

  const loadTheme = useCallback(async (user: Me) => {
    if (user.role !== "OWNER" && user.role !== "ADMIN") {
      setPrimary(colors.primary);
      return;
    }
    try {
      const settings = await getTenantSettings();
      setPrimary(settings.theme_primary_color);
    } catch {
      setPrimary(colors.primary);
    }
  }, []);

  useEffect(() => {
    let active = true;
    hydrateTokens()
      .then(() => getMe())
      .then((user) => {
        if (!active) return;
        setMe(user);
        void loadTheme(user);
      })
      .catch(() => {
        // Sem sessão válida: cai no login.
      })
      .finally(() => {
        if (active) setBooting(false);
      });
    return () => {
      active = false;
    };
  }, [loadTheme]);

  function handleLoggedIn(user: Me) {
    setMe(user);
    setTab("agenda");
    void loadTheme(user);
  }

  function handleLoggedOut() {
    setMe(null);
    setTab("agenda");
    setPrimary(colors.primary);
  }

  if (booting) {
    return (
      <SafeAreaView style={styles.center}>
        <StatusBar style="dark" />
        <ActivityIndicator color={colors.primary} />
        <Text style={styles.loading}>Carregando sessão…</Text>
      </SafeAreaView>
    );
  }

  if (!me) {
    return (
      <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
        <StatusBar style="dark" />
        <LoginScreen onLogged={handleLoggedIn} />
      </SafeAreaView>
    );
  }

  const isManager = me.role === "OWNER" || me.role === "ADMIN";
  const tabs: { key: Tab; label: string; icon: string }[] = [
    { key: "agenda", label: "Agenda", icon: "▤" },
    { key: "clients", label: "Clientes", icon: "◎" },
    ...(isManager ? [{ key: "team" as Tab, label: "Equipe", icon: "◈" }] : []),
    { key: "profile", label: "Perfil", icon: "◉" },
  ];

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.bg }}>
      <StatusBar style="dark" />
      <View style={{ flex: 1 }}>
        {tab === "agenda" ? <AgendaScreen me={me} /> : null}
        {tab === "clients" ? <ClientsScreen /> : null}
        {tab === "team" ? <TeamScreen /> : null}
        {tab === "profile" ? (
          <ProfileScreen me={me} onLoggedOut={handleLoggedOut} />
        ) : null}
      </View>

      <View style={styles.tabBar}>
        {tabs.map((item) => {
          const active = tab === item.key;
          return (
            <Pressable
              key={item.key}
              accessibilityRole="tab"
              accessibilityState={{ selected: active }}
              onPress={() => setTab(item.key)}
              style={styles.tab}
            >
              <Text
                style={[
                  styles.tabIcon,
                  { color: active ? primary : colors.muted },
                ]}
              >
                {item.icon}
              </Text>
              <Text
                style={[
                  styles.tabLabel,
                  { color: active ? primary : colors.muted },
                ]}
              >
                {item.label}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: colors.bg,
  },
  loading: {
    color: colors.muted,
    fontSize: 13,
    marginTop: 10,
  },
  tabBar: {
    flexDirection: "row",
    borderTopColor: colors.border,
    borderTopWidth: 1,
    backgroundColor: colors.surface,
    paddingTop: 8,
    paddingBottom: 10,
  },
  tab: {
    flex: 1,
    alignItems: "center",
    gap: 2,
  },
  tabIcon: {
    fontSize: 18,
  },
  tabLabel: {
    fontSize: 10,
    fontWeight: "700",
  },
});
