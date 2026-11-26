"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  addLgpdConsent,
  createMedicalRecord,
  deleteAttachment,
  getAttachmentUrl,
  getClient,
  getClientCredits,
  getClientCreditUsages,
  getMedicalRecords,
  getMe,
  presignAttachment,
  applyClientCredit,
  type Client,
  type ClientCredit,
  type ClientCreditUsage,
  type MedicalRecord,
  type Me,
} from "@/lib/api";
import { formatDateOnly, formatIsoDate } from "@/lib/agenda";
import { supportsMedicalRecords } from "@/lib/profiles";
import { formatPrice } from "@/lib/public";

function fileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function MedicalRecordPage() {
  const params = useParams<{ id: string }>();
  const clientId = Array.isArray(params.id) ? params.id[0] : params.id;
  const [client, setClient] = useState<Client | null>(null);
  const [records, setRecords] = useState<MedicalRecord[]>([]);
  const [role, setRole] = useState<Me["role"] | null>(null);
  const [businessProfile, setBusinessProfile] =
    useState<Me["business_profile"]>("GENERAL");
  const [credits, setCredits] = useState<ClientCredit[]>([]);
  const [creditUsages, setCreditUsages] = useState<ClientCreditUsage[]>([]);
  const [selectedCreditId, setSelectedCreditId] = useState("");
  const [creditAmount, setCreditAmount] = useState("0.00");
  const [creditNote, setCreditNote] = useState("");
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [attachmentBusy, setAttachmentBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadRecords = useCallback(async () => {
    if (!clientId) return;
    setRecords(await getMedicalRecords(clientId));
  }, [clientId]);

  useEffect(() => {
    if (!clientId) return;
    let active = true;
    Promise.all([getClient(clientId), getMedicalRecords(clientId), getMe()])
      .then(([clientData, recordsData, me]) => {
        if (!active) return;
        setClient(clientData);
        setRecords(recordsData);
        setRole(me.role);
        setBusinessProfile(me.business_profile);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Falha ao carregar prontuário.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [clientId]);

  useEffect(() => {
    if (!clientId || (role !== "OWNER" && role !== "ADMIN")) return;
    let active = true;
    Promise.all([
      getClientCredits(clientId),
      getClientCreditUsages(clientId),
    ])
      .then(([creditData, usageData]) => {
        if (!active) return;
        setCredits(creditData);
        setCreditUsages(usageData);
        const available = creditData.find((item) => item.is_available);
        if (available) {
          setSelectedCreditId(available.id);
          setCreditAmount(available.remaining_amount);
        }
      })
      .catch(() => {
        // Créditos são opcionais no prontuário.
      });
    return () => {
      active = false;
    };
  }, [clientId, role]);

  async function handleCreateRecord(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clientId) return;
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await createMedicalRecord(clientId, {
        title: title.trim(),
        notes: notes.trim(),
      });
      setTitle("");
      setNotes("");
      await loadRecords();
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
    if (!clientId) return;
    setError(null);
    setNotice(null);
    try {
      await addLgpdConsent(clientId, {
        terms_version: "v1",
        purposes: ["health_data", "appointment_management"],
      });
      setNotice("Consentimento LGPD registrado.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao registrar consentimento.",
      );
    }
  }

  async function handleAttachment(record: MedicalRecord, file: File) {
    if (!clientId) return;
    setAttachmentBusy(record.id);
    setError(null);
    setNotice(null);
    try {
      const presign = await presignAttachment(clientId, record.id, {
        filename: file.name,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size,
      });
      const upload = await fetch(presign.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });
      if (!upload.ok) {
        throw new Error("Falha no upload do arquivo.");
      }
      await loadRecords();
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
    if (!clientId) return;
    setError(null);
    try {
      const data = await getAttachmentUrl(clientId, record.id, attachmentId);
      window.open(data.url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao abrir anexo.",
      );
    }
  }

  async function downloadAttachment(
    record: MedicalRecord,
    attachmentId: string,
    filename: string,
  ) {
    if (!clientId) return;
    setError(null);
    setAttachmentBusy(record.id);
    try {
      const data = await getAttachmentUrl(clientId, record.id, attachmentId);
      const response = await fetch(data.url, { cache: "no-store" });
      if (!response.ok) throw new Error("Falha ao baixar anexo.");
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (err) {
      try {
        const data = await getAttachmentUrl(clientId, record.id, attachmentId);
        window.open(data.url, "_blank", "noopener,noreferrer");
      } catch {
        setError(
          err instanceof ApiError ? err.message : "Falha ao baixar anexo.",
        );
      }
    } finally {
      setAttachmentBusy(null);
    }
  }

  async function handleDeleteAttachment(
    record: MedicalRecord,
    attachmentId: string,
    filename: string,
  ) {
    if (!clientId) return;
    if (!window.confirm(`Excluir o anexo "${filename}"?`)) return;
    setError(null);
    setNotice(null);
    setAttachmentBusy(record.id);
    try {
      await deleteAttachment(clientId, record.id, attachmentId);
      await loadRecords();
      setNotice("Anexo excluído.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir anexo.",
      );
    } finally {
      setAttachmentBusy(null);
    }
  }

  async function handleUseCredit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!clientId || !selectedCreditId) return;
    setError(null);
    setNotice(null);
    try {
      await applyClientCredit(clientId, selectedCreditId, {
        amount: creditAmount,
        note: creditNote.trim() || null,
      });
      const [creditData, usageData] = await Promise.all([
        getClientCredits(clientId),
        getClientCreditUsages(clientId),
      ]);
      setCredits(creditData);
      setCreditUsages(usageData);
      setCreditNote("");
      const available = creditData.find((item) => item.is_available);
      if (available) {
        setSelectedCreditId(available.id);
        setCreditAmount(available.remaining_amount);
      } else {
        setSelectedCreditId("");
        setCreditAmount("0.00");
      }
      setNotice("Crédito aplicado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao aplicar crédito.",
      );
    }
  }

  const isManager = role === "OWNER" || role === "ADMIN";
  const medicalEnabled = supportsMedicalRecords(businessProfile);

  if (loading) {
    return (
      <AppShell>
        <div className="page">
          <p className="table-empty">Carregando prontuário…</p>
        </div>
      </AppShell>
    );
  }

  if (!client) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">{error ?? "Cliente não encontrado."}</p>
          <Link className="button button-ghost" href="/clientes">
            Voltar para clientes
          </Link>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <div className="muted-small">
              <Link href="/clientes">Clientes</Link> / prontuário
            </div>
            <h1>{client.full_name}</h1>
            <p>
              {client.phone}
              {client.email ? ` · ${client.email}` : ""} · Score {client.score}
              {client.is_blocked ? " · Bloqueado" : ""}
            </p>
          </div>
          <div className="page-actions">
            <button
              className="button button-ghost button-small"
              type="button"
              onClick={handleConsent}
            >
              Registrar consentimento LGPD
            </button>
            <Link className="button button-ghost button-small" href="/clientes">
              Voltar
            </Link>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {medicalEnabled ? (
          <div className="admin-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Evolução clínica</h2>
                <span className="muted-small">
                  {records.length} registro(s)
                </span>
              </div>
            {records.length === 0 ? (
              <p className="table-empty">Nenhuma evolução registrada.</p>
            ) : (
              records.map((record) => (
                <article className="medical-record" key={record.id}>
                  <div className="panel-title">
                    <div>
                      <strong>{record.title}</strong>
                      <div className="muted-small">
                        {formatIsoDate(record.created_at)}
                      </div>
                    </div>
                  </div>
                  <p className="medical-notes">{record.notes}</p>

                  {record.attachments.length > 0 ? (
                    <ul className="attachment-list">
                      {record.attachments.map((attachment) => (
                        <li key={attachment.id}>
                          <span>
                            {attachment.filename}
                            <small> · {fileSize(attachment.size_bytes)}</small>
                          </span>
                          <div className="row-actions">
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              onClick={() =>
                                openAttachment(record, attachment.id)
                              }
                            >
                              Abrir
                            </button>
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              disabled={attachmentBusy === record.id}
                              onClick={() =>
                                downloadAttachment(
                                  record,
                                  attachment.id,
                                  attachment.filename,
                                )
                              }
                            >
                              Baixar
                            </button>
                            {isManager ? (
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                disabled={attachmentBusy === record.id}
                                onClick={() =>
                                  handleDeleteAttachment(
                                    record,
                                    attachment.id,
                                    attachment.filename,
                                  )
                                }
                              >
                                Excluir
                              </button>
                            ) : null}
                          </div>
                        </li>
                      ))}
                    </ul>
                  ) : null}

                  <label className="attachment-upload">
                    {attachmentBusy === record.id
                      ? "Enviando…"
                      : "Anexar foto/documento"}
                    <input
                      type="file"
                      accept="image/jpeg,image/png,application/pdf"
                      disabled={attachmentBusy === record.id}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void handleAttachment(record, file);
                        event.target.value = "";
                      }}
                    />
                  </label>
                </article>
              ))
            )}
          </section>

          <section className="panel">
            <div className="panel-title">
              <h2>Nova evolução</h2>
            </div>
            <form onSubmit={handleCreateRecord}>
              <div className="field">
                <label htmlFor="record-title">Título</label>
                <input
                  id="record-title"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="Ex.: avaliação pós-atendimento"
                  required
                  maxLength={255}
                />
              </div>
              <div className="field">
                <label htmlFor="record-notes">Notas clínicas</label>
                <textarea
                  id="record-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  required
                  rows={6}
                  maxLength={10000}
                />
              </div>
              <button className="button" type="submit" disabled={saving}>
                {saving ? "Salvando…" : "Registrar evolução"}
              </button>
            </form>
            <p className="muted-small medical-note-help">
              As notas são cifradas no banco. Anexos usam bucket privado e URLs
              temporárias de 60 segundos.
            </p>
          </section>
          </div>
        ) : (
          <section className="panel">
            <div className="panel-title">
              <h2>Prontuário não habilitado</h2>
            </div>
            <p className="subtitle">
              O perfil deste negócio não utiliza prontuário clínico. Agenda,
              clientes, pacotes, assinaturas, estoque, financeiro e SORA IA
              continuam disponíveis.
            </p>
          </section>
        )}

        {isManager ? (
          <section className="panel section-gap">
            <div className="panel-title">
              <h2>Créditos do cliente</h2>
              <span className="muted-small">
                {credits.filter((item) => item.is_available).length} disponível(is)
              </span>
            </div>
            {credits.length === 0 ? (
              <p className="table-empty">
                Nenhum crédito gerado para este cliente.
              </p>
            ) : (
              <div className="admin-grid">
                <div>
                  <div className="table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Motivo</th>
                          <th>Valor</th>
                          <th>Usado</th>
                          <th>Saldo</th>
                          <th>Validade</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {credits.map((credit) => (
                          <tr key={credit.id}>
                            <td>
                              <strong>{credit.reason}</strong>
                              <div className="muted-small">
                                {credit.reference}
                              </div>
                            </td>
                            <td className="price-cell">
                              {formatPrice(credit.amount)}
                            </td>
                            <td className="price-cell">
                              {formatPrice(credit.used_amount)}
                            </td>
                            <td className="price-cell">
                              {formatPrice(credit.remaining_amount)}
                            </td>
                            <td>{formatDateOnly(credit.expires_at)}</td>
                            <td>
                              <span
                                className={`pill ${
                                  credit.is_available
                                    ? "pill-active"
                                    : "pill-blocked"
                                }`}
                              >
                                {credit.is_available
                                  ? "Disponível"
                                  : "Indisponível"}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="panel-title section-gap">
                    <h3>Histórico de uso</h3>
                  </div>
                  {creditUsages.length === 0 ? (
                    <p className="table-empty">Nenhuma utilização.</p>
                  ) : (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Data</th>
                            <th>Valor</th>
                            <th>Observação</th>
                          </tr>
                        </thead>
                        <tbody>
                          {creditUsages.map((usage) => (
                            <tr key={usage.id}>
                              <td>{formatIsoDate(usage.created_at)}</td>
                              <td className="price-cell">
                                {formatPrice(usage.amount)}
                              </td>
                              <td>{usage.note ?? "—"}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                <form onSubmit={handleUseCredit}>
                  <div className="field">
                    <label htmlFor="credit-select">Crédito</label>
                    <select
                      id="credit-select"
                      value={selectedCreditId}
                      onChange={(event) => {
                        setSelectedCreditId(event.target.value);
                        const credit = credits.find(
                          (item) => item.id === event.target.value,
                        );
                        setCreditAmount(credit?.remaining_amount ?? "0.00");
                      }}
                      required
                    >
                      <option value="">Selecione…</option>
                      {credits
                        .filter((item) => item.is_available)
                        .map((credit) => (
                          <option key={credit.id} value={credit.id}>
                            {credit.reason} · saldo{" "}
                            {formatPrice(credit.remaining_amount)}
                          </option>
                        ))}
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="credit-amount">Valor a aplicar (R$)</label>
                    <input
                      id="credit-amount"
                      inputMode="decimal"
                      value={creditAmount}
                      onChange={(event) => setCreditAmount(event.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="credit-note">Observação</label>
                    <input
                      id="credit-note"
                      value={creditNote}
                      onChange={(event) => setCreditNote(event.target.value)}
                      maxLength={1000}
                    />
                  </div>
                  <button
                    className="button"
                    type="submit"
                    disabled={!selectedCreditId}
                  >
                    Aplicar crédito
                  </button>
                  <p className="muted-small">
                    O uso reduz o saldo do crédito e fica registrado no
                    histórico e na auditoria.
                  </p>
                </form>
              </div>
            )}
          </section>
        ) : null}
      </div>
    </AppShell>
  );
}
