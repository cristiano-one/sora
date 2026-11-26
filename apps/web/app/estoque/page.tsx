"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  addStockMovement,
  ApiError,
  createInventoryItem,
  deleteInventoryItem,
  getInventory,
  getMe,
  getStockMovements,
  updateInventoryItem,
  type InventoryItem,
  type Me,
  type StockMovement,
} from "@/lib/api";
import { formatIsoDate } from "@/lib/agenda";
import { formatPrice } from "@/lib/public";

const MOVEMENT_LABEL: Record<StockMovement["kind"], string> = {
  IN: "Entrada",
  OUT: "Saída",
  ADJUSTMENT: "Ajuste",
};

export default function InventoryPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [unit, setUnit] = useState("un");
  const [quantity, setQuantity] = useState("0.000");
  const [minQuantity, setMinQuantity] = useState("0.000");
  const [unitCost, setUnitCost] = useState("0.00");
  const [active, setActive] = useState(true);
  const [editing, setEditing] = useState<InventoryItem | null>(null);

  const [movingItem, setMovingItem] = useState<InventoryItem | null>(null);
  const [movementKind, setMovementKind] =
    useState<StockMovement["kind"]>("IN");
  const [movementQuantity, setMovementQuantity] = useState("1.000");
  const [movementReason, setMovementReason] = useState("");
  const [movements, setMovements] = useState<StockMovement[]>([]);

  const load = useCallback(async () => {
    setItems(await getInventory());
  }, []);

  useEffect(() => {
    let activeRequest = true;
    Promise.all([getMe(), getInventory()])
      .then(([user, data]) => {
        if (!activeRequest) return;
        setMe(user);
        setItems(data);
      })
      .catch((err) => {
        if (!activeRequest) return;
        setError(
          err instanceof ApiError ? err.message : "Falha ao carregar estoque.",
        );
      })
      .finally(() => {
        if (activeRequest) setLoading(false);
      });
    return () => {
      activeRequest = false;
    };
  }, []);

  function resetItemForm() {
    setEditing(null);
    setName("");
    setUnit("un");
    setQuantity("0.000");
    setMinQuantity("0.000");
    setUnitCost("0.00");
    setActive(true);
  }

  function startEdit(item: InventoryItem) {
    setMovingItem(null);
    setEditing(item);
    setName(item.name);
    setUnit(item.unit);
    setQuantity(item.quantity);
    setMinQuantity(item.min_quantity);
    setUnitCost(item.unit_cost);
    setActive(item.is_active);
    setError(null);
  }

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      if (editing) {
        await updateInventoryItem(editing.id, {
          name: name.trim(),
          unit: unit.trim(),
          min_quantity: minQuantity,
          unit_cost: unitCost,
          is_active: active,
        });
      } else {
        await createInventoryItem({
          name: name.trim(),
          unit: unit.trim(),
          quantity,
          min_quantity: minQuantity,
          unit_cost: unitCost,
          is_active: active,
        });
      }
      resetItemForm();
      await load();
      setNotice(editing ? "Insumo atualizado." : "Insumo cadastrado.");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar insumo.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(item: InventoryItem) {
    if (!window.confirm(`Excluir o insumo ${item.name}?`)) return;
    setError(null);
    try {
      await deleteInventoryItem(item.id);
      if (editing?.id === item.id) resetItemForm();
      if (movingItem?.id === item.id) setMovingItem(null);
      await load();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir insumo.",
      );
    }
  }

  async function startMovement(item: InventoryItem) {
    setEditing(null);
    setMovingItem(item);
    setMovementKind("IN");
    setMovementQuantity("1.000");
    setMovementReason("");
    setError(null);
    setNotice(null);
    try {
      setMovements(await getStockMovements(item.id));
    } catch {
      setMovements([]);
    }
  }

  async function handleMovement(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!movingItem) return;
    setError(null);
    setNotice(null);
    setSaving(true);
    try {
      await addStockMovement(movingItem.id, {
        kind: movementKind,
        quantity: movementQuantity,
        reason: movementReason.trim() || null,
      });
      const refreshed = await getInventory();
      setItems(refreshed);
      const current = refreshed.find((item) => item.id === movingItem.id);
      if (current) setMovingItem(current);
      setMovements(await getStockMovements(movingItem.id));
      setMovementReason("");
      setNotice("Movimentação registrada.");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Falha ao movimentar estoque.",
      );
    } finally {
      setSaving(false);
    }
  }

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";
  const lowStockCount = items.filter((item) => item.low_stock).length;

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Estoque &amp; insumos</h1>
            <p>
              Saldo, custo médio, mínimo de reposição e movimentações dos
              insumos da clínica.
            </p>
          </div>
          {lowStockCount > 0 ? (
            <span className="pill pill-blocked">
              {lowStockCount} abaixo do mínimo
            </span>
          ) : null}
        </header>

        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="public-notice">{notice}</p> : null}

        {me && !isManager ? (
          <p className="error">Acesso restrito a gestores e administradores.</p>
        ) : (
          <div className="admin-grid">
            <section className="panel">
              <div className="panel-title">
                <h2>Insumos</h2>
                <span className="muted-small">{items.length}</span>
              </div>
              {loading ? (
                <p className="table-empty">Carregando…</p>
              ) : items.length === 0 ? (
                <p className="table-empty">Nenhum insumo cadastrado.</p>
              ) : (
                <div className="table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Insumo</th>
                        <th>Saldo</th>
                        <th>Mínimo</th>
                        <th>Custo</th>
                        <th>Total</th>
                        <th>Status</th>
                        <th />
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <tr key={item.id}>
                          <td>
                            <strong>{item.name}</strong>
                            <div className="muted-small">{item.unit}</div>
                          </td>
                          <td className="price-cell">
                            {item.quantity} {item.unit}
                          </td>
                          <td>
                            {item.min_quantity} {item.unit}
                          </td>
                          <td className="price-cell">
                            {formatPrice(item.unit_cost)}
                          </td>
                          <td className="price-cell">
                            {formatPrice(item.total_value)}
                          </td>
                          <td>
                            {item.low_stock ? (
                              <span className="pill pill-blocked">
                                Repor
                              </span>
                            ) : !item.is_active ? (
                              <span className="pill">Inativo</span>
                            ) : (
                              <span className="pill pill-active">OK</span>
                            )}
                          </td>
                          <td>
                            <div className="row-actions">
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => startMovement(item)}
                              >
                                Movimentar
                              </button>
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => startEdit(item)}
                              >
                                Editar
                              </button>
                              <button
                                className="button button-ghost button-small button-danger"
                                type="button"
                                onClick={() => handleDelete(item)}
                              >
                                Excluir
                              </button>
                            </div>
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
                <h2>
                  {movingItem
                    ? `Movimentar ${movingItem.name}`
                    : editing
                      ? "Editar insumo"
                      : "Novo insumo"}
                </h2>
                {movingItem || editing ? (
                  <button
                    className="button button-ghost button-small"
                    type="button"
                    onClick={() => {
                      setMovingItem(null);
                      resetItemForm();
                    }}
                  >
                    Voltar
                  </button>
                ) : null}
              </div>

              {movingItem ? (
                <>
                  <p className="muted-small">
                    Saldo atual: {movingItem.quantity} {movingItem.unit}
                  </p>
                  <form onSubmit={handleMovement}>
                    <div className="field">
                      <label htmlFor="movement-kind">Tipo</label>
                      <select
                        id="movement-kind"
                        value={movementKind}
                        onChange={(event) =>
                          setMovementKind(
                            event.target.value as StockMovement["kind"],
                          )
                        }
                      >
                        <option value="IN">Entrada (compra)</option>
                        <option value="OUT">Saída (consumo)</option>
                        <option value="ADJUSTMENT">
                          Ajuste (contagem absoluta)
                        </option>
                      </select>
                    </div>
                    <div className="field">
                      <label htmlFor="movement-quantity">Quantidade</label>
                      <input
                        id="movement-quantity"
                        inputMode="decimal"
                        value={movementQuantity}
                        onChange={(event) =>
                          setMovementQuantity(event.target.value)
                        }
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="movement-reason">Motivo</label>
                      <input
                        id="movement-reason"
                        value={movementReason}
                        onChange={(event) =>
                          setMovementReason(event.target.value)
                        }
                        maxLength={500}
                        placeholder="Compra, uso em atendimento, contagem…"
                      />
                    </div>
                    <button className="button" type="submit" disabled={saving}>
                      {saving ? "Registrando…" : "Registrar movimentação"}
                    </button>
                  </form>

                  <div className="panel-title section-gap">
                    <h3>Últimas movimentações</h3>
                  </div>
                  {movements.length === 0 ? (
                    <p className="table-empty">Sem movimentações.</p>
                  ) : (
                    <div className="table-wrap">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Tipo</th>
                            <th>Qtd.</th>
                            <th>Motivo</th>
                            <th>Data</th>
                          </tr>
                        </thead>
                        <tbody>
                          {movements.map((movement) => (
                            <tr key={movement.id}>
                              <td>{MOVEMENT_LABEL[movement.kind]}</td>
                              <td>{movement.quantity}</td>
                              <td>{movement.reason ?? "—"}</td>
                              <td>{formatIsoDate(movement.created_at)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <form onSubmit={handleSave}>
                  <div className="field">
                    <label htmlFor="item-name">Nome</label>
                    <input
                      id="item-name"
                      value={name}
                      onChange={(event) => setName(event.target.value)}
                      required
                      maxLength={255}
                    />
                  </div>
                  <div className="form-grid">
                    <div className="field">
                      <label htmlFor="item-unit">Unidade</label>
                      <input
                        id="item-unit"
                        value={unit}
                        onChange={(event) => setUnit(event.target.value)}
                        required
                        maxLength={20}
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="item-quantity">Saldo inicial</label>
                      <input
                        id="item-quantity"
                        inputMode="decimal"
                        value={quantity}
                        onChange={(event) => setQuantity(event.target.value)}
                        disabled={Boolean(editing)}
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="item-min">Estoque mínimo</label>
                      <input
                        id="item-min"
                        inputMode="decimal"
                        value={minQuantity}
                        onChange={(event) =>
                          setMinQuantity(event.target.value)
                        }
                        required
                      />
                    </div>
                    <div className="field">
                      <label htmlFor="item-cost">Custo unitário (R$)</label>
                      <input
                        id="item-cost"
                        inputMode="decimal"
                        value={unitCost}
                        onChange={(event) => setUnitCost(event.target.value)}
                        required
                      />
                    </div>
                  </div>
                  <div className="checkbox-field">
                    <input
                      id="item-active"
                      type="checkbox"
                      checked={active}
                      onChange={(event) => setActive(event.target.checked)}
                    />
                    <label htmlFor="item-active">Insumo ativo</label>
                  </div>
                  <button className="button" type="submit" disabled={saving}>
                    {saving
                      ? "Salvando…"
                      : editing
                        ? "Salvar alterações"
                        : "Cadastrar insumo"}
                  </button>
                  {editing ? (
                    <p className="muted-small">
                      O saldo só muda por movimentação de estoque.
                    </p>
                  ) : null}
                </form>
              )}
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
