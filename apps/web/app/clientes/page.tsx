"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createClient,
  deleteClient,
  getClients,
  getMe,
  updateClient,
  type Client,
  type Me,
} from "@/lib/api";
import {
  birthDateToIso,
  formatBirthDate,
  formatPhone,
  formatState,
  formatZip,
  isoToBirthDate,
  isValidBirthDate,
} from "@/lib/masks";
import { supportsMedicalRecords } from "@/lib/profiles";

export default function ClientsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [zip, setZip] = useState("");
  const [street, setStreet] = useState("");
  const [addressNumber, setAddressNumber] = useState("");
  const [complement, setComplement] = useState("");
  const [neighborhood, setNeighborhood] = useState("");
  const [city, setCity] = useState("");
  const [state, setState] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<Client | null>(null);

  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadClients = useCallback(async () => {
    const data = await getClients();
    setClients(data);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getClients()])
      .then(([user, data]) => {
        if (!active) return;
        setMe(user);
        setClients(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar clientes.",
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

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return clients;
    return clients.filter(
      (client) =>
        client.full_name.toLowerCase().includes(term) ||
        client.phone.toLowerCase().includes(term),
    );
  }, [clients, search]);

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!isValidBirthDate(birthDate)) {
      setError("Data de nascimento inválida. Use dd/mm/aaaa.");
      return;
    }
    setSaving(true);
    const birthIso = birthDate.trim() ? birthDateToIso(birthDate) : null;
    const address = {
      address_zip: zip.trim() || null,
      address_street: street.trim() || null,
      address_number: addressNumber.trim() || null,
      address_complement: complement.trim() || null,
      address_neighborhood: neighborhood.trim() || null,
      address_city: city.trim() || null,
      address_state: state.trim() || null,
      notes: notes.trim() || null,
    };
    try {
      if (editing) {
        await updateClient(editing.id, {
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || null,
          birth_date: birthIso,
          ...address,
        });
      } else {
        await createClient({
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || undefined,
          birth_date: birthIso,
          ...address,
        });
      }
      cancelEdit();
      await loadClients();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar cliente.",
      );
    } finally {
      setSaving(false);
    }
  }

  function startEdit(client: Client) {
    setEditing(client);
    setFullName(client.full_name);
    setPhone(formatPhone(client.phone));
    setEmail(client.email ?? "");
    setBirthDate(isoToBirthDate(client.birth_date));
    setZip(client.address_zip ?? "");
    setStreet(client.address_street ?? "");
    setAddressNumber(client.address_number ?? "");
    setComplement(client.address_complement ?? "");
    setNeighborhood(client.address_neighborhood ?? "");
    setCity(client.address_city ?? "");
    setState(client.address_state ?? "");
    setNotes(client.notes ?? "");
    setError(null);
  }

  function cancelEdit() {
    setEditing(null);
    setFullName("");
    setPhone("");
    setEmail("");
    setBirthDate("");
    setZip("");
    setStreet("");
    setAddressNumber("");
    setComplement("");
    setNeighborhood("");
    setCity("");
    setState("");
    setNotes("");
  }

  async function handleDelete(client: Client) {
    if (!window.confirm(`Excluir o cliente ${client.full_name}?`)) return;
    setError(null);
    try {
      await deleteClient(client.id);
      if (editing?.id === client.id) cancelEdit();
      await loadClients();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir cliente.",
      );
    }
  }

  async function toggleBlock(client: Client) {
    setError(null);
    try {
      await updateClient(client.id, { is_blocked: !client.is_blocked });
      await loadClients();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar cliente.",
      );
    }
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Clientes</h1>
            <p>
              Cadastro, score confidencial e bloqueio de agendamento. Telefone
              mascarado para colaboradores.
            </p>
          </div>
          <div className="page-actions">
            <input
              className="admin-search"
              aria-label="Buscar cliente"
              placeholder="Buscar por nome ou telefone"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}

        <div className={`admin-grid ${isManager ? "" : "admin-grid-wide"}`}>
          <section className="panel">
            <div className="panel-title">
              <h2>Base de clientes</h2>
              <span className="muted-small">
                {filtered.length} de {clients.length}
              </span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : filtered.length === 0 ? (
              <p className="table-empty">Nenhum cliente encontrado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nome</th>
                      <th>Telefone</th>
                      <th>Score</th>
                      <th>Status</th>
                      <th />
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((client) => (
                      <tr key={client.id}>
                        <td>
                          <strong>{client.full_name}</strong>
                          {client.email ? (
                            <div className="muted-small">{client.email}</div>
                          ) : null}
                          {client.address_city ? (
                            <div className="muted-small">
                              {client.address_city}
                              {client.address_state
                                ? `/${client.address_state}`
                                : ""}
                            </div>
                          ) : null}
                        </td>
                        <td>{client.phone}</td>
                        <td>{client.score}</td>
                        <td>
                          {client.is_blocked ? (
                            <span className="pill pill-blocked">Bloqueado</span>
                          ) : (
                            <span className="pill pill-active">Ativo</span>
                          )}
                        </td>
                        <td>
                          <div className="row-actions">
                            {me &&
                            supportsMedicalRecords(me.business_profile) ? (
                              <Link
                                className="button button-ghost button-small"
                                href={`/clientes/${client.id}`}
                              >
                                Prontuário
                              </Link>
                            ) : null}
                            {isManager ? (
                              <>
                                <button
                                  className="button button-ghost button-small"
                                  type="button"
                                  onClick={() => startEdit(client)}
                                >
                                  Editar
                                </button>
                                <button
                                  className="button button-ghost button-small"
                                  type="button"
                                  onClick={() => toggleBlock(client)}
                                >
                                  {client.is_blocked
                                    ? "Desbloquear"
                                    : "Bloquear"}
                                </button>
                                <button
                                  className="button button-ghost button-small button-danger"
                                  type="button"
                                  onClick={() => handleDelete(client)}
                                >
                                  Excluir
                                </button>
                              </>
                            ) : null}
                          </div>
                        </td>
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
                <h2>{editing ? "Editar cliente" : "Novo cliente"}</h2>
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
                  <label htmlFor="client-name">Nome completo</label>
                  <input
                    id="client-name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="client-phone">Telefone</label>
                    <input
                      id="client-phone"
                      value={phone}
                      onChange={(event) =>
                        setPhone(formatPhone(event.target.value))
                      }
                      placeholder="(11) 91234-5678"
                      inputMode="tel"
                      required
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-email">E-mail (opcional)</label>
                    <input
                      id="client-email"
                      type="email"
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-birth">Data de nascimento</label>
                    <input
                      id="client-birth"
                      value={birthDate}
                      onChange={(event) =>
                        setBirthDate(formatBirthDate(event.target.value))
                      }
                      placeholder="dd/mm/aaaa"
                      inputMode="numeric"
                      maxLength={10}
                    />
                  </div>
                </div>

                <h3 className="form-section-title">Endereço</h3>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="client-zip">CEP</label>
                    <input
                      id="client-zip"
                      value={zip}
                      onChange={(event) => setZip(formatZip(event.target.value))}
                      placeholder="00000-000"
                      inputMode="numeric"
                      maxLength={9}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-street">Logradouro</label>
                    <input
                      id="client-street"
                      value={street}
                      onChange={(event) => setStreet(event.target.value)}
                      maxLength={255}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-number">Número</label>
                    <input
                      id="client-number"
                      value={addressNumber}
                      onChange={(event) => setAddressNumber(event.target.value)}
                      maxLength={20}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-complement">Complemento</label>
                    <input
                      id="client-complement"
                      value={complement}
                      onChange={(event) => setComplement(event.target.value)}
                      maxLength={120}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-neighborhood">Bairro</label>
                    <input
                      id="client-neighborhood"
                      value={neighborhood}
                      onChange={(event) => setNeighborhood(event.target.value)}
                      maxLength={120}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-city">Cidade</label>
                    <input
                      id="client-city"
                      value={city}
                      onChange={(event) => setCity(event.target.value)}
                      maxLength={120}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="client-state">UF</label>
                    <input
                      id="client-state"
                      value={state}
                      onChange={(event) =>
                        setState(formatState(event.target.value))
                      }
                      placeholder="SP"
                      maxLength={2}
                    />
                  </div>
                </div>

                <div className="field">
                  <label htmlFor="client-notes">Observações</label>
                  <textarea
                    id="client-notes"
                    value={notes}
                    onChange={(event) => setNotes(event.target.value)}
                    rows={3}
                    maxLength={5000}
                    placeholder="Preferências, alergias, informações importantes…"
                  />
                </div>

                <button className="button" type="submit" disabled={saving}>
                  {saving
                    ? "Salvando…"
                    : editing
                      ? "Salvar alterações"
                      : "Cadastrar cliente"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
