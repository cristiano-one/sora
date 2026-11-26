"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createPackage,
  createService,
  deletePackage,
  deleteService,
  getMe,
  getPackages,
  getServices,
  updatePackage,
  updateService,
  type Me,
  type Package,
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
  const [editing, setEditing] = useState<Service | null>(null);
  const [packages, setPackages] = useState<Package[]>([]);
  const [pkgName, setPkgName] = useState("");
  const [pkgDescription, setPkgDescription] = useState("");
  const [pkgPrice, setPkgPrice] = useState("0.00");
  const [pkgActive, setPkgActive] = useState(true);
  const [pkgItems, setPkgItems] = useState<Record<string, number>>({});
  const [editingPackage, setEditingPackage] = useState<Package | null>(null);
  const [packageSaving, setPackageSaving] = useState(false);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadServices = useCallback(async () => {
    const data = await getServices();
    setServices(data);
  }, []);

  const loadPackages = useCallback(async () => {
    setPackages(await getPackages());
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getServices(), getPackages()])
      .then(([user, data, packageData]) => {
        if (!active) return;
        setMe(user);
        setServices(data);
        setPackages(packageData);
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

  function cancelPackageEdit() {
    setEditingPackage(null);
    setPkgName("");
    setPkgDescription("");
    setPkgPrice("0.00");
    setPkgActive(true);
    setPkgItems({});
    setError(null);
  }

  function startPackageEdit(item: Package) {
    setEditingPackage(item);
    setPkgName(item.name);
    setPkgDescription(item.description ?? "");
    setPkgPrice(item.total_price);
    setPkgActive(item.is_active);
    setPkgItems(
      Object.fromEntries(
        item.items.map((entry) => [entry.service_id, entry.quantity]),
      ),
    );
    setError(null);
  }

  async function handleSavePackage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const items = Object.entries(pkgItems)
      .filter(([, quantity]) => quantity > 0)
      .map(([service_id, quantity]) => ({ service_id, quantity }));
    if (!editingPackage && items.length === 0) {
      setError("Selecione ao menos um serviço para o pacote.");
      return;
    }
    setPackageSaving(true);
    try {
      if (editingPackage) {
        await updatePackage(editingPackage.id, {
          name: pkgName.trim(),
          description: pkgDescription.trim() || null,
          total_price: pkgPrice,
          is_active: pkgActive,
        });
      } else {
        await createPackage({
          name: pkgName.trim(),
          description: pkgDescription.trim() || null,
          total_price: pkgPrice,
          items,
          is_active: pkgActive,
        });
      }
      cancelPackageEdit();
      await loadPackages();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar pacote.",
      );
    } finally {
      setPackageSaving(false);
    }
  }

  async function handleDeletePackage(item: Package) {
    if (!window.confirm(`Excluir o pacote ${item.name}?`)) return;
    setError(null);
    try {
      await deletePackage(item.id);
      if (editingPackage?.id === item.id) cancelPackageEdit();
      await loadPackages();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir pacote.",
      );
    }
  }

  async function togglePackageActive(item: Package) {
    setError(null);
    try {
      await updatePackage(item.id, { is_active: !item.is_active });
      await loadPackages();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar pacote.",
      );
    }
  }

  function composition(item: Package): string {
    return item.items
      .map((entry) => {
        const service = services.find(
          (candidate) => candidate.id === entry.service_id,
        );
        return `${service?.name ?? "Serviço"} ×${entry.quantity}`;
      })
      .join(" · ");
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

        <div className="admin-grid section-gap">
          <section className="panel">
            <div className="panel-title">
              <h2>Pacotes</h2>
              <span className="muted-small">
                {packages.length} cadastrado(s)
              </span>
            </div>
            {packages.length === 0 ? (
              <p className="table-empty">Nenhum pacote cadastrado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Pacote</th>
                      <th>Composição</th>
                      <th>Preço</th>
                      <th>Status</th>
                      {isManager ? <th /> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {packages.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <strong>{item.name}</strong>
                          {item.description ? (
                            <div className="muted-small">
                              {item.description}
                            </div>
                          ) : null}
                        </td>
                        <td>{composition(item)}</td>
                        <td className="price-cell">
                          {formatPrice(item.total_price)}
                        </td>
                        <td>
                          {item.is_active ? (
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
                                onClick={() => startPackageEdit(item)}
                              >
                                Editar
                              </button>
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => togglePackageActive(item)}
                              >
                                {item.is_active ? "Desativar" : "Ativar"}
                              </button>
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                onClick={() => handleDeletePackage(item)}
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
                <h2>
                  {editingPackage ? "Editar pacote" : "Novo pacote"}
                </h2>
                {editingPackage ? (
                  <button
                    className="button button-ghost button-small"
                    type="button"
                    onClick={cancelPackageEdit}
                  >
                    Cancelar edição
                  </button>
                ) : null}
              </div>
              <form onSubmit={handleSavePackage}>
                <div className="field">
                  <label htmlFor="package-name">Nome</label>
                  <input
                    id="package-name"
                    value={pkgName}
                    onChange={(event) => setPkgName(event.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="field">
                  <label htmlFor="package-description">Descrição</label>
                  <textarea
                    id="package-description"
                    value={pkgDescription}
                    onChange={(event) =>
                      setPkgDescription(event.target.value)
                    }
                    rows={2}
                    maxLength={2000}
                  />
                </div>
                <div className="field">
                  <label htmlFor="package-price">Preço total (R$)</label>
                  <input
                    id="package-price"
                    value={pkgPrice}
                    onChange={(event) => setPkgPrice(event.target.value)}
                    required
                  />
                </div>

                <div className="field">
                  <label>Serviços incluídos</label>
                  {services.length === 0 ? (
                    <p className="muted-small">
                      Cadastre um serviço antes de montar um pacote.
                    </p>
                  ) : (
                    <div className="package-items">
                      {services.map((service) => (
                        <label
                          className="package-item"
                          key={service.id}
                          htmlFor={`package-item-${service.id}`}
                        >
                          <span>
                            {service.name}
                            <small>
                              {" "}
                              · {formatPrice(service.price)}
                            </small>
                          </span>
                          <input
                            id={`package-item-${service.id}`}
                            type="number"
                            min={0}
                            max={100}
                            value={pkgItems[service.id] ?? 0}
                            onChange={(event) =>
                              setPkgItems((current) => ({
                                ...current,
                                [service.id]: Number(event.target.value),
                              }))
                            }
                          />
                        </label>
                      ))}
                    </div>
                  )}
                </div>

                <div className="checkbox-field">
                  <input
                    id="package-active"
                    type="checkbox"
                    checked={pkgActive}
                    onChange={(event) => setPkgActive(event.target.checked)}
                  />
                  <label htmlFor="package-active">Pacote ativo</label>
                </div>

                {editingPackage ? (
                  <p className="muted-small">
                    Para alterar a composição, cadastre um novo pacote.
                  </p>
                ) : null}

                <button
                  className="button"
                  type="submit"
                  disabled={packageSaving}
                >
                  {packageSaving
                    ? "Salvando…"
                    : editingPackage
                      ? "Salvar alterações"
                      : "Cadastrar pacote"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
