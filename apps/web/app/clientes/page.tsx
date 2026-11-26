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

export default function ClientsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [clients, setClients] = useState<Client[]>([]);
  const [search, setSearch] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
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
    setSaving(true);
    try {
      if (editing) {
        await updateClient(editing.id, {
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || null,
        });
      } else {
        await createClient({
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim() || undefined,
        });
      }
      setEditing(null);
      setFullName("");
      setPhone("");
      setEmail("");
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
    setPhone(client.phone);
    setEmail(client.email ?? "");
    setError(null);
  }

  function cancelEdit() {
    setEditing(null);
    setFullName("");
    setPhone("");
    setEmail("");
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
                            <Link
                              className="button button-ghost button-small"
                              href={`/clientes/${client.id}`}
                            >
                              Prontuário
                            </Link>
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
                <div className="field">
                  <label htmlFor="client-phone">Telefone</label>
                  <input
                    id="client-phone"
                    value={phone}
                    onChange={(event) => setPhone(event.target.value)}
                    placeholder="(11) 91234-5678"
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
