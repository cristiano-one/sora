import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import { ApiError, getMe, login } from "../api";
import { colors } from "../theme";
import { ui } from "../ui";

export function LoginScreen({
  onLogged,
}: {
  onLogged: (me: Awaited<ReturnType<typeof getMe>>) => void;
}) {
  const [tenantSlug, setTenantSlug] = useState("demo");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("demo12345");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogin() {
    setError(null);
    setBusy(true);
    try {
      await login({ tenant_slug: tenantSlug.trim(), email: email.trim(), password });
      const me = await getMe();
      onLogged(me);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível entrar. Verifique a conexão com a API.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: colors.bg }}
      behavior={Platform.OS === "ios" ? "padding" : undefined}
    >
      <ScrollView contentContainerStyle={{ flexGrow: 1, justifyContent: "center", padding: 22 }}>
        <View style={{ alignItems: "center", marginBottom: 22 }}>
          <View
            style={{
              width: 54,
              height: 54,
              borderRadius: 16,
              backgroundColor: colors.primary,
              alignItems: "center",
              justifyContent: "center",
              marginBottom: 14,
            }}
          >
            <Text style={{ color: "white", fontSize: 24, fontWeight: "700" }}>S</Text>
          </View>
          <Text style={ui.title}>Sora Studio</Text>
          <Text style={ui.subtitle}>Seu estúdio na palma da mão.</Text>
        </View>

        <View style={ui.card}>
          <Text style={ui.label}>Clínica (slug)</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            style={ui.input}
            value={tenantSlug}
            onChangeText={setTenantSlug}
            placeholder="demo"
            placeholderTextColor="#94a3b8"
          />
          <Text style={ui.label}>E-mail</Text>
          <TextInput
            autoCapitalize="none"
            autoCorrect={false}
            keyboardType="email-address"
            style={ui.input}
            value={email}
            onChangeText={setEmail}
            placeholder="voce@clinica.com"
            placeholderTextColor="#94a3b8"
          />
          <Text style={ui.label}>Senha</Text>
          <TextInput
            secureTextEntry
            style={ui.input}
            value={password}
            onChangeText={setPassword}
            placeholder="Sua senha"
            placeholderTextColor="#94a3b8"
          />
          <Pressable
            accessibilityRole="button"
            disabled={busy}
            onPress={handleLogin}
            style={[ui.button, busy ? ui.buttonDisabled : null]}
          >
            {busy ? (
              <ActivityIndicator color="white" />
            ) : (
              <Text style={ui.buttonText}>Entrar</Text>
            )}
          </Pressable>
          {error ? <Text style={ui.error}>{error}</Text> : null}
        </View>

        <Text style={[ui.subtitle, { textAlign: "center", marginTop: 14 }]}>
          Acesso seguro com JWT + refresh token no dispositivo.
        </Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
