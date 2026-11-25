"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getAccessToken } from "@/lib/tokens";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    router.replace(getAccessToken() ? "/dashboard" : "/login");
  }, [router]);

  return (
    <main className="shell">
      <div className="card">
        <p className="subtitle">Carregando…</p>
      </div>
    </main>
  );
}
