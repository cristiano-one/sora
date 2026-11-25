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
  cancelAppointment,
  createAppointment,
  getAppointments,
  getAvailability,
  getClients,
  getMe,
  getServices,
  getUsers,
  type Appointment,
  type Client,
  type Me,
  type Service,
  type UserSummary,
} from "@/lib/api";
import {
  formatDateLabel,
  formatTime,
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

  async function handleCancel(id: string) {
    if (!window.confirm("Cancelar este agendamento?")) return;
    setError(null);
    try {
      await cancelAppointment(id);
      await refreshAgenda();
      if (formService) {
        const available = await getAvailability(
          formService,
          date,
          formCollaborator,
        );
        setSlots(available.available_slots);
      }
    } catch {
      setError("Não foi possível cancelar o agendamento.");
    }
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
              appointments.map((appointment) => (
                <article key={appointment.id} className="appointment-card">
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
                      {collaboratorNames.get(appointment.collaborator_id) ??
                        "Profissional"}
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
                      {STATUS_LABEL[appointment.status] ?? appointment.status}
                    </span>
                    {appointment.status !== "CANCELLED" &&
                    appointment.status !== "COMPLETED" &&
                    appointment.status !== "EXPIRED" ? (
                      <button
                        className="button button-ghost button-small"
                        type="button"
                        onClick={() => handleCancel(appointment.id)}
                      >
                        Cancelar
                      </button>
                    ) : null}
                  </div>
                </article>
              ))
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
