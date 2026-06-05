"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getVacancy } from "@/lib/api";
import type { Vacancy } from "@/lib/types";

export default function VacancyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const [vacancy, setVacancy] = useState<Vacancy | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getVacancy(id)
      .then(setVacancy)
      .catch((err) =>
        setError(err instanceof ApiError ? err.message : "Error al cargar la vacante."),
      )
      .finally(() => setLoading(false));
  }, [id]);

  return (
    <div className="space-y-6">
      <Link href="/vacancies" className="text-sm text-slate-500 hover:text-slate-900">
        ← Volver a vacantes
      </Link>

      {loading && <p className="text-sm text-slate-500">Cargando…</p>}

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      {vacancy && (
        <article className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-semibold text-slate-900">{vacancy.title}</h1>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {vacancy.status}
            </span>
          </div>

          {vacancy.description && (
            <p className="text-sm text-slate-600">{vacancy.description}</p>
          )}

          <dl className="grid gap-3 text-sm sm:grid-cols-2">
            <Detail label="Seniority" value={vacancy.seniority} />
            <Detail label="Modalidad" value={vacancy.modality} />
            <Detail label="País / zona" value={vacancy.country ?? "—"} />
            <Detail
              label="Rango salarial"
              value={
                vacancy.salary_min || vacancy.salary_max
                  ? `${vacancy.salary_min ?? "?"} – ${vacancy.salary_max ?? "?"}`
                  : "—"
              }
            />
            <Detail label="Skills obligatorias" value={vacancy.required_skills.join(", ") || "—"} />
            <Detail label="Skills deseables" value={vacancy.desired_skills.join(", ") || "—"} />
          </dl>
        </article>
      )}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-400">{label}</dt>
      <dd className="text-slate-800">{value}</dd>
    </div>
  );
}
