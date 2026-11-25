"use client";

import { useParams } from "next/navigation";
import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type FormEvent,
} from "react";

import {
  ApiError,
  confirmMockPublicPayment,
  createPublicAppointment,
  createPublicSubscription,
  getPublicAvailability,
  getPublicContext,
  type PublicAppointment,
  type PublicContext,
  type PublicPayment,
  type PublicPlan,
} from "@/lib/api";
import {
  formatDateLabel,
  formatIsoDate,
  formatTime,
  shiftDate,
  toTenantIso,
  todayInTenant,
} from "@/lib/agenda";
import { billingCycleLabel, formatPrice, parseMagicToken } from "@/lib/public";

const STATUS_LABEL: Record<string, string> = {
  SCHEDULED: "Agendado",
  PENDING_DEPOSIT: "Aguardando sinal",
  CONFIRMED: "Confirmado",
  CANCELLED: "Cancelado",
  EXPIRED: "Expirado",
};

const INVALID_LINK_MESSAGE =
  "Este link é inválido ou expirou. Peça um novo link para a clínica no WhatsApp.";

type PendingPayment = {
  payment: PublicPayment;
  kind: "appointment" | "subscription";
  appointment?: PublicAppointment;
  plan?: PublicPlan;
};

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
  const [subscribingPlanId, setSubscribingPlanId] = useState<string | null>(
    null,
  );
  const [linkInvalid, setLinkInvalid] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [slotsError, setSlotsError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<PublicAppointment | null>(
    null,
  );
  const [pendingPayment, setPendingPayment] = useState<PendingPayment | null>(
    null,
  );
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [copyLabel, setCopyLabel] = useState("Copiar código Pix");

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
    setSlotsError(null);
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
      } else {
        setSlotsError("Não foi possível carregar os horários. Tente novamente.");
      }
    } finally {
      setLoadingSlots(false);
    }
  }, [slug, token, serviceId, professionalId, date]);

  useEffect(() => {
    void refreshSlots();
  }, [refreshSlots]);

  const reloadContext = useCallback(async () => {
    if (!slug || !token) return null;
    const data = await getPublicContext(slug, token);
    setContext(data);
    return data;
  }, [slug, token]);

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
  const themeStyle = context
    ? ({ "--primary": context.theme_primary_color } as CSSProperties)
    : undefined;

  function openPayment(next: PendingPayment) {
    setPendingPayment(next);
    setConfirmation(null);
    setError(null);
    setCopyLabel("Copiar código Pix");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
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
      if (appointment.payment) {
        openPayment({
          payment: appointment.payment,
          kind: "appointment",
          appointment,
        });
      } else {
        setConfirmation(appointment);
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
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

  async function handleSubscribe(plan: PublicPlan) {
    setError(null);
    setNotice(null);
    if (!slug || !token) return;
    if (!fullName.trim()) {
      setError("Informe seu nome antes de assinar o plano.");
      return;
    }

    setSubscribingPlanId(plan.id);
    try {
      const subscription = await createPublicSubscription(slug, {
        token,
        plan_id: plan.id,
        full_name: fullName.trim(),
      });
      if (subscription.payment) {
        openPayment({
          payment: subscription.payment,
          kind: "subscription",
          plan,
        });
      } else {
        await reloadContext();
        setNotice(`Plano ${plan.name} ativado!`);
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setLinkInvalid(true);
        } else if (err.status === 409 || err.status === 422) {
          setError(err.message);
        } else {
          setError("Não foi possível contratar o plano. Tente novamente.");
        }
      } else {
        setError("Não foi possível contratar o plano. Tente novamente.");
      }
    } finally {
      setSubscribingPlanId(null);
    }
  }

  async function handlePaymentConfirm() {
    if (!pendingPayment || !slug || !token) return;
    setPaymentBusy(true);
    setError(null);
    try {
      const result = await confirmMockPublicPayment(
        slug,
        token,
        pendingPayment.payment.id,
      );
      if (pendingPayment.kind === "appointment" && pendingPayment.appointment) {
        setConfirmation({
          ...pendingPayment.appointment,
          status: result.appointment_status ?? pendingPayment.appointment.status,
          payment: result,
        });
        setPendingPayment(null);
      } else {
        await reloadContext();
        const planName = pendingPayment.plan?.name;
        setPendingPayment(null);
        setNotice(planName ? `Plano ${planName} ativado!` : "Plano ativado!");
      }
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setLinkInvalid(true);
        } else if (
          err.status === 409 &&
          err.message.toLowerCase().includes("expirado")
        ) {
          setPendingPayment(null);
          setError("O pagamento expirou. Escolha um novo horário.");
        } else {
          setError(err.message);
        }
      } else {
        setError("Não foi possível confirmar o Pix. Tente novamente.");
      }
      await reloadContext();
      await refreshSlots();
    } finally {
      setPaymentBusy(false);
    }
  }

  async function handleCopyPix() {
    if (!pendingPayment) return;
    try {
      await navigator.clipboard.writeText(
        pendingPayment.payment.pix_copy_paste,
      );
      setCopyLabel("Copiado!");
    } catch {
      setCopyLabel("Selecione e copie o código");
    }
  }

  function closePayment() {
    if (pendingPayment?.kind === "appointment" && pendingPayment.appointment) {
      setConfirmation(pendingPayment.appointment);
    }
    setPendingPayment(null);
    setError(null);
  }

  function resetBooking() {
    setConfirmation(null);
    setSelectedSlot("");
    setError(null);
    setNotice(null);
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

  if (loading) {
    return (
      <main className="public-shell">
        <div className="public-card public-card-narrow">
          <p className="subtitle">Carregando a agenda da clínica…</p>
        </div>
      </main>
    );
  }

  if (!context) {
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
          <h1>Não foi possível abrir a agenda</h1>
          <p className="subtitle">
            {error ?? "Tente novamente em instantes ou fale com a clínica."}
          </p>
        </div>
      </main>
    );
  }

  if (pendingPayment) {
    const amount = formatPrice(pendingPayment.payment.amount);
    return (
      <main className="public-shell" style={themeStyle}>
        <div className="public-card">
          <div className="brand">
            <div className="brand-mark">S</div>
            <div>
              <div className="brand-name">{context.tenant_name}</div>
              <div className="brand-tag">Pagamento Pix</div>
            </div>
          </div>

          <h1>
            {pendingPayment.kind === "appointment"
              ? "Pague o sinal"
              : "Ative seu plano"}
          </h1>
          <p className="subtitle">
            Escaneie o QR Code ou copie o código Pix. A confirmação libera{" "}
            {pendingPayment.kind === "appointment"
              ? "o seu horário."
              : "as cotas do plano."}
          </p>

          {pendingPayment.plan ? (
            <div className="public-resume">
              <strong>{pendingPayment.plan.name}</strong>
              <span>
                {formatPrice(pendingPayment.plan.price)} ·{" "}
                {billingCycleLabel(pendingPayment.plan.billing_cycle)}
              </span>
            </div>
          ) : null}

          {pendingPayment.appointment ? (
            <div className="public-resume">
              <strong>{pendingPayment.appointment.service_name}</strong>
              <span>
                {formatDateLabel(date)} ·{" "}
                {formatTime(pendingPayment.appointment.starts_at)}–
                {formatTime(pendingPayment.appointment.ends_at)}
              </span>
            </div>
          ) : null}

          <div className="public-payment-amount">{amount}</div>

          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            className="public-qr"
            src={pendingPayment.payment.qr_code_data_uri}
            alt="QR Code Pix"
          />

          <div className="public-pix-box">
            <code>{pendingPayment.payment.pix_copy_paste}</code>
            <button
              className="button button-ghost button-small"
              type="button"
              onClick={handleCopyPix}
            >
              {copyLabel}
            </button>
          </div>

          <p className="public-note">
            Expira às {formatTime(pendingPayment.payment.expires_at)}. Depois
            disso, o horário volta a ficar disponível.
          </p>

          <button
            className="button"
            type="button"
            onClick={handlePaymentConfirm}
            disabled={paymentBusy}
          >
            {paymentBusy ? "Confirmando…" : "Simular pagamento Pix"}
          </button>
          <button
            className="button button-ghost"
            type="button"
            onClick={closePayment}
            disabled={paymentBusy}
          >
            Voltar
          </button>

          {error ? <p className="error">{error}</p> : null}

          <p className="public-note">
            Ambiente de demonstração: o botão acima simula a confirmação do
            Pix. Na produção, o gateway confirma via webhook.
          </p>
        </div>
      </main>
    );
  }

  if (confirmation) {
    const confirmedDeposit = formatPrice(confirmation.deposit_amount);
    return (
      <main className="public-shell" style={themeStyle}>
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

          {confirmation.used_subscription ? (
            <p className="public-note">
              Cota do seu plano utilizada neste agendamento.
            </p>
          ) : null}

          {confirmation.status === "PENDING_DEPOSIT" ? (
            <>
              <p className="public-note">
                Pague o sinal para confirmar seu horário. Sem o pagamento, ele
                é liberado após 10 minutos.
              </p>
              {confirmation.payment ? (
                <button
                  className="button"
                  type="button"
                  onClick={() =>
                    openPayment({
                      payment: confirmation.payment as PublicPayment,
                      kind: "appointment",
                      appointment: confirmation,
                    })
                  }
                >
                  Pagar sinal
                </button>
              ) : null}
            </>
          ) : (
            <p className="public-note">
              Guarde estas informações. Para remarcar, fale com a recepção da
              clínica.
            </p>
          )}

          <button className="button button-ghost" type="button" onClick={resetBooking}>
            Fazer outro agendamento
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="public-shell" style={themeStyle}>
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

        {notice ? <p className="public-notice">{notice}</p> : null}

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

              {slotsError ? (
                <p className="error">{slotsError}</p>
              ) : loadingSlots ? (
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

            {context.plans.length > 0 || context.subscription ? (
              <section className="public-step">
                <h2>5. Clube de assinatura</h2>
                {context.subscription ? (
                  <div className="public-subscription">
                    <div className="public-subscription-head">
                      <strong>{context.subscription.plan_name}</strong>
                      <span>
                        Ativo até{" "}
                        {formatIsoDate(context.subscription.current_period_end)}
                      </span>
                    </div>
                    <div className="public-quota-list">
                      {context.subscription.quotas.map((quota) => (
                        <div key={quota.service_id}>
                          <span>{quota.service_name}</span>
                          <strong>
                            {quota.remaining} de {quota.uses_per_cycle}{" "}
                            restantes
                          </strong>
                        </div>
                      ))}
                    </div>
                    <p className="public-note">
                      Ao agendar um serviço com cota disponível, ela é usada
                      automaticamente e o sinal é dispensado.
                    </p>
                  </div>
                ) : (
                  <div className="public-plans">
                    {context.plans.map((plan) => (
                      <article className="public-plan" key={plan.id}>
                        <div className="public-plan-info">
                          <strong>{plan.name}</strong>
                          {plan.description ? (
                            <span>{plan.description}</span>
                          ) : null}
                          <div className="public-plan-price">
                            {formatPrice(plan.price)}{" "}
                            <small>
                              {billingCycleLabel(plan.billing_cycle)}
                            </small>
                          </div>
                          <ul>
                            {plan.items.map((item) => (
                              <li key={item.service_id}>
                                {item.service_name} · {item.uses_per_cycle}x por
                                ciclo
                              </li>
                            ))}
                          </ul>
                        </div>
                        <button
                          className="button button-ghost button-small"
                          type="button"
                          onClick={() => handleSubscribe(plan)}
                          disabled={subscribingPlanId !== null}
                        >
                          {subscribingPlanId === plan.id
                            ? "Abrindo…"
                            : "Assinar"}
                        </button>
                      </article>
                    ))}
                  </div>
                )}
              </section>
            ) : null}

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
