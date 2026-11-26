"use client";

import { useRouter } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createAppointment,
  getAppointments,
  getAvailability,
  getClients,
  getMe,
  getServices,
  getUsers,
  updateAppointment,
  type Appointment,
  type Client,
  type Me,
  type Service,
  type UserSummary,
} from "@/lib/api";
import {
  formatDateLabel,
  formatTime,
  isoToTenantDate,
  isoToTenantTime,
  shiftDate,
  toTenantIso,
  todayInTenant,
} from "@/lib/agenda";

const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: "Agendado",
  PENDING_DEPOSIT: "Aguardando sinal",
  CONFIRMED: "Confirmado",
  CANCELLED: "Cancelado",
  EXPIRED: "Expirado",
  COMPLETED: "Concluído",
  NO_SHOW: "Faltou",
};

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

export default function AgendaPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [date, setDate] = useState(todayInTenant());
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [filterCollaborator, setFilterCollaborator] = useState("");
  const [formCollaborator, setFormCollaborator] = useState("");
  const [formClient, setFormClient] = useState("");
  const [formService, setFormService] = useState("");
  const [formTime, setFormTime] = useState("");
  const [slots, setSlots] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionId, setActionId] = useState<string | null>(null);
  const [reschedule, setReschedule] = useState<{
    id: string;
    date: string;
    time: string;
  } | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const refreshAgenda = useCallback(async () => {
    const data = await getAppointments(date, filterCollaborator || undefined);
    setAppointments(data);
  }, [date, filterCollaborator]);

  useEffect(() => {
    let active = true;

    getMe()
      .then(async (data) => {
        if (!active) return;
        setMe(data);
        const [svc, cli] = await Promise.all([getServices(), getClients()]);
        if (!active) return;
        setServices(svc.filter((item) => item.is_active));
        setClients(cli);
        if (data.role === "OWNER" || data.role === "ADMIN") {
          const usr = await getUsers();
          if (!active) return;
          setUsers(usr.filter((item) => item.is_active));
        }
        setFormCollaborator(data.id);
      })
      .catch(() => {
        if (active) router.replace("/login");
      });

    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    if (!me) return;
    let active = true;
    setLoading(true);
    refreshAgenda()
      .catch(() => {
        if (active) setError("Não foi possível carregar a agenda.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [me, refreshAgenda]);

  useEffect(() => {
    if (!formService || !formCollaborator) {
      setSlots([]);
      return;
    }
    let active = true;
    getAvailability(formService, date, formCollaborator)
      .then((data) => {
        if (active) setSlots(data.available_slots);
      })
      .catch(() => {
        if (active) setSlots([]);
      });
    return () => {
      active = false;
    };
  }, [formService, date, formCollaborator]);

  const collaboratorNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const user of users) map.set(user.id, user.full_name);
    if (me) map.set(me.id, me.full_name);
    return map;
  }, [users, me]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!formClient || !formService || !formTime) {
      setError("Selecione cliente, serviço e horário.");
      return;
    }
    setSaving(true);
    try {
      await createAppointment({
        client_id: formClient,
        service_id: formService,
        collaborator_id: formCollaborator || undefined,
        starts_at: toTenantIso(date, formTime),
      });
      setFormTime("");
      await refreshAgenda();
      const available = await getAvailability(formService, date, formCollaborator);
      setSlots(available.available_slots);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Horário indisponível — escolha outra brecha.");
        const available = await getAvailability(formService, date, formCollaborator);
        setSlots(available.available_slots);
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Você não pode agendar para outro profissional.");
      } else {
        setError("Não foi possível criar o agendamento.");
      }
    } finally {
      setSaving(false);
    }
  }

  async function refreshSlots() {
    if (!formService) return;
    const available = await getAvailability(
      formService,
      date,
      formCollaborator,
    );
    setSlots(available.available_slots);
  }

  async function handleStatus(
    appointment: Appointment,
    status: "CONFIRMED" | "COMPLETED" | "NO_SHOW" | "CANCELLED",
    label: string,
  ) {
    if (
      status === "CANCELLED" &&
      !window.confirm(`Cancelar o agendamento de ${appointment.client_name}?`)
    ) {
      return;
    }
    if (
      status === "NO_SHOW" &&
      !window.confirm(`Marcar ${appointment.client_name} como falta?`)
    ) {
      return;
    }
    setError(null);
    setActionId(appointment.id);
    try {
      await updateAppointment(appointment.id, { status });
      await refreshAgenda();
      if (formService) await refreshSlots();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : `Não foi possível ${label.toLowerCase()} o agendamento.`,
      );
    } finally {
      setActionId(null);
    }
  }

  function startReschedule(appointment: Appointment) {
    setReschedule({
      id: appointment.id,
      date: isoToTenantDate(appointment.starts_at),
      time: isoToTenantTime(appointment.starts_at),
    });
    setError(null);
  }

  async function handleReschedule(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!reschedule) return;
    setError(null);
    setActionId(reschedule.id);
    try {
      await updateAppointment(reschedule.id, {
        starts_at: toTenantIso(reschedule.date, reschedule.time),
      });
      setReschedule(null);
      await refreshAgenda();
      if (formService) await refreshSlots();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Horário indisponível — escolha outra brecha.");
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Não foi possível reagendar o atendimento.",
        );
      }
    } finally {
      setActionId(null);
    }
  }

  async function handleCancel(id: string) {
    const appointment = appointments.find((item) => item.id === id);
    if (!appointment) return;
    await handleStatus(appointment, "CANCELLED", "cancelar");
  }

  if (!me) {
    return (
      <main className="shell">
        <div className="card">
          <p className="subtitle">Carregando agenda…</p>
        </div>
      </main>
    );
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div className="greeting">
            <span className="badge">{ROLE_LABEL[me.role] ?? me.role}</span>
            <h1>Agenda</h1>
            <p>
              {formatDateLabel(date)} · {appointments.length} agendamento(s)
            </p>
          </div>
        </header>

        <section className="panel agenda-datebar">
          <button
            className="button button-ghost"
            type="button"
            onClick={() => setDate(shiftDate(date, -1))}
          >
            ← Anterior
          </button>
          <input
            aria-label="Data"
            type="date"
            value={date}
            onChange={(event) => setDate(event.target.value)}
          />
          <button
            className="button button-ghost"
            type="button"
            onClick={() => setDate(shiftDate(date, 1))}
          >
            Próximo →
          </button>
          <button
            className="button button-ghost"
            type="button"
            onClick={() => setDate(todayInTenant())}
          >
            Hoje
          </button>
          {isManager ? (
            <select
              aria-label="Filtrar profissional"
              className="select"
              value={filterCollaborator}
              onChange={(event) => setFilterCollaborator(event.target.value)}
            >
              <option value="">Todos os profissionais</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.full_name}
                </option>
              ))}
            </select>
          ) : null}
        </section>

        <div className="agenda-layout">
          <section className="agenda-list">
            {loading ? (
              <div className="panel">Carregando…</div>
            ) : appointments.length === 0 ? (
              <div className="panel agenda-empty">
                Nenhum agendamento neste dia.
              </div>
            ) : (
              appointments.map((appointment) => {
                const closed = [
                  "CANCELLED",
                  "COMPLETED",
                  "EXPIRED",
                  "NO_SHOW",
                ].includes(appointment.status);
                const busy = actionId === appointment.id;
                return (
                  <div key={appointment.id}>
                    <article className="appointment-card">
                      <div className="appointment-time">
                        {formatTime(appointment.starts_at)}
                      </div>
                      <div className="appointment-main">
                        <div className="appointment-title">
                          {appointment.client_name}
                          {appointment.subscription_id ? (
                            <span className="badge-subscriber">Assinante</span>
                          ) : null}
                        </div>
                        <div className="appointment-sub">
                          {appointment.service_name} ·{" "}
                          {collaboratorNames.get(
                            appointment.collaborator_id,
                          ) ?? "Profissional"}
                        </div>
                        <div className="appointment-sub">
                          {formatTime(appointment.starts_at)}–
                          {formatTime(appointment.ends_at)}
                          {appointment.deposit_amount
                            ? ` · sinal R$ ${appointment.deposit_amount}`
                            : ""}
                        </div>
                      </div>
                      <div className="appointment-side">
                        <span
                          className={`status status-${appointment.status.toLowerCase()}`}
                        >
                          {STATUS_LABEL[appointment.status] ??
                            appointment.status}
                        </span>
                        {appointment.status === "PENDING_DEPOSIT" ? (
                          <button
                            className="button button-ghost button-small"
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              handleStatus(
                                appointment,
                                "CONFIRMED",
                                "confirmar",
                              )
                            }
                          >
                            Confirmar
                          </button>
                        ) : null}
                        {appointment.status === "SCHEDULED" ||
                        appointment.status === "CONFIRMED" ? (
                          <>
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                handleStatus(
                                  appointment,
                                  "COMPLETED",
                                  "concluir",
                                )
                              }
                            >
                              Concluir
                            </button>
                            <button
                              className="button button-ghost button-small button-danger"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                handleStatus(
                                  appointment,
                                  "NO_SHOW",
                                  "marcar falta",
                                )
                              }
                            >
                              Faltou
                            </button>
                          </>
                        ) : null}
                        {!closed ? (
                          <>
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              disabled={busy}
                              onClick={() => startReschedule(appointment)}
                            >
                              Reagendar
                            </button>
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              disabled={busy}
                              onClick={() => handleCancel(appointment.id)}
                            >
                              Cancelar
                            </button>
                          </>
                        ) : null}
                      </div>
                    </article>

                    {reschedule?.id === appointment.id ? (
                      <form
                        className="panel agenda-reschedule"
                        onSubmit={handleReschedule}
                      >
                        <strong>Reagendar {appointment.client_name}</strong>
                        <div className="agenda-reschedule-fields">
                          <div className="field">
                            <label htmlFor={`reschedule-date-${appointment.id}`}>
                              Nova data
                            </label>
                            <input
                              id={`reschedule-date-${appointment.id}`}
                              type="date"
                              value={reschedule.date}
                              onChange={(event) =>
                                setReschedule({
                                  ...reschedule,
                                  date: event.target.value,
                                })
                              }
                              required
                            />
                          </div>
                          <div className="field">
                            <label htmlFor={`reschedule-time-${appointment.id}`}>
                              Novo horário
                            </label>
                            <input
                              id={`reschedule-time-${appointment.id}`}
                              type="time"
                              value={reschedule.time}
                              onChange={(event) =>
                                setReschedule({
                                  ...reschedule,
                                  time: event.target.value,
                                })
                              }
                              required
                            />
                          </div>
                        </div>
                        <div className="row-actions">
                          <button
                            className="button button-small"
                            type="submit"
                            disabled={busy}
                          >
                            {busy ? "Reagendando…" : "Confirmar novo horário"}
                          </button>
                          <button
                            className="button button-ghost button-small"
                            type="button"
                            disabled={busy}
                            onClick={() => setReschedule(null)}
                          >
                            Voltar
                          </button>
                        </div>
                      </form>
                    ) : null}
                  </div>
                );
              })
            )}
          </section>

          <section className="panel agenda-form">
            <h2>Novo agendamento</h2>
            <p className="subtitle">
              Conflitos são bloqueados pelo backend (lock + constraint).
            </p>

            <form onSubmit={handleCreate}>
              <div className="field">
                <label htmlFor="client">Cliente</label>
                <select
                  id="client"
                  value={formClient}
                  onChange={(event) => setFormClient(event.target.value)}
                  required
                >
                  <option value="">Selecione…</option>
                  {clients.map((client) => (
                    <option key={client.id} value={client.id}>
                      {client.full_name}
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="service">Serviço</label>
                <select
                  id="service"
                  value={formService}
                  onChange={(event) => setFormService(event.target.value)}
                  required
                >
                  <option value="">Selecione…</option>
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} ({service.duration_minutes} min)
                    </option>
                  ))}
                </select>
              </div>

              <div className="field">
                <label htmlFor="collaborator">Profissional</label>
                {isManager ? (
                  <select
                    id="collaborator"
                    value={formCollaborator}
                    onChange={(event) => setFormCollaborator(event.target.value)}
                    required
                  >
                    <option value="">Selecione…</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.full_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input id="collaborator" value={me.full_name} disabled />
                )}
              </div>

              <div className="field">
                <label htmlFor="date">Data</label>
                <input
                  id="date"
                  type="date"
                  value={date}
                  onChange={(event) => setDate(event.target.value)}
                />
              </div>

              <div className="field">
                <label>Horários livres</label>
                <div className="slot-grid">
                  {slots.length === 0 ? (
                    <span className="appointment-sub">
                      Sem horários livres para este serviço.
                    </span>
                  ) : (
                    slots.map((slot) => (
                      <button
                        key={slot}
                        className={`slot ${formTime === slot ? "active" : ""}`}
                        type="button"
                        onClick={() => setFormTime(slot)}
                      >
                        {slot}
                      </button>
                    ))
                  )}
                </div>
              </div>

              <div className="field">
                <label htmlFor="time">Horário</label>
                <input
                  id="time"
                  type="time"
                  value={formTime}
                  onChange={(event) => setFormTime(event.target.value)}
                  required
                />
              </div>

              <button className="button" type="submit" disabled={saving}>
                {saving ? "Agendando…" : "Agendar"}
              </button>

              {error ? <p className="error">{error}</p> : null}
            </form>
          </section>
        </div>
      </div>
    </AppShell>
  );
}
