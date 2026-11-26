"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

import {
  getMe,
  getTenantSettings,
  logout,
  type Me,
} from "@/lib/api";

const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono / Gestor",
  ADMIN: "Administrador",
  COLLABORATOR: "Colaborador",
};

const SECTIONS = [
  {
    label: "Visão geral",
    items: [{ href: "/dashboard", label: "Painel", icon: "◫", manager: false }],
  },
  {
    label: "Operação",
    items: [
      { href: "/agenda", label: "Agenda", icon: "▤", manager: false },
      { href: "/clientes", label: "Clientes", icon: "◎", manager: false },
      {
        href: "/minha-comissao",
        label: "Minha comissão",
        icon: "％",
        manager: false,
      },
      { href: "/comandas", label: "Comandas", icon: "▣", manager: true },
      { href: "/pagamentos", label: "Sinais Pix", icon: "◈", manager: true },
    ],
  },
  {
    label: "Gestão",
    items: [
      {
        href: "/catalogo",
        label: "Catálogo",
        icon: "◇",
        manager: true,
        children: [
          { href: "/catalogo/servicos", label: "Serviços" },
          { href: "/catalogo/pacotes", label: "Pacotes" },
        ],
      },
      { href: "/estoque", label: "Estoque", icon: "▦", manager: true },
      { href: "/equipe", label: "Equipe", icon: "◈", manager: true },
      {
        href: "/assinaturas",
        label: "Assinaturas",
        icon: "☆",
        manager: true,
        children: [
          { href: "/assinaturas/assinantes", label: "Assinantes" },
          { href: "/assinaturas/planos", label: "Planos" },
          { href: "/assinaturas/contratar", label: "Contratar para cliente" },
          { href: "/assinaturas/novo-plano", label: "Novo plano" },
        ],
      },
      {
        href: "/financeiro",
        label: "Financeiro",
        icon: "◭",
        manager: true,
        ownerOnly: true,
        children: [
          { href: "/financeiro/fluxo-caixa", label: "Fluxo de caixa" },
          { href: "/financeiro/dre", label: "DRE" },
          { href: "/financeiro/lancamentos", label: "Lançamentos" },
          { href: "/financeiro/contas", label: "Contas e caixa" },
          { href: "/financeiro/comissoes", label: "Comissões" },
          { href: "/financeiro/folha", label: "Folha & pró-labore" },
          {
            href: "/financeiro/dizimo",
            label: "Dízimo & oferta",
            titheOnly: true,
          },
          { href: "/financeiro/vendas", label: "Vendas" },
        ],
      },
      { href: "/sora-ia", label: "SORA IA", icon: "✦", manager: true },
      {
        href: "/configuracoes",
        label: "Configurações",
        icon: "⚙",
        manager: true,
        children: [
          { href: "/configuracoes/aparencia", label: "Aparência" },
          { href: "/configuracoes/agenda", label: "Agenda & score" },
          { href: "/configuracoes/agente", label: "Agente SORA IA" },
          { href: "/configuracoes/whatsapp", label: "WhatsApp" },
          { href: "/configuracoes/financeiro", label: "Financeiro" },
          { href: "/configuracoes/automacoes", label: "Automações" },
          { href: "/configuracoes/dados", label: "Dados & LGPD" },
        ],
      },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [theme, setTheme] = useState("#4f46e5");
  const [titheEnabled, setTitheEnabled] = useState(false);
  const [openMenus, setOpenMenus] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let active = true;
    getMe()
      .then((data) => {
        if (!active) return;
        setMe(data);
        if (data.role === "OWNER" || data.role === "ADMIN") {
          getTenantSettings()
            .then((settings) => {
              if (active) {
                setTheme(settings.theme_primary_color);
                setTitheEnabled(settings.enable_tithe_and_offering);
              }
            })
            .catch(() => {
              // Tema é opcional; mantém o padrão.
            });
        }
      })
      .catch(() => {
        if (active) router.replace("/login");
      });
    return () => {
      active = false;
    };
  }, [router]);

  useEffect(() => {
    function handleTheme(event: Event) {
      const color = (event as CustomEvent<string>).detail;
      if (color) setTheme(color);
    }
    window.addEventListener("sora-theme", handleTheme);
    return () => window.removeEventListener("sora-theme", handleTheme);
  }, []);

  async function handleLogout() {
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }

  if (!me) {
    return (
      <main className="shell">
        <div className="card">
          <p className="subtitle">Carregando painel…</p>
        </div>
      </main>
    );
  }

  const isManager = me.role === "OWNER" || me.role === "ADMIN";
  const isOwner = me.role === "OWNER";
  const style = { "--primary": theme } as CSSProperties;

  return (
    <div className="app-shell" style={style}>
      <aside className="sidebar">
        <Link className="sidebar-brand" href="/dashboard">
          <span className="brand-mark">S</span>
          <span>
            <strong>Sora Studio</strong>
            <small>Gestão inteligente</small>
          </span>
        </Link>

        <nav className="sidebar-nav">
          {SECTIONS.map((section) => {
            const items = section.items.filter(
              (item) =>
                (!item.manager || isManager) &&
                (!("ownerOnly" in item) || !item.ownerOnly || isOwner),
            );
            if (items.length === 0) return null;
            return (
              <div className="sidebar-section" key={section.label}>
                <span className="sidebar-label">{section.label}</span>
                {items.map((item) => {
                  const children = "children" in item ? item.children : null;
                  if (children) {
                    const isOpen =
                      openMenus[item.href] ??
                      pathname.startsWith(`${item.href}/`);
                    return (
                      <div className="sidebar-group" key={item.href}>
                        <button
                          className={`sidebar-link sidebar-link-button ${
                            pathname.startsWith(item.href) ? "active" : ""
                          }`}
                          type="button"
                          onClick={() =>
                            setOpenMenus((current) => ({
                              ...current,
                              [item.href]: !isOpen,
                            }))
                          }
                        >
                          <span className="sidebar-icon">{item.icon}</span>
                          {item.label}
                          <span
                            className={`sidebar-chevron ${
                              isOpen ? "open" : ""
                            }`}
                          >
                            ⌄
                          </span>
                        </button>
                        {isOpen ? (
                          <div className="sidebar-submenu">
                            {children
                              .filter(
                                (child) =>
                                  !("titheOnly" in child) ||
                                  !child.titheOnly ||
                                  titheEnabled,
                              )
                              .map((child) => (
                                <Link
                                  key={child.href}
                                  className={`sidebar-sublink ${
                                    pathname === child.href ? "active" : ""
                                  }`}
                                  href={child.href}
                                >
                                  {child.label}
                                </Link>
                              ))}
                          </div>
                        ) : null}
                      </div>
                    );
                  }
                  return (
                    <Link
                      key={item.href}
                      className={`sidebar-link ${
                        pathname === item.href ? "active" : ""
                      }`}
                      href={item.href}
                    >
                      <span className="sidebar-icon">{item.icon}</span>
                      {item.label}
                    </Link>
                  );
                })}
              </div>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="sidebar-user">
            <strong>{me.full_name}</strong>
            <span>{ROLE_LABEL[me.role] ?? me.role}</span>
          </div>
          <button
            className="sidebar-logout"
            type="button"
            onClick={handleLogout}
          >
            Sair
          </button>
        </div>
      </aside>

      <main className="app-main">{children}</main>
    </div>
  );
}
