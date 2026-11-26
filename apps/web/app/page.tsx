"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getAccessToken } from "@/lib/tokens";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    // A plataforma também é o site de vendas: visitante novo entra pelo
    // cadastro/onboarding; usuário autenticado vai direto ao painel.
    router.replace(getAccessToken() ? "/dashboard" : "/cadastro");
  }, [router]);

  return (
    <main className="shell">
      <div className="card">
        <p className="subtitle">Carregando…</p>
      </div>
    </main>
  );
}
