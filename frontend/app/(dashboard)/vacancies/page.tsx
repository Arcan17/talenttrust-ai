"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ApiError, createVacancy, listVacancies } from "@/lib/api";
import type { Modality, Seniority, Vacancy } from "@/lib/types";

const MODALITIES: Modality[] = ["remote", "hybrid", "onsite"];
const SENIORITIES: Seniority[] = ["junior", "mid", "senior"];

export default function VacanciesPage() {
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setVacancies(await listVacancies());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar vacantes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-xl font-semibold text-slate-900">Vacantes</h1>
        <p className="text-sm text-slate-500">
          Crea una vacante y consulta las de tu organización.
        </p>
      </div>

      <CreateVacancyForm onCreated={load} />

      <section>
        {loading && <p className="text-sm text-slate-500">Cargando vacantes…</p>}

        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {!loading && !error && vacancies.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-300 p-8 text-center">
            <p className="text-sm text-slate-500">
              Aún no hay vacantes. Crea la primera con el formulario de arriba.
            </p>
          </div>
        )}

        {!loading && vacancies.length > 0 && (
          <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
            {vacancies.map((v) => (
              <li key={v.id} className="flex items-center justify-between px-4 py-3">
                <div>
                  <Link
                    href={`/vacancies/${v.id}`}
                    className="font-medium text-slate-900 hover:underline"
                  >
                    {v.title}
                  </Link>
                  <p className="text-xs text-slate-500">
                    {v.seniority} · {v.modality} · {v.required_skills.join(", ")}
                  </p>
                </div>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                  {v.status}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function CreateVacancyForm({ onCreated }: { onCreated: () => void }) {
  const [title, setTitle] = useState("");
  const [requiredSkills, setRequiredSkills] = useState("");
  const [desiredSkills, setDesiredSkills] = useState("");
  const [modality, setModality] = useState<Modality>("remote");
  const [seniority, setSeniority] = useState<Seniority>("mid");
  const [country, setCountry] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function splitSkills(raw: string): string[] {
    return raw
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await createVacancy({
        title,
        required_skills: splitSkills(requiredSkills),
        desired_skills: splitSkills(desiredSkills),
        modality,
        seniority,
        country: country.trim() || null,
      });
      setTitle("");
      setRequiredSkills("");
      setDesiredSkills("");
      setCountry("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al crear la vacante.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={onSubmit}
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-6"
    >
      <h2 className="text-sm font-semibold text-slate-900">Nueva vacante</h2>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Título / cargo">
          <input
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Python Backend Developer"
            className="input"
          />
        </Field>
        <Field label="País / zona (opcional)">
          <input
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="CL"
            className="input"
          />
        </Field>
        <Field label="Skills obligatorias (separadas por coma)">
          <input
            required
            value={requiredSkills}
            onChange={(e) => setRequiredSkills(e.target.value)}
            placeholder="python, fastapi"
            className="input"
          />
        </Field>
        <Field label="Skills deseables (separadas por coma)">
          <input
            value={desiredSkills}
            onChange={(e) => setDesiredSkills(e.target.value)}
            placeholder="docker"
            className="input"
          />
        </Field>
        <Field label="Modalidad">
          <select
            value={modality}
            onChange={(e) => setModality(e.target.value as Modality)}
            className="input"
          >
            {MODALITIES.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Seniority">
          <select
            value={seniority}
            onChange={(e) => setSeniority(e.target.value as Seniority)}
            className="input"
          >
            {SENIORITIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {submitting ? "Creando…" : "Crear vacante"}
      </button>
    </form>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}
