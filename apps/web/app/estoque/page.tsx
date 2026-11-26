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
import { formatAccessKey, formatTaxId, onlyDigits } from "@/lib/masks";
import { normalizeDecimal } from "@/lib/money";
import { formatPrice } from "@/lib/public";

const MOVEMENT_LABEL: Record<StockMovement["kind"], string> = {
  IN: "Entrada",
  OUT: "Saída",
  ADJUSTMENT: "Ajuste",
};

const DOCUMENT_LABEL: Record<
  NonNullable<StockMovement["document_type"]>,
  string
> = {
  NFE: "NF-e",
  RECEIPT: "Recibo",
  OTHER: "Outro",
};

const PAYMENT_LABEL: Record<
  NonNullable<StockMovement["payment_method"]>,
  string
> = {
  CASH: "Dinheiro",
  PIX: "Pix",
  CARD: "Cartão",
  TRANSFER: "Transferência",
  BOLETO: "Boleto",
  OTHER: "Outro",
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
  const [documentType, setDocumentType] = useState<
    NonNullable<StockMovement["document_type"]> | ""
  >("");
  const [documentNumber, setDocumentNumber] = useState("");
  const [documentSeries, setDocumentSeries] = useState("");
  const [supplierName, setSupplierName] = useState("");
  const [supplierTaxId, setSupplierTaxId] = useState("");
  const [issueDate, setIssueDate] = useState("");
  const [totalAmount, setTotalAmount] = useState("");
  const [paymentMethod, setPaymentMethod] = useState<
    NonNullable<StockMovement["payment_method"]> | ""
  >("");
  const [accessKey, setAccessKey] = useState("");
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
          min_quantity: normalizeDecimal(minQuantity),
          unit_cost: normalizeDecimal(unitCost),
          is_active: active,
        });
      } else {
        await createInventoryItem({
          name: name.trim(),
          unit: unit.trim(),
          quantity: normalizeDecimal(quantity),
          min_quantity: normalizeDecimal(minQuantity),
          unit_cost: normalizeDecimal(unitCost),
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

  function resetMovementDocument() {
    setDocumentType("");
    setDocumentNumber("");
    setDocumentSeries("");
    setSupplierName("");
    setSupplierTaxId("");
    setIssueDate("");
    setTotalAmount("");
    setPaymentMethod("");
    setAccessKey("");
  }

  async function startMovement(item: InventoryItem) {
    setEditing(null);
    setMovingItem(item);
    setMovementKind("IN");
    setMovementQuantity("1.000");
    setMovementReason("");
    resetMovementDocument();
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
        quantity: normalizeDecimal(movementQuantity),
        reason: movementReason.trim() || null,
        ...(movementKind === "IN"
          ? {
              document_type: documentType || null,
              document_number: documentNumber.trim() || null,
              document_series: documentSeries.trim() || null,
              supplier_name: supplierName.trim() || null,
              supplier_tax_id: supplierTaxId.trim() || null,
              issue_date: issueDate || null,
              total_amount: totalAmount.trim()
                ? normalizeDecimal(totalAmount)
                : null,
              payment_method: paymentMethod || null,
              access_key: onlyDigits(accessKey) || null,
            }
          : {}),
      });
      const refreshed = await getInventory();
      setItems(refreshed);
      const current = refreshed.find((item) => item.id === movingItem.id);
      if (current) setMovingItem(current);
      setMovements(await getStockMovements(movingItem.id));
      setMovementReason("");
      resetMovementDocument();
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
                    {movementKind === "IN" ? (
                      <div className="section-gap">
                        <div className="panel-title">
                          <h3>Nota fiscal / recibo</h3>
                        </div>
                        <p className="muted-small">
                          Preencha os dados do documento de compra para
                          rastrear a entrada.
                        </p>
                        <div className="form-grid">
                          <div className="field">
                            <label htmlFor="document-type">Documento</label>
                            <select
                              id="document-type"
                              value={documentType}
                              onChange={(event) =>
                                setDocumentType(
                                  event.target
                                    .value as NonNullable<
                                    StockMovement["document_type"]
                                  >,
                                )
                              }
                            >
                              <option value="">Sem documento</option>
                              <option value="NFE">NF-e</option>
                              <option value="RECEIPT">Recibo</option>
                              <option value="OTHER">Outro</option>
                            </select>
                          </div>
                          <div className="field">
                            <label htmlFor="document-number">Número</label>
                            <input
                              id="document-number"
                              value={documentNumber}
                              onChange={(event) =>
                                setDocumentNumber(event.target.value)
                              }
                              maxLength={60}
                              placeholder="000123"
                            />
                          </div>
                          <div className="field">
                            <label htmlFor="document-series">Série</label>
                            <input
                              id="document-series"
                              value={documentSeries}
                              onChange={(event) =>
                                setDocumentSeries(event.target.value)
                              }
                              maxLength={20}
                              placeholder="1"
                            />
                          </div>
                          <div className="field">
                            <label htmlFor="issue-date">Emissão</label>
                            <input
                              id="issue-date"
                              type="date"
                              value={issueDate}
                              onChange={(event) =>
                                setIssueDate(event.target.value)
                              }
                            />
                          </div>
                          <div className="field">
                            <label htmlFor="supplier-name">Fornecedor</label>
                            <input
                              id="supplier-name"
                              value={supplierName}
                              onChange={(event) =>
                                setSupplierName(event.target.value)
                              }
                              maxLength={255}
                            />
                          </div>
                          <div className="field">
                            <label htmlFor="supplier-tax-id">CNPJ/CPF</label>
                            <input
                              id="supplier-tax-id"
                              value={supplierTaxId}
                              onChange={(event) =>
                                setSupplierTaxId(formatTaxId(event.target.value))
                              }
                              maxLength={18}
                              inputMode="numeric"
                              placeholder="00.000.000/0000-00"
                            />
                          </div>
                          <div className="field">
                            <label htmlFor="total-amount">
                              Valor total (R$)
                            </label>
                            <input
                              id="total-amount"
                              inputMode="decimal"
                              value={totalAmount}
                              onChange={(event) =>
                                setTotalAmount(event.target.value)
                              }
                              placeholder="0,00"
                            />
                            <span className="muted-small">
                              Aceita vírgula ou ponto; será convertido para
                              decimal.
                            </span>
                          </div>
                          <div className="field">
                            <label htmlFor="payment-method">Pagamento</label>
                            <select
                              id="payment-method"
                              value={paymentMethod}
                              onChange={(event) =>
                                setPaymentMethod(
                                  event.target
                                    .value as NonNullable<
                                    StockMovement["payment_method"]
                                  >,
                                )
                              }
                            >
                              <option value="">Não informado</option>
                              <option value="CASH">Dinheiro</option>
                              <option value="PIX">Pix</option>
                              <option value="CARD">Cartão</option>
                              <option value="TRANSFER">Transferência</option>
                              <option value="BOLETO">Boleto</option>
                              <option value="OTHER">Outro</option>
                            </select>
                          </div>
                        </div>
                        <div className="field">
                          <label htmlFor="access-key">
                            Chave de acesso (NF-e)
                          </label>
                          <input
                            id="access-key"
                            inputMode="numeric"
                            value={accessKey}
                            onChange={(event) =>
                              setAccessKey(event.target.value)
                            }
                            maxLength={44}
                            placeholder="44 dígitos"
                          />
                        </div>
                      </div>
                    ) : null}
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
                            <th>Documento</th>
                            <th>Fornecedor</th>
                            <th>Valor</th>
                            <th>Motivo</th>
                            <th>Data</th>
                          </tr>
                        </thead>
                        <tbody>
                          {movements.map((movement) => (
                            <tr key={movement.id}>
                              <td>{MOVEMENT_LABEL[movement.kind]}</td>
                              <td>{movement.quantity}</td>
                              <td>
                                {movement.document_type
                                  ? `${DOCUMENT_LABEL[movement.document_type]}${
                                      movement.document_number
                                        ? ` ${movement.document_number}`
                                        : ""
                                    }`
                                  : "—"}
                                {movement.payment_method
                                  ? ` · ${PAYMENT_LABEL[movement.payment_method]}`
                                  : ""}
                              </td>
                              <td>{movement.supplier_name ?? "—"}</td>
                              <td>
                                {movement.total_amount
                                  ? formatPrice(movement.total_amount)
                                  : "—"}
                              </td>
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
                  ) : (
                    <p className="muted-small">
                      Para registrar nota fiscal ou recibo de compra, cadastre
                      o insumo e use “Movimentar → Entrada (compra)”.
                    </p>
                  )}
                </form>
              )}
            </section>
          </div>
        )}
      </div>
    </AppShell>
  );
}
