"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createService,
  deleteService,
  getMe,
  getServices,
  updateService,
  type Me,
  type Service,
} from "@/lib/api";
import { formatPrice } from "@/lib/public";

export default function ServicesPage() {
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
  const [editing, setEditing] = useState<Service | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadServices = useCallback(async () => {
    setServices(await getServices());
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
            err instanceof ApiError ? err.message : "Falha ao carregar serviços.",
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

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaving(true);
    const payload = {
      name: name.trim(),
      duration_minutes: Number(duration),
      buffer_minutes: Number(buffer),
      price,
      cost,
      requires_deposit: requiresDeposit,
      deposit_amount: requiresDeposit ? depositAmount : null,
      show_average_price: showAveragePrice,
    };
    try {
      if (editing) {
        await updateService(editing.id, payload);
      } else {
        await createService(payload);
      }
      setName("");
      setEditing(null);
      await loadServices();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar serviço.",
      );
    } finally {
      setSaving(false);
    }
  }

  function startEdit(service: Service) {
    setEditing(service);
    setName(service.name);
    setDuration(String(service.duration_minutes));
    setBuffer(String(service.buffer_minutes));
    setPrice(service.price);
    setCost(service.cost);
    setRequiresDeposit(service.requires_deposit);
    setDepositAmount(service.deposit_amount ?? "30.00");
    setShowAveragePrice(service.show_average_price);
    setError(null);
  }

  function cancelEdit() {
    setEditing(null);
    setName("");
    setDuration("60");
    setBuffer("0");
    setPrice("120.00");
    setCost("0.00");
    setRequiresDeposit(false);
    setDepositAmount("30.00");
    setShowAveragePrice(true);
  }

  async function handleDelete(service: Service) {
    if (!window.confirm(`Excluir o serviço ${service.name}?`)) return;
    setError(null);
    try {
      await deleteService(service.id);
      if (editing?.id === service.id) cancelEdit();
      await loadServices();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir serviço.",
      );
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
            <h1>Serviços</h1>
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
              <h2>Serviços cadastrados</h2>
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
                            ? formatPrice(service.deposit_amount)
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
                            <div className="row-actions">
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => startEdit(service)}
                              >
                                Editar
                              </button>
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => toggleActive(service)}
                              >
                                {service.is_active ? "Desativar" : "Ativar"}
                              </button>
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                onClick={() => handleDelete(service)}
                              >
                                Excluir
                              </button>
                            </div>
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
                <h2>{editing ? "Editar serviço" : "Novo serviço"}</h2>
                {editing ? (
                  <button
                    className="button button-ghost button-small"
                    type="button"
                    onClick={cancelEdit}
                  >
                    Cancelar edição
                  </button>
                ) : null}
              </div>
              <form onSubmit={handleSave}>
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
                  {saving
                    ? "Salvando…"
                    : editing
                      ? "Salvar alterações"
                      : "Cadastrar serviço"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
