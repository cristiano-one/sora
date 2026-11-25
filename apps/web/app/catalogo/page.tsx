"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createService,
  getMe,
  getServices,
  updateService,
  type Me,
  type Service,
} from "@/lib/api";
import { formatPrice } from "@/lib/public";

export default function CatalogPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [name, setName] = useState("");
  const [duration, setDuration] = useState("60");
  const [buffer, setBuffer] = useState("0");
  const [price, setPrice] = useState("120.00");
  const [cost, setCost] = useState("0.00");
  const [requiresDeposit, setRequiresDeposit] = useState(false);
  const [depositAmount, setDepositAmount] = useState("30.00");
  const [showAveragePrice, setShowAveragePrice] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadServices = useCallback(async () => {
    const data = await getServices();
    setServices(data);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getServices()])
      .then(([user, data]) => {
        if (!active) return;
        setMe(user);
        setServices(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar catálogo.",
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

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await createService({
        name: name.trim(),
        duration_minutes: Number(duration),
        buffer_minutes: Number(buffer),
        price,
        cost,
        requires_deposit: requiresDeposit,
        deposit_amount: requiresDeposit ? depositAmount : null,
        show_average_price: showAveragePrice,
      });
      setName("");
      await loadServices();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao cadastrar serviço.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function toggleActive(service: Service) {
    setError(null);
    try {
      await updateService(service.id, { is_active: !service.is_active });
      await loadServices();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar serviço.",
      );
    }
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Catálogo</h1>
            <p>
              Duração real, buffer, preço, custo de insumo e regra de sinal por
              serviço.
            </p>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}

        <div className={`admin-grid ${isManager ? "" : "admin-grid-wide"}`}>
          <section className="panel">
            <div className="panel-title">
              <h2>Serviços</h2>
              <span className="muted-small">{services.length} cadastrados</span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : services.length === 0 ? (
              <p className="table-empty">Nenhum serviço cadastrado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Serviço</th>
                      <th>Duração</th>
                      <th>Preço</th>
                      <th>Sinal</th>
                      <th>Status</th>
                      {isManager ? <th /> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {services.map((service) => (
                      <tr key={service.id}>
                        <td>
                          <strong>{service.name}</strong>
                          {service.description ? (
                            <div className="muted-small">
                              {service.description}
                            </div>
                          ) : null}
                        </td>
                        <td>
                          {service.duration_minutes} min
                          {service.buffer_minutes > 0
                            ? ` + ${service.buffer_minutes}`
                            : ""}
                        </td>
                        <td className="price-cell">
                          {formatPrice(service.price)}
                        </td>
                        <td className="price-cell">
                          {service.requires_deposit
                            ? formatPrice(service.deposit_amount) ?? "—"
                            : "—"}
                        </td>
                        <td>
                          {service.is_active ? (
                            <span className="pill pill-active">Ativo</span>
                          ) : (
                            <span className="pill">Inativo</span>
                          )}
                        </td>
                        {isManager ? (
                          <td>
                            <button
                              className="button button-ghost button-small"
                              type="button"
                              onClick={() => toggleActive(service)}
                            >
                              {service.is_active ? "Desativar" : "Ativar"}
                            </button>
                          </td>
                        ) : null}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {isManager ? (
            <section className="panel">
              <div className="panel-title">
                <h2>Novo serviço</h2>
              </div>
              <form onSubmit={handleCreate}>
                <div className="field">
                  <label htmlFor="service-name">Nome</label>
                  <input
                    id="service-name"
                    value={name}
                    onChange={(event) => setName(event.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="service-duration">Duração (min)</label>
                    <input
                      id="service-duration"
                      type="number"
                      min={5}
                      value={duration}
                      onChange={(event) => setDuration(event.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="service-buffer">Buffer (min)</label>
                    <input
                      id="service-buffer"
                      type="number"
                      min={0}
                      value={buffer}
                      onChange={(event) => setBuffer(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="service-price">Preço (R$)</label>
                    <input
                      id="service-price"
                      value={price}
                      onChange={(event) => setPrice(event.target.value)}
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="service-cost">Custo (R$)</label>
                    <input
                      id="service-cost"
                      value={cost}
                      onChange={(event) => setCost(event.target.value)}
                    />
                  </div>
                </div>

                <div className="checkbox-field">
                  <input
                    id="service-deposit"
                    type="checkbox"
                    checked={requiresDeposit}
                    onChange={(event) =>
                      setRequiresDeposit(event.target.checked)
                    }
                  />
                  <label htmlFor="service-deposit">Exige sinal</label>
                </div>

                {requiresDeposit ? (
                  <div className="field">
                    <label htmlFor="service-deposit-amount">
                      Valor do sinal (R$)
                    </label>
                    <input
                      id="service-deposit-amount"
                      value={depositAmount}
                      onChange={(event) =>
                        setDepositAmount(event.target.value)
                      }
                    />
                  </div>
                ) : null}

                <div className="checkbox-field">
                  <input
                    id="service-price-visible"
                    type="checkbox"
                    checked={showAveragePrice}
                    onChange={(event) =>
                      setShowAveragePrice(event.target.checked)
                    }
                  />
                  <label htmlFor="service-price-visible">
                    Mostrar preço no link público
                  </label>
                </div>

                <button className="button" type="submit" disabled={saving}>
                  {saving ? "Salvando…" : "Cadastrar serviço"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
