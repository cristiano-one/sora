"use client";

import { useParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";

import {
  ApiError,
  createPublicAppointment,
  getPublicAvailability,
  getPublicContext,
  type PublicAppointment,
  type PublicContext,
} from "@/lib/api";
import {
  formatDateLabel,
  formatTime,
  shiftDate,
  toTenantIso,
  todayInTenant,
} from "@/lib/agenda";
import { formatPrice, parseMagicToken } from "@/lib/public";

const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: "Agendado",
  PENDING_DEPOSIT: "Aguardando sinal",
  CONFIRMED: "Confirmado",
};

const INVALID_LINK_MESSAGE =
  "Este link é inválido ou expirou. Peça um novo link para a clínica no WhatsApp.";

export default function PublicBookingPage() {
  const params = useParams<{ slug: string }>();
  const slug = Array.isArray(params.slug) ? params.slug[0] : params.slug;
  const [token, setToken] = useState<string | null>(null);
  const [context, setContext] = useState<PublicContext | null>(null);
  const [date, setDate] = useState(todayInTenant());
  const [serviceId, setServiceId] = useState("");
  const [professionalId, setProfessionalId] = useState("");
  const [slots, setSlots] = useState<string[]>([]);
  const [selectedSlot, setSelectedSlot] = useState("");
  const [fullName, setFullName] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingSlots, setLoadingSlots] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [linkInvalid, setLinkInvalid] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<PublicAppointment | null>(
    null,
  );

  useEffect(() => {
    if (!slug) {
      setLinkInvalid(true);
      setLoading(false);
      return;
    }
    const magic = parseMagicToken(window.location.search);
    if (!magic) {
      setLinkInvalid(true);
      setLoading(false);
      return;
    }

    let active = true;
    setToken(magic);
    getPublicContext(slug, magic)
      .then((data) => {
        if (!active) return;
        setContext(data);
        setFullName(data.client_name ?? "");
        if (data.services.length > 0) {
          setServiceId(data.services[0].id);
        }
        if (data.professionals.length > 0) {
          setProfessionalId(data.professionals[0].id);
        }
      })
      .catch((err) => {
        if (!active) return;
        if (err instanceof ApiError && err.status === 401) {
          setLinkInvalid(true);
        } else {
          setError("Não foi possível abrir a agenda da clínica.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [slug]);

  const refreshSlots = useCallback(async () => {
    if (!slug || !token || !serviceId || !professionalId || !date) {
      setSlots([]);
      return;
    }
    setLoadingSlots(true);
    try {
      const data = await getPublicAvailability(
        slug,
        token,
        serviceId,
        professionalId,
        date,
      );
      setSlots(data.available_slots);
      setSelectedSlot((current) =>
        data.available_slots.includes(current) ? current : "",
      );
    } catch (err) {
      setSlots([]);
      setSelectedSlot("");
      if (err instanceof ApiError && err.status === 401) {
        setLinkInvalid(true);
      }
    } finally {
      setLoadingSlots(false);
    }
  }, [slug, token, serviceId, professionalId, date]);

  useEffect(() => {
    void refreshSlots();
  }, [refreshSlots]);

  const service = useMemo(
    () => context?.services.find((item) => item.id === serviceId) ?? null,
    [context, serviceId],
  );
  const professional = useMemo(
    () =>
      context?.professionals.find((item) => item.id === professionalId) ??
      null,
    [context, professionalId],
  );
  const hasOptions =
    Boolean(context) &&
    (context?.services.length ?? 0) > 0 &&
    (context?.professionals.length ?? 0) > 0;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (
      !slug ||
      !token ||
      !serviceId ||
      !professionalId ||
      !selectedSlot ||
      !fullName.trim()
    ) {
      setError("Escolha o serviço, o profissional, o horário e informe seu nome.");
      return;
    }

    setSubmitting(true);
    try {
      const appointment = await createPublicAppointment(slug, {
        token,
        service_id: serviceId,
        collaborator_id: professionalId,
        starts_at: toTenantIso(date, selectedSlot),
        full_name: fullName.trim(),
      });
      setConfirmation(appointment);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setLinkInvalid(true);
        } else if (err.status === 409 || err.status === 422) {
          setError(err.message);
        } else {
          setError("Não foi possível concluir o agendamento. Tente novamente.");
        }
      } else {
        setError("Não foi possível concluir o agendamento. Tente novamente.");
      }
      await refreshSlots();
    } finally {
      setSubmitting(false);
    }
  }

  function resetBooking() {
    setConfirmation(null);
    setSelectedSlot("");
    setError(null);
    void refreshSlots();
  }

  if (linkInvalid) {
    return (
      <main className="public-shell">
        <div className="public-card public-card-narrow">
          <div className="brand">
            <div className="brand-mark">S</div>
            <div>
              <div className="brand-name">Sora Studio</div>
              <div className="brand-tag">Agendamento online</div>
            </div>
          </div>
          <h1>Link inválido ou expirado</h1>
          <p className="subtitle">{INVALID_LINK_MESSAGE}</p>
        </div>
      </main>
    );
  }

  if (loading || !context) {
    return (
      <main className="public-shell">
        <div className="public-card public-card-narrow">
          <p className="subtitle">Carregando a agenda da clínica…</p>
        </div>
      </main>
    );
  }

  if (confirmation) {
    const confirmedDeposit = formatPrice(confirmation.deposit_amount);
    return (
      <main className="public-shell">
        <div className="public-card">
          <div className="brand">
            <div className="brand-mark">S</div>
            <div>
              <div className="brand-name">Sora Studio</div>
              <div className="brand-tag">{context.tenant_name}</div>
            </div>
          </div>

          <div className="public-success-mark">✓</div>
          <h1>Horário reservado!</h1>
          <p className="subtitle">
            {confirmation.status === "PENDING_DEPOSIT"
              ? "Seu horário está reservado aguardando o sinal."
              : "Seu agendamento foi registrado com sucesso."}
          </p>

          <dl className="public-summary">
            <div>
              <dt>Serviço</dt>
              <dd>{confirmation.service_name}</dd>
            </div>
            <div>
              <dt>Profissional</dt>
              <dd>{confirmation.collaborator_name}</dd>
            </div>
            <div>
              <dt>Data</dt>
              <dd>{formatDateLabel(date)}</dd>
            </div>
            <div>
              <dt>Horário</dt>
              <dd>
                {formatTime(confirmation.starts_at)}–
                {formatTime(confirmation.ends_at)}
              </dd>
            </div>
            <div>
              <dt>Status</dt>
              <dd>
                {STATUS_LABEL[confirmation.status] ?? confirmation.status}
              </dd>
            </div>
            {confirmedDeposit ? (
              <div>
                <dt>Sinal</dt>
                <dd>{confirmedDeposit}</dd>
              </div>
            ) : null}
          </dl>

          {confirmation.status === "PENDING_DEPOSIT" ? (
            <p className="public-note">
              Este serviço exige um sinal. A clínica entrará em contato para
              combinar o Pix.
            </p>
          ) : (
            <p className="public-note">
              Guarde estas informações. Para remarcar, fale com a recepção da
              clínica.
            </p>
          )}

          <button className="button" type="button" onClick={resetBooking}>
            Fazer outro agendamento
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="public-shell">
      <div className="public-card">
        <div className="brand">
          <div className="brand-mark">S</div>
          <div>
            <div className="brand-name">{context.tenant_name}</div>
            <div className="brand-tag">Agendamento online</div>
          </div>
        </div>

        <h1>
          {context.client_name
            ? `Olá, ${context.client_name.split(" ")[0]}!`
            : "Agende seu horário"}
        </h1>
        <p className="subtitle">
          Escolha o serviço, o profissional e um horário livre. Leva menos de um
          minuto.
        </p>

        {!hasOptions ? (
          <p className="public-empty">
            A clínica ainda não disponibilizou horários para agendamento online.
          </p>
        ) : (
          <form onSubmit={handleSubmit}>
            <section className="public-step">
              <h2>1. Serviço</h2>
              <div className="public-options">
                {context.services.map((item) => {
                  const price = formatPrice(item.price);
                  return (
                    <button
                      key={item.id}
                      className={`public-option ${
                        serviceId === item.id ? "active" : ""
                      }`}
                      type="button"
                      onClick={() => {
                        setServiceId(item.id);
                        setSelectedSlot("");
                      }}
                    >
                      <strong>{item.name}</strong>
                      <span>
                        {item.duration_minutes} min
                        {price ? ` · ${price}` : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>

            <section className="public-step">
              <h2>2. Profissional</h2>
              <div className="public-options public-options-row">
                {context.professionals.map((item) => (
                  <button
                    key={item.id}
                    className={`public-option ${
                      professionalId === item.id ? "active" : ""
                    }`}
                    type="button"
                    onClick={() => {
                      setProfessionalId(item.id);
                      setSelectedSlot("");
                    }}
                  >
                    <strong>{item.full_name}</strong>
                  </button>
                ))}
              </div>
            </section>

            <section className="public-step">
              <h2>3. Data e horário</h2>
              <div className="public-datebar">
                <button
                  className="button button-ghost button-small"
                  type="button"
                  onClick={() => setDate(shiftDate(date, -1))}
                  disabled={!date || date <= todayInTenant()}
                >
                  ←
                </button>
                <input
                  aria-label="Data"
                  type="date"
                  value={date}
                  min={todayInTenant()}
                  onChange={(event) => {
                    if (!event.target.value) return;
                    setDate(event.target.value);
                    setSelectedSlot("");
                  }}
                />
                <button
                  className="button button-ghost button-small"
                  type="button"
                  onClick={() => setDate(shiftDate(date, 1))}
                  disabled={!date}
                >
                  →
                </button>
              </div>
              <p className="public-date-label">
                {date ? formatDateLabel(date) : "Escolha uma data"}
              </p>

              {loadingSlots ? (
                <p className="public-empty">Buscando horários livres…</p>
              ) : slots.length === 0 ? (
                <p className="public-empty">
                  Nenhum horário livre neste dia. Tente outra data.
                </p>
              ) : (
                <div className="slot-grid">
                  {slots.map((slot) => (
                    <button
                      key={slot}
                      className={`slot ${selectedSlot === slot ? "active" : ""}`}
                      type="button"
                      onClick={() => setSelectedSlot(slot)}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              )}
            </section>

            <section className="public-step">
              <h2>4. Seus dados</h2>
              <div className="field">
                <label htmlFor="full-name">Nome completo</label>
                <input
                  id="full-name"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Como devemos chamar você?"
                  maxLength={255}
                  required
                />
              </div>
            </section>

            {service && professional ? (
              <div className="public-resume">
                <strong>{service.name}</strong>
                <span>
                  {professional.full_name} · {formatDateLabel(date)}
                  {selectedSlot ? ` · ${selectedSlot}` : ""}
                </span>
              </div>
            ) : null}

            <button className="button" type="submit" disabled={submitting}>
              {submitting ? "Reservando…" : "Confirmar agendamento"}
            </button>

            {error ? <p className="error">{error}</p> : null}

            <p className="public-note">
              Ao confirmar, você concorda com o contato da clínica sobre este
              agendamento.
            </p>
          </form>
        )}
      </div>
    </main>
  );
}
