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
  addSaleItem,
  ApiError,
  applySaleCredit,
  cancelSale,
  closeSale,
  createAppointment,
  createSaleFromAppointment,
  getAppointmentsRange,
  getAvailability,
  getCheckinLink,
  getClientCredits,
  getClients,
  getMe,
  getSaleAccounts,
  getServices,
  getUsers,
  removeSaleItem,
  updateAppointment,
  updateSale,
  type Appointment,
  type Client,
  type ClientCredit,
  type Me,
  type Sale,
  type SaleAccount,
  type SalePaymentMethod,
  type Service,
  type UserSummary,
} from "@/lib/api";
import {
  formatDateLabel,
  formatTime,
  isoToTenantDate,
  isoToTenantTime,
  toTenantIso,
  todayInTenant,
} from "@/lib/agenda";
import {
  buildMonthCells,
  dayNumber,
  groupByDate,
  monthBounds,
  monthLabel,
  monthStart,
  shiftMonth,
} from "@/lib/agenda-calendar";
import { formatPrice } from "@/lib/public";

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

const WEEKDAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];

function statusClass(status: string): string {
  return `agenda-event agenda-event-${status.toLowerCase()}`;
}

function initials(name: string): string {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

export default function AgendaPage() {
  const router = useRouter();
  const today = todayInTenant();
  const [me, setMe] = useState<Me | null>(null);
  const [month, setMonth] = useState(monthStart(today));
  const [selectedDate, setSelectedDate] = useState(today);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [filterCollaborator, setFilterCollaborator] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);
  const [checkinBusy, setCheckinBusy] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [formClient, setFormClient] = useState("");
  const [formService, setFormService] = useState("");
  const [formCollaborator, setFormCollaborator] = useState("");
  const [formTime, setFormTime] = useState("");
  const [slots, setSlots] = useState<string[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const [reschedule, setReschedule] = useState<{
    id: string;
    date: string;
    time: string;
  } | null>(null);

  const [sale, setSale] = useState<Sale | null>(null);
  const [saleBusy, setSaleBusy] = useState(false);
  const [saleAccounts, setSaleAccounts] = useState<SaleAccount[]>([]);
  const [saleCredits, setSaleCredits] = useState<ClientCredit[]>([]);
  const [saleAccountId, setSaleAccountId] = useState("");
  const [salePaymentMethod, setSalePaymentMethod] =
    useState<SalePaymentMethod>("PIX");
  const [saleDiscount, setSaleDiscount] = useState("0.00");
  const [saleServiceId, setSaleServiceId] = useState("");
  const [saleItemDescription, setSaleItemDescription] = useState("");
  const [saleItemPrice, setSaleItemPrice] = useState("0.00");
  const [saleCreditId, setSaleCreditId] = useState("");
  const [saleCreditAmount, setSaleCreditAmount] = useState("0.00");
  const [saleNotes, setSaleNotes] = useState("");

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const cells = useMemo(() => buildMonthCells(month), [month]);
  const byDate = useMemo(() => groupByDate(appointments), [appointments]);
  const selectedAppointments = byDate[selectedDate] ?? [];
  const collaboratorNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const user of users) map.set(user.id, user.full_name);
    if (me) map.set(me.id, me.full_name);
    return map;
  }, [users, me]);

  const refreshAgenda = useCallback(async () => {
    const range = monthBounds(month);
    const data = await getAppointmentsRange(
      range.from,
      range.to,
      filterCollaborator || undefined,
    );
    setAppointments(data);
  }, [filterCollaborator, month]);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getServices(), getClients()])
      .then(async ([user, serviceData, clientData]) => {
        if (!active) return;
        setMe(user);
        setServices(serviceData.filter((item) => item.is_active));
        setClients(clientData);
        setFormCollaborator(user.id);
        setFormService(
          serviceData.find((item) => item.is_active)?.id ?? "",
        );
        if (user.role === "OWNER" || user.role === "ADMIN") {
          const userData = await getUsers();
          if (!active) return;
          setUsers(userData.filter((item) => item.is_active));
        }
      })
      .catch((err) => {
        if (active) {
          if (err instanceof ApiError && err.status === 401) {
            router.replace("/login");
          } else {
            setError("Não foi possível carregar a agenda.");
          }
        }
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
    if (!showForm || !formService || !formCollaborator) {
      setSlots([]);
      return;
    }
    let active = true;
    setSlotsLoading(true);
    getAvailability(formService, selectedDate, formCollaborator)
      .then((data) => {
        if (active) setSlots(data.available_slots);
      })
      .catch(() => {
        if (active) setSlots([]);
      })
      .finally(() => {
        if (active) setSlotsLoading(false);
      });
    return () => {
      active = false;
    };
  }, [formCollaborator, formService, selectedDate, showForm]);

  function goToMonth(nextMonth: string) {
    setMonth(nextMonth);
    setSelectedDate(nextMonth);
  }

  function selectDate(date: string) {
    setSelectedDate(date);
    if (!date.startsWith(month.slice(0, 7))) {
      setMonth(monthStart(date));
    }
  }

  function openForm() {
    setShowForm(true);
    setFormTime("");
    setError(null);
    setNotice(null);
  }

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!formClient || !formService || !formTime) {
      setError("Selecione cliente, serviço e horário.");
      return;
    }
    setSaving(true);
    try {
      const created = await createAppointment({
        client_id: formClient,
        service_id: formService,
        collaborator_id: formCollaborator || undefined,
        starts_at: toTenantIso(selectedDate, formTime),
      });
      setShowForm(false);
      setFormTime("");
      setFormClient("");
      setSelectedDate(isoToTenantDate(created.starts_at));
      await refreshAgenda();
      setNotice("Agendamento criado.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Horário indisponível — escolha outra brecha.");
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Você não pode agendar para outro profissional.");
      } else {
        setError(
          err instanceof ApiError
            ? err.message
            : "Não foi possível criar o agendamento.",
        );
      }
    } finally {
      setSaving(false);
    }
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
      setNotice(`Agendamento atualizado: ${label}.`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível atualizar o agendamento.",
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

  async function handleCheckinLink(appointment: Appointment) {
    setCheckinBusy(appointment.id);
    setError(null);
    setNotice(null);
    try {
      const link = await getCheckinLink(appointment.id);
      await navigator.clipboard.writeText(link.url);
      setNotice("Link de check-in copiado. Envie ao cliente pelo WhatsApp.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao gerar o link de check-in.",
      );
    } finally {
      setCheckinBusy(null);
    }
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
      setSelectedDate(reschedule.date);
      if (!reschedule.date.startsWith(month.slice(0, 7))) {
        setMonth(monthStart(reschedule.date));
      }
      setReschedule(null);
      await refreshAgenda();
      setNotice("Atendimento reagendado.");
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

  async function openComanda(appointment: Appointment) {
    setError(null);
    setNotice(null);
    setActionId(appointment.id);
    try {
      const [data, accounts, credits] = await Promise.all([
        createSaleFromAppointment(appointment.id),
        getSaleAccounts(),
        getClientCredits(appointment.client_id),
      ]);
      setSale(data);
      setSaleAccounts(accounts);
      setSaleCredits(credits.filter((item) => item.is_available));
      setSaleAccountId(accounts[0]?.id ?? "");
      setSalePaymentMethod("PIX");
      setSaleDiscount(data.discount);
      setSaleNotes(data.notes ?? "");
      setSaleServiceId(services[0]?.id ?? "");
      setSaleItemDescription("");
      setSaleItemPrice("0.00");
      const available = credits.find((item) => item.is_available);
      setSaleCreditId(available?.id ?? "");
      setSaleCreditAmount(available?.remaining_amount ?? "0.00");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Não foi possível abrir a comanda.",
      );
    } finally {
      setActionId(null);
    }
  }

  async function handleAddSaleService() {
    if (!sale || !saleServiceId) return;
    setSaleBusy(true);
    setError(null);
    try {
      setSale(
        await addSaleItem(sale.id, {
          service_id: saleServiceId,
          category: "SERVICE",
          quantity: 1,
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao adicionar serviço.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleAddManualItem() {
    if (!sale || !saleItemDescription.trim()) return;
    setSaleBusy(true);
    setError(null);
    try {
      const updated = await addSaleItem(sale.id, {
        category: "PRODUCT",
        description: saleItemDescription.trim(),
        quantity: 1,
        unit_price: saleItemPrice,
        cost: "0.00",
      });
      setSale(updated);
      setSaleItemDescription("");
      setSaleItemPrice("0.00");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao adicionar item.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleRemoveSaleItem(itemId: string) {
    if (!sale) return;
    setSaleBusy(true);
    setError(null);
    try {
      setSale(await removeSaleItem(sale.id, itemId));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao remover item.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleSaleDiscount() {
    if (!sale) return;
    setSaleBusy(true);
    setError(null);
    try {
      setSale(
        await updateSale(sale.id, {
          discount: saleDiscount,
          notes: saleNotes.trim() || null,
        }),
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao aplicar desconto.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleSaleCredit() {
    if (!sale || !saleCreditId) return;
    setSaleBusy(true);
    setError(null);
    try {
      const updated = await applySaleCredit(sale.id, {
        credit_id: saleCreditId,
        amount: saleCreditAmount,
      });
      setSale(updated);
      const credits = await getClientCredits(sale.client_id);
      setSaleCredits(credits.filter((item) => item.is_available));
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao aplicar crédito.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleCloseSale() {
    if (!sale) return;
    if (!saleAccountId) {
      setError("Selecione a conta que receberá o pagamento.");
      return;
    }
    setSaleBusy(true);
    setError(null);
    try {
      const closed = await closeSale(sale.id, {
        payment_method: salePaymentMethod,
        account_id: saleAccountId,
        notes: saleNotes.trim() || null,
      });
      setSale(null);
      await refreshAgenda();
      setNotice(`Comanda fechada: ${formatPrice(closed.total)}.`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao fechar comanda.",
      );
    } finally {
      setSaleBusy(false);
    }
  }

  async function handleCancelSale() {
    if (!sale) return;
    if (!window.confirm("Cancelar esta comanda e devolver créditos?")) return;
    setSaleBusy(true);
    setError(null);
    try {
      await cancelSale(sale.id);
      setSale(null);
      await refreshAgenda();
      setNotice("Comanda cancelada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao cancelar comanda.",
      );
    } finally {
      setSaleBusy(false);
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
      <div className="page agenda-page">
        <header className="page-header agenda-header">
          <div>
            <span className="badge">{ROLE_LABEL[me.role] ?? me.role}</span>
            <h1>Agenda</h1>
            <p>
              {formatDateLabel(selectedDate)} ·{" "}
              {selectedAppointments.length} atendimento(s)
            </p>
          </div>
          <div className="page-actions">
            <button
              className="button button-ghost button-small"
              type="button"
              onClick={() => {
                goToMonth(monthStart(today));
                setSelectedDate(today);
              }}
            >
              Hoje
            </button>
            <button className="button" type="button" onClick={openForm}>
              + Novo agendamento
            </button>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        <div className="agenda-workspace">
          <aside className="agenda-side">
            <div className="agenda-side-head">
              <div>
                <span className="agenda-eyebrow">Você vai atender</span>
                <h2>{formatDateLabel(selectedDate)}</h2>
              </div>
              <span className="agenda-count">
                {selectedAppointments.length}
              </span>
            </div>

            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : selectedAppointments.length === 0 ? (
              <div className="agenda-empty-card">
                <span>☾</span>
                <p>Nenhum atendimento neste dia.</p>
                <button
                  className="button button-ghost button-small"
                  type="button"
                  onClick={openForm}
                >
                  Agendar horário
                </button>
              </div>
            ) : (
              <div className="agenda-appointments">
                {selectedAppointments.map((appointment) => {
                  const closed = [
                    "CANCELLED",
                    "COMPLETED",
                    "EXPIRED",
                    "NO_SHOW",
                  ].includes(appointment.status);
                  const busy = actionId === appointment.id;
                  return (
                    <article
                      className="agenda-person-card"
                      key={appointment.id}
                    >
                      <div className="agenda-person-top">
                        <div className="agenda-avatar">
                          {initials(appointment.client_name)}
                        </div>
                        <div className="agenda-person-info">
                          <strong>{appointment.client_name}</strong>
                          <span>
                            {formatTime(appointment.starts_at)}–
                            {formatTime(appointment.ends_at)}
                          </span>
                        </div>
                        <span
                          className={`agenda-dot agenda-dot-${appointment.status.toLowerCase()}`}
                          title={
                            STATUS_LABEL[appointment.status] ??
                            appointment.status
                          }
                        />
                      </div>
                      <div className="agenda-person-details">
                        <span>{appointment.service_name}</span>
                        <span>
                          {collaboratorNames.get(
                            appointment.collaborator_id,
                          ) ?? "Profissional"}
                        </span>
                        {appointment.checked_in_at ? (
                          <span className="agenda-checkin">
                            ✓ Chegou {formatTime(appointment.checked_in_at)}
                          </span>
                        ) : null}
                      </div>
                      {appointment.deposit_amount ? (
                        <span className="agenda-deposit">
                          Sinal {formatPrice(appointment.deposit_amount)}
                        </span>
                      ) : null}
                      <div className="agenda-card-actions">
                        {isManager &&
                        !["CANCELLED", "EXPIRED"].includes(
                          appointment.status,
                        ) ? (
                          <button
                            className="agenda-text-action agenda-text-strong"
                            type="button"
                            disabled={busy}
                            onClick={() => openComanda(appointment)}
                          >
                            Comanda
                          </button>
                        ) : null}
                        {appointment.status === "PENDING_DEPOSIT" ? (
                          <button
                            className="agenda-text-action"
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              handleStatus(
                                appointment,
                                "CONFIRMED",
                                "confirmado",
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
                              className="agenda-text-action"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                handleStatus(
                                  appointment,
                                  "COMPLETED",
                                  "concluído",
                                )
                              }
                            >
                              Concluir
                            </button>
                            <button
                              className="agenda-text-action agenda-text-danger"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                handleStatus(
                                  appointment,
                                  "NO_SHOW",
                                  "falta",
                                )
                              }
                            >
                              Faltou
                            </button>
                          </>
                        ) : null}
                        {!closed ? (
                          <>
                            {!appointment.checked_in_at ? (
                              <button
                                className="agenda-text-action"
                                type="button"
                                disabled={checkinBusy === appointment.id}
                                onClick={() => handleCheckinLink(appointment)}
                              >
                                {checkinBusy === appointment.id
                                  ? "Gerando…"
                                  : "Link check-in"}
                              </button>
                            ) : null}
                            <button
                              className="agenda-text-action"
                              type="button"
                              disabled={busy}
                              onClick={() => startReschedule(appointment)}
                            >
                              Reagendar
                            </button>
                            <button
                              className="agenda-text-action agenda-text-danger"
                              type="button"
                              disabled={busy}
                              onClick={() =>
                                handleStatus(
                                  appointment,
                                  "CANCELLED",
                                  "cancelado",
                                )
                              }
                            >
                              Cancelar
                            </button>
                          </>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}

            <button
              className="agenda-see-more"
              type="button"
              onClick={openForm}
            >
              + Adicionar atendimento
            </button>
          </aside>

          <section className="agenda-calendar-panel">
            <div className="agenda-calendar-toolbar">
              <div>
                <span className="agenda-eyebrow">Calendário</span>
                <h2>{monthLabel(month)}</h2>
              </div>
              <div className="agenda-calendar-controls">
                {isManager ? (
                  <select
                    aria-label="Filtrar profissional"
                    className="select"
                    value={filterCollaborator}
                    onChange={(event) =>
                      setFilterCollaborator(event.target.value)
                    }
                  >
                    <option value="">Todos os profissionais</option>
                    {users.map((user) => (
                      <option key={user.id} value={user.id}>
                        {user.full_name}
                      </option>
                    ))}
                  </select>
                ) : null}
                <button
                  className="agenda-nav-button"
                  type="button"
                  aria-label="Mês anterior"
                  onClick={() => goToMonth(shiftMonth(month, -1))}
                >
                  ‹
                </button>
                <button
                  className="agenda-nav-button"
                  type="button"
                  aria-label="Próximo mês"
                  onClick={() => goToMonth(shiftMonth(month, 1))}
                >
                  ›
                </button>
              </div>
            </div>

            <div className="agenda-weekdays">
              {WEEKDAYS.map((weekday) => (
                <span key={weekday}>{weekday}</span>
              ))}
            </div>

            <div className="agenda-month-grid">
              {cells.map((cell) => {
                const dayAppointments = byDate[cell.date] ?? [];
                const selected = cell.date === selectedDate;
                const isToday = cell.date === today;
                return (
                  <button
                    key={cell.date}
                    className={`agenda-day ${
                      cell.inMonth ? "" : "agenda-day-outside"
                    } ${selected ? "agenda-day-selected" : ""} ${
                      isToday ? "agenda-day-today" : ""
                    }`}
                    type="button"
                    onClick={() => selectDate(cell.date)}
                  >
                    <span className="agenda-day-number">
                      {dayNumber(cell.date)}
                    </span>
                    <span className="agenda-day-events">
                      {dayAppointments.slice(0, 3).map((appointment) => (
                        <span
                          className={statusClass(appointment.status)}
                          key={appointment.id}
                          title={`${formatTime(appointment.starts_at)} · ${
                            appointment.client_name
                          } · ${appointment.service_name}`}
                        >
                          {formatTime(appointment.starts_at)}{" "}
                          {appointment.client_name.split(" ")[0]}
                        </span>
                      ))}
                      {dayAppointments.length > 3 ? (
                        <span className="agenda-more-events">
                          +{dayAppointments.length - 3}
                        </span>
                      ) : null}
                    </span>
                  </button>
                );
              })}
            </div>

            <div className="agenda-legend">
              <span>
                <i className="agenda-dot agenda-dot-scheduled" /> Agendado
              </span>
              <span>
                <i className="agenda-dot agenda-dot-confirmed" /> Confirmado
              </span>
              <span>
                <i className="agenda-dot agenda-dot-pending_deposit" /> Sinal
              </span>
              <span>
                <i className="agenda-dot agenda-dot-completed" /> Concluído
              </span>
              <span>
                <i className="agenda-dot agenda-dot-no_show" /> Falta
              </span>
            </div>
          </section>
        </div>

        {showForm ? (
          <div
            className="agenda-modal-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) setShowForm(false);
            }}
          >
            <section className="agenda-modal">
              <div className="agenda-modal-head">
                <div>
                  <span className="agenda-eyebrow">Novo atendimento</span>
                  <h2>{formatDateLabel(selectedDate)}</h2>
                </div>
                <button
                  className="agenda-nav-button"
                  type="button"
                  aria-label="Fechar"
                  onClick={() => setShowForm(false)}
                >
                  ×
                </button>
              </div>

              <form onSubmit={handleCreate}>
                <div className="field">
                  <label htmlFor="agenda-client">Cliente</label>
                  <select
                    id="agenda-client"
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

                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="agenda-service">Serviço</label>
                    <select
                      id="agenda-service"
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
                    <label htmlFor="agenda-collaborator">Profissional</label>
                    {isManager ? (
                      <select
                        id="agenda-collaborator"
                        value={formCollaborator}
                        onChange={(event) =>
                          setFormCollaborator(event.target.value)
                        }
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
                      <input
                        id="agenda-collaborator"
                        value={me.full_name}
                        disabled
                      />
                    )}
                  </div>
                </div>

                <div className="field">
                  <label>Horários livres</label>
                  <div className="slot-grid">
                    {slotsLoading ? (
                      <span className="appointment-sub">Carregando…</span>
                    ) : slots.length === 0 ? (
                      <span className="appointment-sub">
                        Sem horários livres para este serviço.
                      </span>
                    ) : (
                      slots.map((slot) => (
                        <button
                          key={slot}
                          className={`slot ${
                            formTime === slot ? "active" : ""
                          }`}
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
                  <label htmlFor="agenda-time">Horário</label>
                  <input
                    id="agenda-time"
                    type="time"
                    value={formTime}
                    onChange={(event) => setFormTime(event.target.value)}
                    required
                  />
                </div>

                <div className="agenda-modal-actions">
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={() => setShowForm(false)}
                  >
                    Cancelar
                  </button>
                  <button className="button" type="submit" disabled={saving}>
                    {saving ? "Agendando…" : "Confirmar agendamento"}
                  </button>
                </div>
              </form>
            </section>
          </div>
        ) : null}

        {sale ? (
          <div
            className="agenda-modal-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) setSale(null);
            }}
          >
            <section className="agenda-modal agenda-sale-modal">
              <div className="agenda-modal-head">
                <div>
                  <span className="agenda-eyebrow">Comanda digital</span>
                  <h2>{sale.client_name}</h2>
                  <span className="muted-small">
                    {sale.collaborator_name ?? "Profissional"} ·{" "}
                    {sale.appointment_id
                      ? "vinculada ao agendamento"
                      : "venda avulsa"}
                  </span>
                </div>
                <button
                  className="agenda-nav-button"
                  type="button"
                  aria-label="Fechar"
                  onClick={() => setSale(null)}
                >
                  ×
                </button>
              </div>

              <div className="sale-items">
                {sale.items.map((item) => (
                  <div className="sale-item-row" key={item.id}>
                    <div>
                      <strong>{item.description}</strong>
                      <span>
                        {item.quantity} × {formatPrice(item.unit_price)}
                      </span>
                    </div>
                    <strong>{formatPrice(item.total)}</strong>
                    <button
                      className="agenda-text-action agenda-text-danger"
                      type="button"
                      disabled={saleBusy}
                      onClick={() => handleRemoveSaleItem(item.id)}
                    >
                      remover
                    </button>
                  </div>
                ))}
              </div>

              <div className="sale-add-row sale-add-service">
                <select
                  aria-label="Adicionar serviço"
                  value={saleServiceId}
                  onChange={(event) => setSaleServiceId(event.target.value)}
                >
                  <option value="">Adicionar serviço…</option>
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name} · {formatPrice(service.price)}
                    </option>
                  ))}
                </select>
                <button
                  className="button button-ghost button-small"
                  type="button"
                  disabled={saleBusy || !saleServiceId}
                  onClick={handleAddSaleService}
                >
                  + Serviço
                </button>
              </div>

              <div className="sale-add-row sale-add-manual">
                <input
                  aria-label="Descrição do item avulso"
                  value={saleItemDescription}
                  onChange={(event) =>
                    setSaleItemDescription(event.target.value)
                  }
                  placeholder="Produto ou item avulso"
                />
                <input
                  aria-label="Valor do item avulso"
                  inputMode="decimal"
                  value={saleItemPrice}
                  onChange={(event) => setSaleItemPrice(event.target.value)}
                />
                <button
                  className="button button-ghost button-small"
                  type="button"
                  disabled={saleBusy || !saleItemDescription.trim()}
                  onClick={handleAddManualItem}
                >
                  + Item
                </button>
              </div>

              <div className="sale-summary">
                <div>
                  <span>Subtotal</span>
                  <strong>{formatPrice(sale.subtotal)}</strong>
                </div>
                <div>
                  <span>Desconto</span>
                  <strong>− {formatPrice(sale.discount)}</strong>
                </div>
                <div>
                  <span>Crédito</span>
                  <strong>− {formatPrice(sale.credit_amount)}</strong>
                </div>
                <div className="sale-total">
                  <span>Total</span>
                  <strong>{formatPrice(sale.total)}</strong>
                </div>
              </div>

              <div className="sale-controls">
                <div className="field">
                  <label htmlFor="sale-discount">Desconto (R$)</label>
                  <div className="sale-inline">
                    <input
                      id="sale-discount"
                      inputMode="decimal"
                      value={saleDiscount}
                      onChange={(event) =>
                        setSaleDiscount(event.target.value)
                      }
                    />
                    <button
                      className="button button-ghost button-small"
                      type="button"
                      disabled={saleBusy}
                      onClick={handleSaleDiscount}
                    >
                      Aplicar
                    </button>
                  </div>
                </div>

                {saleCredits.length > 0 ? (
                  <div className="field">
                    <label htmlFor="sale-credit">Crédito do cliente</label>
                    <div className="sale-inline">
                      <select
                        id="sale-credit"
                        value={saleCreditId}
                        onChange={(event) => {
                          setSaleCreditId(event.target.value);
                          const credit = saleCredits.find(
                            (item) => item.id === event.target.value,
                          );
                          setSaleCreditAmount(
                            credit?.remaining_amount ?? "0.00",
                          );
                        }}
                      >
                        <option value="">Selecione…</option>
                        {saleCredits.map((credit) => (
                          <option key={credit.id} value={credit.id}>
                            Saldo {formatPrice(credit.remaining_amount)}
                          </option>
                        ))}
                      </select>
                      <input
                        aria-label="Valor do crédito"
                        inputMode="decimal"
                        value={saleCreditAmount}
                        onChange={(event) =>
                          setSaleCreditAmount(event.target.value)
                        }
                      />
                      <button
                        className="button button-ghost button-small"
                        type="button"
                        disabled={saleBusy || !saleCreditId}
                        onClick={handleSaleCredit}
                      >
                        Aplicar
                      </button>
                    </div>
                  </div>
                ) : null}

                <div className="field">
                  <label htmlFor="sale-notes">Observação</label>
                  <input
                    id="sale-notes"
                    value={saleNotes}
                    onChange={(event) => setSaleNotes(event.target.value)}
                    maxLength={2000}
                  />
                </div>

                <div className="sale-close-grid">
                  <div className="field">
                    <label htmlFor="sale-payment">Pagamento</label>
                    <select
                      id="sale-payment"
                      value={salePaymentMethod}
                      onChange={(event) =>
                        setSalePaymentMethod(
                          event.target.value as SalePaymentMethod,
                        )
                      }
                    >
                      <option value="PIX">Pix</option>
                      <option value="CASH">Dinheiro</option>
                      <option value="CARD">Cartão</option>
                      <option value="BOLETO">Boleto</option>
                      <option value="TRANSFER">Transferência</option>
                      <option value="OTHER">Outro</option>
                    </select>
                  </div>
                  <div className="field">
                    <label htmlFor="sale-account">Conta</label>
                    <select
                      id="sale-account"
                      value={saleAccountId}
                      onChange={(event) =>
                        setSaleAccountId(event.target.value)
                      }
                    >
                      <option value="">Selecione…</option>
                      {saleAccounts.map((account) => (
                        <option key={account.id} value={account.id}>
                          {account.name} · {account.type}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="agenda-modal-actions sale-actions">
                <button
                  className="agenda-text-action agenda-text-danger"
                  type="button"
                  disabled={saleBusy}
                  onClick={handleCancelSale}
                >
                  Cancelar comanda
                </button>
                <button
                  className="button"
                  type="button"
                  disabled={saleBusy || !saleAccountId}
                  onClick={handleCloseSale}
                >
                  {saleBusy
                    ? "Fechando…"
                    : `Fechar comanda · ${formatPrice(sale.total)}`}
                </button>
              </div>
              {error ? <p className="error">{error}</p> : null}
            </section>
          </div>
        ) : null}

        {reschedule ? (
          <div
            className="agenda-modal-backdrop"
            role="presentation"
            onMouseDown={(event) => {
              if (event.target === event.currentTarget) setReschedule(null);
            }}
          >
            <section className="agenda-modal agenda-modal-small">
              <div className="agenda-modal-head">
                <div>
                  <span className="agenda-eyebrow">Reagendar</span>
                  <h2>Novo horário</h2>
                </div>
                <button
                  className="agenda-nav-button"
                  type="button"
                  aria-label="Fechar"
                  onClick={() => setReschedule(null)}
                >
                  ×
                </button>
              </div>
              <form onSubmit={handleReschedule}>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="reschedule-date">Data</label>
                    <input
                      id="reschedule-date"
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
                    <label htmlFor="reschedule-time">Horário</label>
                    <input
                      id="reschedule-time"
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
                <div className="agenda-modal-actions">
                  <button
                    className="button button-ghost"
                    type="button"
                    onClick={() => setReschedule(null)}
                  >
                    Voltar
                  </button>
                  <button
                    className="button"
                    type="submit"
                    disabled={actionId === reschedule.id}
                  >
                    {actionId === reschedule.id
                      ? "Reagendando…"
                      : "Confirmar novo horário"}
                  </button>
                </div>
              </form>
            </section>
          </div>
        ) : null}
      </div>
    </AppShell>
  );
}
