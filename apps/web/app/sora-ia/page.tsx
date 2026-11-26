"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  closeAiConversation,
  getAiConversation,
  getAiConversations,
  getAiSummary,
  getBirthdayCredits,
  getMe,
  runBirthdayCredits,
  sendAiConversationMessage,
  takeoverAiConversation,
  type AiConversation,
  type AiConversationDetail,
  type AiSummary,
  type BirthdayCredit,
  type Me,
} from "@/lib/api";
import { formatDateLabel, formatDateOnly, formatTime } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

const STATUS_LABEL: Record<string, string> = {
  OPEN: "SORA IA",
  HUMAN: "Atendimento humano",
  CLOSED: "Encerrada",
};

export default function SoraAiPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [summary, setSummary] = useState<AiSummary | null>(null);
  const [conversations, setConversations] = useState<AiConversation[]>([]);
  const [credits, setCredits] = useState<BirthdayCredit[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<AiConversationDetail | null>(null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [creditBusy, setCreditBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadOverview = useCallback(async () => {
    const year = String(new Date().getFullYear());
    const [summaryData, conversationData, creditData] = await Promise.all([
      getAiSummary(),
      getAiConversations(),
      getBirthdayCredits(year),
    ]);
    setSummary(summaryData);
    setConversations(conversationData);
    setCredits(creditData);
    setSelectedId((current) => {
      if (current && conversationData.some((item) => item.id === current)) {
        return current;
      }
      return conversationData[0]?.id ?? null;
    });
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), loadOverview()])
      .then(([user]) => {
        if (active) setMe(user);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Falha ao carregar a central.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [loadOverview]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    let active = true;
    getAiConversation(selectedId)
      .then((data) => {
        if (active) setDetail(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao abrir conversa.",
          );
        }
      });
    return () => {
      active = false;
    };
  }, [selectedId]);

  async function reloadConversation(id: string) {
    const [data] = await Promise.all([getAiConversation(id), loadOverview()]);
    setDetail(data);
  }

  async function handleTakeover() {
    if (!detail) return;
    setSaving(true);
    setError(null);
    try {
      await takeoverAiConversation(detail.id);
      await reloadConversation(detail.id);
      setNotice("Atendimento assumido pela equipe.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao assumir conversa.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleSend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!detail || !reply.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await sendAiConversationMessage(detail.id, reply.trim());
      setReply("");
      await reloadConversation(detail.id);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao enviar mensagem.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleClose() {
    if (!detail) return;
    setSaving(true);
    setError(null);
    try {
      await closeAiConversation(detail.id);
      await reloadConversation(detail.id);
      setNotice("Conversa encerrada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao encerrar conversa.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleRunCredits() {
    setCreditBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await runBirthdayCredits();
      await loadOverview();
      setNotice(
        result.created > 0
          ? `${result.created} crédito(s) gerado(s) · R$ ${result.total_amount}`
          : "Nenhum aniversariante novo para creditar.",
      );
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao gerar créditos de aniversário.",
      );
    } finally {
      setCreditBusy(false);
    }
  }

  if (!isManager && me) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">Apenas dono ou administrador acessa a SORA IA.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>SORA IA &amp; Conversas</h1>
            <p>
              Resumo do atendente virtual, histórico do WhatsApp e escalonamento
              para humano.
            </p>
          </div>
          <div className="page-actions">
            <Link className="button button-ghost" href="/configuracoes">
              Configurar agente
            </Link>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        <section className="stats">
          <article className="stat">
            <div className="stat-label">Agente</div>
            <div className="stat-value">{summary?.agent_name ?? "Sora"}</div>
            <div className="stat-note">Atendimento automático 24/7</div>
          </article>
          <article className="stat">
            <div className="stat-label">Conversas abertas</div>
            <div className="stat-value">
              {summary?.open_conversations ?? "—"}
            </div>
            <div className="stat-note">Conduzidas pela SORA IA</div>
          </article>
          <article className="stat">
            <div className="stat-label">Precisam de humano</div>
            <div className="stat-value">
              {summary?.human_conversations ?? "—"}
            </div>
            <div className="stat-note">Aguardando a equipe</div>
          </article>
          <article className="stat">
            <div className="stat-label">Mensagens hoje</div>
            <div className="stat-value">{summary?.messages_today ?? "—"}</div>
            <div className="stat-note">
              {summary?.appointments_today ?? 0} agendamento(s) hoje
            </div>
          </article>
        </section>

        <div className="ai-layout">
          <section className="panel ai-conversations">
            <div className="panel-title">
              <h2>Conversas</h2>
              <span className="muted-small">{conversations.length}</span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : conversations.length === 0 ? (
              <p className="table-empty">
                Nenhuma conversa ainda. O canal é mock: use o webhook interno
                para simular uma mensagem.
              </p>
            ) : (
              conversations.map((conversation) => (
                <button
                  key={conversation.id}
                  type="button"
                  className={`ai-conversation ${
                    selectedId === conversation.id ? "active" : ""
                  }`}
                  onClick={() => setSelectedId(conversation.id)}
                >
                  <div className="ai-conversation-head">
                    <strong>
                      {conversation.client_name ?? conversation.phone}
                    </strong>
                    <span
                      className={`pill ${
                        conversation.status === "HUMAN"
                          ? "pill-blocked"
                          : conversation.status === "CLOSED"
                            ? ""
                            : "pill-active"
                      }`}
                    >
                      {STATUS_LABEL[conversation.status] ?? conversation.status}
                    </span>
                  </div>
                  <span className="ai-preview">
                    {conversation.last_message ?? "Sem mensagens"}
                  </span>
                  <span className="ai-time">
                    {formatTime(conversation.last_message_at)}
                  </span>
                </button>
              ))
            )}

            <div className="ai-birthdays">
              <div className="panel-title">
                <h2>Aniversários (7 dias)</h2>
              </div>
              {summary && summary.birthdays.length > 0 ? (
                summary.birthdays.map((birthday) => (
                  <div className="ai-birthday" key={birthday.client_id}>
                    <div>
                      <strong>{birthday.full_name}</strong>
                      <span className="muted-small">
                        {formatDateOnly(birthday.birth_date)}
                      </span>
                    </div>
                    <span className="pill pill-active">
                      {birthday.days_until === 0
                        ? "hoje"
                        : `em ${birthday.days_until}d`}
                    </span>
                  </div>
                ))
              ) : (
                <p className="muted-small">Nenhum aniversariante próximo.</p>
              )}
            </div>

            <div className="ai-birthdays">
              <div className="panel-title">
                <h2>Créditos gerados</h2>
                <button
                  className="button button-ghost button-small"
                  type="button"
                  onClick={handleRunCredits}
                  disabled={creditBusy}
                >
                  {creditBusy ? "Gerando…" : "Gerar créditos"}
                </button>
              </div>
              {credits.length > 0 ? (
                credits.map((credit) => (
                  <div className="ai-birthday" key={credit.id}>
                    <div>
                      <strong>{credit.client_name}</strong>
                      <span className="muted-small">
                        válido até {formatDateOnly(credit.expires_at)} · usado{" "}
                        {credit.used_amount}
                      </span>
                    </div>
                    <span className="pill pill-active">
                      {formatPrice(credit.amount)}
                    </span>
                  </div>
                ))
              ) : (
                <p className="muted-small">
                  Nenhum crédito gerado neste ano. Configure o valor em
                  Configurações.
                </p>
              )}
            </div>
          </section>

          <section className="panel ai-chat">
            {!detail ? (
              <p className="table-empty">
                Selecione uma conversa para ver o histórico.
              </p>
            ) : (
              <>
                <div className="ai-chat-head">
                  <div>
                    <h2>{detail.client_name ?? detail.phone}</h2>
                    <p className="muted-small">
                      {detail.phone} ·{" "}
                      {summary?.date ? formatDateLabel(summary.date) : ""}
                    </p>
                  </div>
                  <div className="ai-chat-actions">
                    {detail.status === "OPEN" ? (
                      <button
                        className="button button-ghost button-small"
                        type="button"
                        onClick={handleTakeover}
                        disabled={saving}
                      >
                        Assumir conversa
                      </button>
                    ) : null}
                    {detail.status !== "CLOSED" ? (
                      <button
                        className="button button-ghost button-small"
                        type="button"
                        onClick={handleClose}
                        disabled={saving}
                      >
                        Encerrar
                      </button>
                    ) : null}
                  </div>
                </div>

                <div className="ai-messages">
                  {detail.messages.map((message) => (
                    <div
                      key={message.id}
                      className={`ai-bubble ${
                        message.direction === "OUTBOUND"
                          ? "ai-bubble-out"
                          : "ai-bubble-in"
                      }`}
                    >
                      <p>{message.content}</p>
                      <span>
                        {formatTime(message.created_at)}
                        {message.intent ? ` · ${message.intent}` : ""}
                      </span>
                    </div>
                  ))}
                </div>

                {detail.status !== "CLOSED" ? (
                  <form className="ai-reply" onSubmit={handleSend}>
                    <input
                      aria-label="Resposta"
                      value={reply}
                      onChange={(event) => setReply(event.target.value)}
                      placeholder="Escreva uma resposta como recepção…"
                      maxLength={2000}
                    />
                    <button
                      className="button"
                      type="submit"
                      disabled={saving || !reply.trim()}
                    >
                      {saving ? "Enviando…" : "Enviar"}
                    </button>
                  </form>
                ) : (
                  <p className="muted-small">
                    Conversa encerrada. O histórico permanece disponível.
                  </p>
                )}
              </>
            )}
          </section>
        </div>

        <p className="public-note ai-note">
          Canal mock: o envio real pelo WhatsApp e o LLM (PydanticAI) entram na
          integração final. As respostas atuais são determinísticas e passam
          pelos guardrails Zero-Leak.
        </p>
      </div>
    </AppShell>
  );
}
