"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { AppShell } from "@/components/app-shell";
import {
  ApiError,
  createUser,
  deleteUser,
  getMe,
  getUsers,
  updateUser,
  type Me,
  type UserSummary,
} from "@/lib/api";
import { formatPrice } from "@/lib/public";

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

function commissionLabel(user: UserSummary): string {
  const parts: string[] = [];
  if (user.commission_percentage) {
    parts.push(`${user.commission_percentage}%`);
  }
  if (user.commission_fixed) {
    parts.push(`fixo ${formatPrice(user.commission_fixed)}`);
  }
  if (parts.length === 0) return "—";
  return `${parts.join(" + ")} · ${user.commission_base}`;
}

export default function TeamPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [users, setUsers] = useState<UserSummary[]>([]);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"ADMIN" | "COLLABORATOR">("COLLABORATOR");
  const [commissionPercentage, setCommissionPercentage] = useState("40.00");
  const [commissionFixed, setCommissionFixed] = useState("0.00");
  const [commissionBase, setCommissionBase] = useState<"GROSS" | "NET">(
    "GROSS",
  );
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<UserSummary | null>(null);

  const isOwner = me?.role === "OWNER";
  const isManager = me?.role === "OWNER" || me?.role === "ADMIN";

  const loadUsers = useCallback(async () => {
    const data = await getUsers();
    setUsers(data);
  }, []);

  useEffect(() => {
    let active = true;
    Promise.all([getMe(), getUsers()])
      .then(([user, data]) => {
        if (!active) return;
        setMe(user);
        setUsers(data);
      })
      .catch((err) => {
        if (active) {
          setError(
            err instanceof ApiError ? err.message : "Falha ao carregar equipe.",
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
    try {
      if (editing) {
        await updateUser(editing.id, {
          full_name: fullName.trim(),
          role,
          commission_percentage:
            commissionPercentage.trim() === "" ? null : commissionPercentage,
          commission_fixed:
            commissionFixed.trim() === "" ? null : commissionFixed,
          commission_base: commissionBase,
        });
      } else {
        await createUser({
          full_name: fullName.trim(),
          email: email.trim(),
          password,
          role,
          commission_percentage:
            commissionPercentage.trim() === "" ? null : commissionPercentage,
          commission_fixed:
            commissionFixed.trim() === "" ? null : commissionFixed,
          commission_base: commissionBase,
        });
      }
      cancelEdit();
      await loadUsers();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao salvar usuário.",
      );
    } finally {
      setSaving(false);
    }
  }

  function startEdit(user: UserSummary) {
    setEditing(user);
    setFullName(user.full_name);
    setEmail(user.email);
    setPassword("");
    setRole(user.role === "ADMIN" ? "ADMIN" : "COLLABORATOR");
    setCommissionPercentage(user.commission_percentage ?? "");
    setCommissionFixed(user.commission_fixed ?? "");
    setCommissionBase(user.commission_base === "NET" ? "NET" : "GROSS");
    setError(null);
  }

  function cancelEdit() {
    setEditing(null);
    setFullName("");
    setEmail("");
    setPassword("");
    setRole("COLLABORATOR");
    setCommissionPercentage("40.00");
    setCommissionFixed("0.00");
    setCommissionBase("GROSS");
  }

  async function handleDelete(user: UserSummary) {
    if (!window.confirm(`Excluir o usuário ${user.full_name}?`)) return;
    setError(null);
    try {
      await deleteUser(user.id);
      if (editing?.id === user.id) cancelEdit();
      await loadUsers();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao excluir usuário.",
      );
    }
  }

  async function toggleActive(user: UserSummary) {
    setError(null);
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      await loadUsers();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao atualizar usuário.",
      );
    }
  }

  return (
    <AppShell>
      <div className="page">
        <header className="page-header">
          <div>
            <h1>Equipe</h1>
            <p>
              Colaboradores, administradores e regras de comissão. O dono não
              pode ser rebaixado.
            </p>
          </div>
        </header>

        {error ? <p className="error">{error}</p> : null}

        <div className="admin-grid">
          <section className="panel">
            <div className="panel-title">
              <h2>Usuários</h2>
              <span className="muted-small">{users.length} cadastrados</span>
            </div>
            {loading ? (
              <p className="table-empty">Carregando…</p>
            ) : users.length === 0 ? (
              <p className="table-empty">Nenhum usuário encontrado.</p>
            ) : (
              <div className="table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Nome</th>
                      <th>Papel</th>
                      <th>Comissão</th>
                      <th>Status</th>
                      {isManager ? <th /> : null}
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id}>
                        <td>
                          <strong>{user.full_name}</strong>
                          <div className="muted-small">{user.email}</div>
                        </td>
                        <td>
                          <span className="pill pill-manager">
                            {ROLE_LABEL[user.role] ?? user.role}
                          </span>
                        </td>
                        <td className="muted-small">
                          {commissionLabel(user)}
                        </td>
                        <td>
                          {user.is_active ? (
                            <span className="pill pill-active">Ativo</span>
                          ) : (
                            <span className="pill">Inativo</span>
                          )}
                        </td>
                        {isManager && user.role !== "OWNER" ? (
                          <td>
                            <div className="row-actions">
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => startEdit(user)}
                              >
                                Editar
                              </button>
                              <button
                                className="button button-ghost button-small"
                                type="button"
                                onClick={() => toggleActive(user)}
                              >
                                {user.is_active ? "Desativar" : "Ativar"}
                              </button>
                              {(isOwner || user.role === "COLLABORATOR") &&
                              user.id !== me?.id ? (
                                <button
                                  className="button button-ghost button-small button-danger"
                                  type="button"
                                  onClick={() => handleDelete(user)}
                                >
                                  Excluir
                                </button>
                              ) : null}
                            </div>
                          </td>
                        ) : (
                          <td />
                        )}
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
                <h2>{editing ? "Editar usuário" : "Novo usuário"}</h2>
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
                  <label htmlFor="user-name">Nome completo</label>
                  <input
                    id="user-name"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    required
                    maxLength={255}
                  />
                </div>
                <div className="field">
                  <label htmlFor="user-email">E-mail</label>
                  <input
                    id="user-email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    disabled={Boolean(editing)}
                    required
                  />
                </div>
                {!editing ? (
                  <div className="field">
                    <label htmlFor="user-password">Senha inicial</label>
                    <input
                      id="user-password"
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      minLength={8}
                      required
                    />
                  </div>
                ) : null}
                <div className="field">
                  <label htmlFor="user-role">Papel</label>
                  <select
                    id="user-role"
                    value={role}
                    onChange={(event) =>
                      setRole(event.target.value as "ADMIN" | "COLLABORATOR")
                    }
                  >
                    {isOwner ? <option value="ADMIN">Administrador</option> : null}
                    <option value="COLLABORATOR">Colaborador</option>
                  </select>
                </div>
                <div className="form-grid">
                  <div className="field">
                    <label htmlFor="commission-percentage">Comissão %</label>
                    <input
                      id="commission-percentage"
                      value={commissionPercentage}
                      onChange={(event) =>
                        setCommissionPercentage(event.target.value)
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="commission-fixed">Comissão fixa</label>
                    <input
                      id="commission-fixed"
                      value={commissionFixed}
                      onChange={(event) =>
                        setCommissionFixed(event.target.value)
                      }
                    />
                  </div>
                </div>
                <div className="field">
                  <label htmlFor="commission-base">Base da comissão</label>
                  <select
                    id="commission-base"
                    value={commissionBase}
                    onChange={(event) =>
                      setCommissionBase(event.target.value as "GROSS" | "NET")
                    }
                  >
                    <option value="GROSS">Bruto</option>
                    <option value="NET">Líquido</option>
                  </select>
                </div>
                <button className="button" type="submit" disabled={saving}>
                  {saving
                    ? "Salvando…"
                    : editing
                      ? "Salvar alterações"
                      : "Cadastrar usuário"}
                </button>
              </form>
            </section>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
}
