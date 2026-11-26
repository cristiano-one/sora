"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createPackage,
  deletePackage,
  getMe,
  getPackages,
  getServices,
  updatePackage,
  type Me,
  type Package,
  type Service,
} from "@/lib/api";
import { formatPrice } from "@/lib/public";

export default function PackagesPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [services, setServices] = useState<Service[]>([]);
  const [packages, setPackages] = useState<Package[]>([]);
  const [pkgName, setPkgName] = useState("");
  const [pkgDescription, setPkgDescription] = useState("");
  const [pkgPrice, setPkgPrice] = useState("0.00");
  const [pkgActive, setPkgActive] = useState(true);
  const [pkgItems, setPkgItems] = useState<Record<string, number>>({});
  const [editingPackage, setEditingPackage] = useState<Package | null>(null);
  const [loading, setLoading] = useState(true);
  const [packageSaving, setPackageSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadPackages = useCallback(async () => {
    setPackages(await getPackages());
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getPackages(), getServices()])
      .then(([user, packageData, serviceData]) => {
        if (!active) return;
        setMe(user);
        setPackages(packageData);
        setServices(serviceData);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar pacotes.",
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
            <h1>Pacotes</h1>
            <p>
              Combine serviços em pacotes, defina o preço fechado e controle a
              disponibilidade no link público.
            </p>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}

        <div className={`admin-grid ${isManager ? "" : "admin-grid-wide"}`}>
          <section className="panel">
            <div className="panel-title">
              <h2>Pacotes cadastrados</h2>
              <span className="muted-small">
                {packages.length} cadastrado(s)
              </span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : packages.length === 0 ? (
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
