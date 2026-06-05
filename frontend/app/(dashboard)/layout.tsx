"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearTokens, getAccessToken, getMe } from "@/lib/api";
import type { User } from "@/lib/types";

export default function DashboardLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!getAccessToken()) {
      router.replace("/login");
      return;
    }
    getMe()
      .then((u) => {
        setUser(u);
        setChecked(true);
      })
      .catch(() => {
        clearTokens();
        router.replace("/login");
      });
  }, [router]);

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  if (!checked) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-slate-500">Cargando…</p>
      </main>
    );
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-3">
          <div className="flex items-center gap-6">
            <Link href="/vacancies" className="font-semibold text-slate-900">
              TalentTrust AI
            </Link>
            <nav className="flex gap-4 text-sm text-slate-600">
              <Link href="/vacancies" className="hover:text-slate-900">
                Vacantes
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-slate-500">
              {user?.email} · {user?.role}
            </span>
            <button
              onClick={logout}
              className="rounded-md border border-slate-300 px-3 py-1 text-slate-700 hover:bg-slate-50"
            >
              Salir
            </button>
          </div>
        </div>
      </header>

      <div className="bg-amber-50 text-amber-800">
        <p className="mx-auto max-w-5xl px-6 py-2 text-xs">
          La IA entrega recomendaciones no vinculantes; la decisión final es humana.
        </p>
      </div>

      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
