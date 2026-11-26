import * as FileSystem from "expo-file-system/legacy";
import * as ImagePicker from "expo-image-picker";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";

import {
  addLgpdConsent,
  ApiError,
  createMedicalRecord,
  deleteAttachment,
  getAttachmentUrl,
  getMedicalRecords,
  getMe,
  presignAttachment,
  type Client,
  type MedicalRecord,
  type Me,
} from "../api";
import { formatIsoDate } from "../format";
import { colors } from "../theme";
import { ui } from "../ui";

function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function ClientRecordScreen({
  client,
  onBack,
}: {
  client: Client;
  onBack: () => void;
}) {
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [attachmentBusy, setAttachmentBusy] = useState<string | null>(null);
  const [role, setRole] = useState<Me["role"] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    setRecords(await getMedicalRecords(client.id));
  }, [client.id]);

  useEffect(() => {
    let active = true;
    Promise.all([getMedicalRecords(client.id), getMe()])
      .then(([data, me]) => {
        if (!active) return;
        setRecords(data);
        setRole(me.role);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar prontuário.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [client.id]);

  async function handleCreateRecord() {
    setError(null);
    setNotice(null);
    if (!title.trim() || !notes.trim()) {
      setError("Informe título e notas clínicas.");
      return;
    }
    setSaving(true);
    try {
      await createMedicalRecord(client.id, {
        title: title.trim(),
        notes: notes.trim(),
      });
      setTitle("");
      setNotes("");
      await load();
      setNotice("Evolução registrada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar evolução.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleConsent() {
    setError(null);
    setNotice(null);
    try {
      await addLgpdConsent(client.id);
      setNotice("Consentimento LGPD registrado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao registrar consentimento.",
      );
    }
  }

  async function handleAttachment(
    record: MedicalRecord,
    source: "camera" | "library",
  ) {
    setError(null);
    setNotice(null);
    try {
      if (source === "camera") {
        const permission = await ImagePicker.requestCameraPermissionsAsync();
        if (!permission.granted) {
          setError("Permissão de câmera negada.");
          return;
        }
      } else {
        const permission =
          await ImagePicker.requestMediaLibraryPermissionsAsync();
        if (!permission.granted) {
          setError("Permissão de galeria negada.");
          return;
        }
      }
      const result =
        source === "camera"
          ? await ImagePicker.launchCameraAsync({
              mediaTypes: ["images"],
              quality: 0.8,
            })
          : await ImagePicker.launchImageLibraryAsync({
              mediaTypes: ["images"],
              quality: 0.8,
            });
      if (result.canceled || result.assets.length === 0) return;
      const asset = result.assets[0];
      const info = await FileSystem.getInfoAsync(asset.uri);
      const size = info.exists ? (info.size ?? 1) : (asset.fileSize ?? 1);
      const contentType = asset.mimeType ?? "image/jpeg";
      setAttachmentBusy(record.id);
      const presign = await presignAttachment(client.id, record.id, {
        filename: asset.fileName ?? "foto-camera.jpg",
        content_type: contentType,
        size_bytes: size,
      });
      const upload = await FileSystem.uploadAsync(
        presign.upload_url,
        asset.uri,
        {
          httpMethod: "PUT",
          uploadType: FileSystem.FileSystemUploadType.BINARY_CONTENT,
          headers: { "Content-Type": contentType },
        },
      );
      if (upload.status >= 300) {
        throw new Error("Falha no upload do anexo.");
      }
      await load();
      setNotice("Anexo enviado.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Falha ao anexar arquivo.",
      );
    } finally {
      setAttachmentBusy(null);
    }
  }

  async function openAttachment(
    record: MedicalRecord,
    attachmentId: string,
  ) {
    try {
      const data = await getAttachmentUrl(client.id, record.id, attachmentId);
      await Linking.openURL(data.url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao abrir anexo.");
    }
  }

  async function deleteRecordAttachment(
    record: MedicalRecord,
    attachmentId: string,
  ) {
    setError(null);
    setNotice(null);
    setAttachmentBusy(record.id);
    try {
      await deleteAttachment(client.id, record.id, attachmentId);
      await load();
      setNotice("Anexo excluído.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir anexo.",
      );
    } finally {
      setAttachmentBusy(null);
    }
  }

  function confirmDeleteAttachment(
    record: MedicalRecord,
    attachmentId: string,
    filename: string,
  ) {
    Alert.alert("Excluir anexo", `Excluir "${filename}"?`, [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Excluir",
        style: "destructive",
        onPress: () => {
          void deleteRecordAttachment(record, attachmentId);
        },
      },
    ]);
  }

  const isManager = role === "OWNER" || role === "ADMIN";

  return (
    <ScrollView style={ui.screen} contentContainerStyle={ui.scroll}>
      <View style={ui.header}>
        <View style={{ flex: 1 }}>
          <Pressable onPress={onBack}>
            <Text style={{ color: colors.primary, fontSize: 12, fontWeight: "700" }}>
              ← Clientes
            </Text>
          </Pressable>
          <Text style={ui.title}>{client.full_name}</Text>
          <Text style={ui.subtitle}>
            {client.phone} · Score {client.score}
            {client.is_blocked ? " · Bloqueado" : ""}
          </Text>
        </View>
        <Pressable style={ui.buttonGhost} onPress={handleConsent}>
          <Text style={ui.buttonGhostText}>Consentimento LGPD</Text>
        </Pressable>
      </View>

      {error ? <Text style={ui.error}>{error}</Text> : null}
      {notice ? (
        <Text style={{ color: colors.success, fontSize: 12, marginVertical: 8 }}>
          {notice}
        </Text>
      ) : null}

      <Text style={ui.sectionTitle}>Evolução clínica</Text>
      {loading ? (
        <ActivityIndicator color={colors.primary} />
      ) : records.length === 0 ? (
        <Text style={ui.empty}>Nenhuma evolução registrada.</Text>
      ) : (
        records.map((record) => (
          <View style={ui.card} key={record.id}>
            <Text style={{ color: colors.text, fontSize: 14, fontWeight: "700" }}>
              {record.title}
            </Text>
            <Text style={{ color: colors.muted, fontSize: 11, marginTop: 2 }}>
              {formatIsoDate(record.created_at)}
            </Text>
            <Text
              style={{
                color: colors.text,
                fontSize: 13,
                lineHeight: 19,
                marginTop: 8,
              }}
            >
              {record.notes}
            </Text>

            {record.attachments.map((attachment) => (
              <View
                key={attachment.id}
                style={{
                  flexDirection: "row",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                  marginTop: 8,
                }}
              >
                <Pressable
                  style={{ flex: 1 }}
                  onPress={() => openAttachment(record, attachment.id)}
                >
                  <Text style={{ color: colors.primary, fontSize: 12 }}>
                    {attachment.filename} · {fileSize(attachment.size_bytes)} ·
                    abrir
                  </Text>
                </Pressable>
                {isManager ? (
                  <Pressable
                    disabled={attachmentBusy === record.id}
                    onPress={() =>
                      confirmDeleteAttachment(
                        record,
                        attachment.id,
                        attachment.filename,
                      )
                    }
                  >
                    <Text style={{ color: colors.danger, fontSize: 12 }}>
                      Excluir
                    </Text>
                  </Pressable>
                ) : null}
              </View>
            ))}

            <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}>
              <Pressable
                style={ui.buttonGhost}
                disabled={attachmentBusy === record.id}
                onPress={() => handleAttachment(record, "camera")}
              >
                <Text style={ui.buttonGhostText}>
                  {attachmentBusy === record.id ? "Enviando…" : "Câmera"}
                </Text>
              </Pressable>
              <Pressable
                style={ui.buttonGhost}
                disabled={attachmentBusy === record.id}
                onPress={() => handleAttachment(record, "library")}
              >
                <Text style={ui.buttonGhostText}>Galeria</Text>
              </Pressable>
            </View>
          </View>
        ))
      )}

      <View style={ui.card}>
        <Text style={ui.sectionTitle}>Nova evolução</Text>
        <Text style={ui.label}>Título</Text>
        <TextInput
          style={ui.input}
          value={title}
          onChangeText={setTitle}
          placeholder="Ex.: avaliação pós-atendimento"
          placeholderTextColor="#94a3b8"
        />
        <Text style={ui.label}>Notas clínicas</Text>
        <TextInput
          style={[ui.input, { minHeight: 100, textAlignVertical: "top" }]}
          value={notes}
          onChangeText={setNotes}
          multiline
          placeholder="Evolução, orientações e intercorrências"
          placeholderTextColor="#94a3b8"
        />
        <Pressable
          style={[ui.button, saving ? ui.buttonDisabled : null]}
          disabled={saving}
          onPress={handleCreateRecord}
        >
          <Text style={ui.buttonText}>
            {saving ? "Salvando…" : "Registrar evolução"}
          </Text>
        </Pressable>
      </View>

      <Text style={ui.subtitle}>
        Notas cifradas no banco. Fotos usam bucket privado e URLs temporárias de
        60 segundos.
      </Text>
    </ScrollView>
  );
}
