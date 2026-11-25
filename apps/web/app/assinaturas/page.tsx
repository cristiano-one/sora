"use client";

import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  cancelSubscription,
  createClientSubscription,
  createSubscriptionPlan,
  getClients,
  getMe,
  getServices,
  getSubscriptionPlans,
  getSubscriptions,
  updateSubscriptionPlan,
  type Client,
  type ClientSubscription,
  type Me,
  type Service,
  type SubscriptionPlan,
} from "@/lib/api";
import { formatIsoDate } from "@/lib/agenda";
import { billingCycleLabel, formatPrice } from "@/lib/public";

const STATUS_LABEL: Record<string, string> = {
  PENDING_PAYMENT: "Aguardando pagamento",
  ACTIVE: "Ativa",
  CANCELLED: "Cancelada",
  EXPIRED: "Expirada",
};

export default function SubscriptionsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [subscriptions, setSubscriptions] = useState<ClientSubscription[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [planName, setPlanName] = useState("");
  const [planDescription, setPlanDescription] = useState("");
  const [planPrice, setPlanPrice] = useState("149.90");
  const [planCycle, setPlanCycle] = useState<"MONTHLY" | "QUARTERLY">(
    "MONTHLY",
  );
  const [planServiceId, setPlanServiceId] = useState("");
  const [planUses, setPlanUses] = useState("4");
  const [planInterval, setPlanInterval] = useState("");
  const [contractClientId, setContractClientId] = useState("");
  const [contractPlanId, setContractPlanId] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingPlan, setSavingPlan] = useState(false);
  const [savingContract, setSavingContract] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const serviceNames = useMemo(() => {
    const map = new Map<string, string>();
    for (const service of services) map.set(service.id, service.name);
    return map;
  }, [services]);

  const reload = useCallback(async () => {
    const [planData, subscriptionData] = await Promise.all([
      getSubscriptionPlans(),
      getSubscriptions(),
    ]);
    setPlans(planData);
    setSubscriptions(subscriptionData);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([
      getMe(),
      getSubscriptionPlans(),
      getSubscriptions(),
      getClients(),
      getServices(),
    ])
      .then(([user, planData, subscriptionData, clientData, serviceData]) => {
        if (!active) return;
        const activeServices = serviceData.filter(
          (service) => service.is_active,
        );
        const activePlans = planData.filter((plan) => plan.is_active);
        setMe(user);
        setPlans(planData);
        setSubscriptions(subscriptionData);
        setClients(clientData);
        setServices(activeServices);
        if (activeServices.length > 0) {
          setPlanServiceId(activeServices[0].id);
        }
        if (clientData.length > 0) {
          setContractClientId(clientData[0].id);
        }
        if (activePlans.length > 0) {
          setContractPlanId(activePlans[0].id);
        }
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Falha ao carregar assinaturas.",
          );
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function handleCreatePlan(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!planServiceId) {
      setError("Cadastre um serviço antes de criar um plano.");
      return;
    }
    setSavingPlan(true);
    try {
      await createSubscriptionPlan({
        name: planName.trim(),
        description: planDescription.trim() || undefined,
        price: planPrice,
        billing_cycle: planCycle,
        items: [
          {
            service_id: planServiceId,
            uses_per_cycle: Number(planUses),
            min_interval_days:
              planInterval.trim() === "" ? null : Number(planInterval),
          },
        ],
      });
      setPlanName("");
      setPlanDescription("");
      setPlanInterval("");
      await reload();
      setNotice("Plano criado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao criar plano.",
      );
    } finally {
      setSavingPlan(false);
    }
  }

  async function togglePlan(plan: SubscriptionPlan) {
    setError(null);
    try {
      await updateSubscriptionPlan(plan.id, { is_active: !plan.is_active });
      await reload();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar plano.",
      );
    }
  }

  async function handleContract(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (!contractClientId || !contractPlanId) {
      setError("Selecione o cliente e o plano.");
      return;
    }
    setSavingContract(true);
    try {
      await createClientSubscription(contractClientId, contractPlanId);
      await reload();
      setNotice("Assinatura ativada para o cliente.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao contratar plano.",
      );
    } finally {
      setSavingContract(false);
    }
  }

  async function handleCancel(subscription: ClientSubscription) {
    if (!window.confirm(`Cancelar a assinatura de ${subscription.client_name}?`)) {
      return;
    }
    setError(null);
    try {
      await cancelSubscription(subscription.id);
      await reload();
      setNotice("Assinatura cancelada.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao cancelar assinatura.",
      );
    }
  }

  if (!isManager && me) {
    return (
      <AppShell>
        <div className="page">
          <p className="error">Apenas dono ou administrador acessa assinaturas.</p>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Assinaturas</h1>
            <p>
              Clubes de recorrência, cotas por serviço e assinantes da clínica.
            </p>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        <section className="panel subscriptions-panel">
          <div className="panel-title">
            <h2>Assinantes</h2>
            <span className="muted-small">
              {subscriptions.length} assinatura(s)
            </span>
          </div>
          {loading ? (
            <p className="table-empty">Carregando…</p>
          ) : subscriptions.length === 0 ? (
            <p className="table-empty">Nenhuma assinatura contratada.</p>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Plano</th>
                    <th>Cotas</th>
                    <th>Vigência</th>
                    <th>Status</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((subscription) => (
                    <tr key={subscription.id}>
                      <td>
                        <strong>{subscription.client_name}</strong>
                      </td>
                      <td>{subscription.plan_name}</td>
                      <td className="muted-small">
                        {subscription.quotas
                          .map(
                            (quota) =>
                              `${quota.service_name}: ${quota.used}/${quota.uses_per_cycle}`,
                          )
                          .join(" · ") || "—"}
                      </td>
                      <td className="muted-small">
                        até {formatIsoDate(subscription.current_period_end)}
                      </td>
                      <td>
                        <span
                          className={`pill ${
                            subscription.status === "ACTIVE"
                              ? "pill-active"
                              : ""
                          }`}
                        >
                          {STATUS_LABEL[subscription.status] ??
                            subscription.status}
                        </span>
                      </td>
                      <td>
                        {subscription.status === "ACTIVE" ||
                        subscription.status === "PENDING_PAYMENT" ? (
                          <button
                            className="button button-ghost button-small"
                            type="button"
                            onClick={() => handleCancel(subscription)}
                          >
                            Cancelar
                          </button>
                        ) : null}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <div className="admin-grid subscriptions-grid">
          <section className="panel">
            <div className="panel-title">
              <h2>Planos</h2>
              <span className="muted-small">{plans.length} plano(s)</span>
            </div>
            {plans.length === 0 ? (
              <p className="table-empty">Nenhum plano cadastrado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Plano</th>
                      <th>Preço</th>
                      <th>Cotas</th>
                      <th>Status</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {plans.map((plan) => (
                      <tr key={plan.id}>
                        <td>
                          <strong>{plan.name}</strong>
                          {plan.description ? (
                            <div className="muted-small">
                              {plan.description}
                            </div>
                          ) : null}
                        </td>
                        <td className="price-cell">
                          {formatPrice(plan.price)}{" "}
                          <span className="muted-small">
                            {billingCycleLabel(plan.billing_cycle)}
                          </span>
                        </td>
                        <td className="muted-small">
                          {plan.items
                            .map(
                              (item) =>
                                `${serviceNames.get(item.service_id) ?? "Serviço"}: ${item.uses_per_cycle}x`,
                            )
                            .join(" · ")}
                        </td>
                        <td>
                          {plan.is_active ? (
                            <span className="pill pill-active">Ativo</span>
                          ) : (
                            <span className="pill">Inativo</span>
                          )}
                        </td>
                        <td>
                          <button
                            className="button button-ghost button-small"
                            type="button"
                            onClick={() => togglePlan(plan)}
                          >
                            {plan.is_active ? "Desativar" : "Ativar"}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-title">
              <h2>Contratar para cliente</h2>
            </div>
            <form onSubmit={handleContract}>
              <div className="field">
                <label htmlFor="contract-client">Cliente</label>
                <select
                  id="contract-client"
                  value={contractClientId}
                  onChange={(event) => setContractClientId(event.target.value)}
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
                <label htmlFor="contract-plan">Plano</label>
                <select
                  id="contract-plan"
                  value={contractPlanId}
                  onChange={(event) => setContractPlanId(event.target.value)}
                  required
                >
                  <option value="">Selecione…</option>
                  {plans
                    .filter((plan) => plan.is_active)
                    .map((plan) => (
                      <option key={plan.id} value={plan.id}>
                        {plan.name} · {formatPrice(plan.price)}
                      </option>
                    ))}
                </select>
              </div>
              <button
                className="button"
                type="submit"
                disabled={savingContract}
              >
                {savingContract ? "Ativando…" : "Ativar assinatura"}
              </button>
            </form>
          </section>
        </div>

        <section className="panel subscriptions-panel">
          <div className="panel-title">
            <h2>Novo plano</h2>
          </div>
          <form onSubmit={handleCreatePlan}>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="plan-name">Nome</label>
                <input
                  id="plan-name"
                  value={planName}
                  onChange={(event) => setPlanName(event.target.value)}
                  required
                  maxLength={255}
                />
              </div>
              <div className="field">
                <label htmlFor="plan-price">Preço (R$)</label>
                <input
                  id="plan-price"
                  value={planPrice}
                  onChange={(event) => setPlanPrice(event.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="plan-cycle">Ciclo</label>
                <select
                  id="plan-cycle"
                  value={planCycle}
                  onChange={(event) =>
                    setPlanCycle(
                      event.target.value as "MONTHLY" | "QUARTERLY",
                    )
                  }
                >
                  <option value="MONTHLY">Mensal</option>
                  <option value="QUARTERLY">Trimestral</option>
                </select>
              </div>
              <div className="field">
                <label htmlFor="plan-service">Serviço incluído</label>
                <select
                  id="plan-service"
                  value={planServiceId}
                  onChange={(event) => setPlanServiceId(event.target.value)}
                  required
                >
                  <option value="">Selecione…</option>
                  {services.map((service) => (
                    <option key={service.id} value={service.id}>
                      {service.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="plan-uses">Usos por ciclo</label>
                <input
                  id="plan-uses"
                  type="number"
                  min={1}
                  value={planUses}
                  onChange={(event) => setPlanUses(event.target.value)}
                  required
                />
              </div>
              <div className="field">
                <label htmlFor="plan-interval">
                  Intervalo mínimo (dias)
                </label>
                <input
                  id="plan-interval"
                  type="number"
                  min={0}
                  value={planInterval}
                  onChange={(event) => setPlanInterval(event.target.value)}
                  placeholder="Opcional"
                />
              </div>
            </div>
            <div className="field plan-description">
              <label htmlFor="plan-description">Descrição (opcional)</label>
              <input
                id="plan-description"
                value={planDescription}
                onChange={(event) => setPlanDescription(event.target.value)}
                maxLength={2000}
              />
            </div>
            <button className="button" type="submit" disabled={savingPlan}>
              {savingPlan ? "Criando…" : "Criar plano"}
            </button>
          </form>
        </section>
      </div>
    </AppShell>
  );
}
