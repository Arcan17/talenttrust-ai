"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { ApiError, getVacancy, uploadCandidate } from "@/lib/api";
import type { Candidate, Vacancy } from "@/lib/types";

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
        <>
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
              <Detail
                label="Skills obligatorias"
                value={vacancy.required_skills.join(", ") || "—"}
              />
              <Detail
                label="Skills deseables"
                value={vacancy.desired_skills.join(", ") || "—"}
              />
            </dl>
          </article>

          <CandidatesSection vacancyId={vacancy.id} />
        </>
      )}
    </div>
  );
}

function CandidatesSection({ vacancyId }: { vacancyId: string }) {
  // No list endpoint exists; we track candidates uploaded in this session.
  const [candidates, setCandidates] = useState<Candidate[]>([]);

  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Candidatos</h2>
      <UploadCandidateForm
        vacancyId={vacancyId}
        onUploaded={(c) => setCandidates((prev) => [c, ...prev])}
      />

      {candidates.length === 0 ? (
        <div className="rounded-lg border border-dashed border-slate-300 p-6 text-center">
          <p className="text-sm text-slate-500">
            Sube un CV con consentimiento para crear un candidato. Los candidatos creados en esta
            sesión aparecerán aquí con un enlace a su dossier.
          </p>
        </div>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white">
          {candidates.map((c) => (
            <li key={c.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <Link
                  href={`/candidates/${c.id}`}
                  className="font-medium text-slate-900 hover:underline"
                >
                  {c.display_name ?? c.id}
                </Link>
                <p className="text-xs text-slate-500">
                  {c.document?.parsed.language?.toUpperCase() ?? "—"} ·{" "}
                  {c.document?.parsed.skills.join(", ") || "sin skills detectadas"}
                </p>
              </div>
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
                {c.status}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function UploadCandidateForm({
  vacancyId,
  onUploaded,
}: {
  vacancyId: string;
  onUploaded: (c: Candidate) => void;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("Selecciona un archivo PDF o DOCX.");
      return;
    }
    if (!consent) {
      setError("Debes confirmar el consentimiento del candidato.");
      return;
    }
    setSubmitting(true);
    try {
      const form = new FormData();
      form.append("file", file);
      form.append("consent_version", "v1");
      form.append("consent_scope", "professional-evaluation");
      if (name.trim()) form.append("display_name", name.trim());
      const candidate = await uploadCandidate(vacancyId, form);
      onUploaded(candidate);
      setName("");
      setEmail("");
      setFile(null);
      setConsent(false);
      (e.target as HTMLFormElement).reset();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al subir el candidato.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
      <h3 className="text-sm font-semibold text-slate-900">Subir candidato (CV)</h3>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Nombre del candidato</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Jane Doe"
            className="input"
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Email (opcional)</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="jane@example.com"
            className="input"
          />
        </label>
      </div>

      <label className="block text-sm">
        <span className="mb-1 block font-medium text-slate-700">CV (PDF o DOCX, máx. 5 MB)</span>
        <input
          type="file"
          accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="block w-full text-sm text-slate-600 file:mr-3 file:rounded-md file:border-0 file:bg-slate-900 file:px-3 file:py-1.5 file:text-sm file:text-white"
        />
      </label>

      <label className="flex items-start gap-2 text-sm text-slate-700">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5"
        />
        <span>
          Confirmo contar con el consentimiento del candidato para el análisis automatizado de su
          CV con fines de evaluación profesional.
        </span>
      </label>

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
        {submitting ? "Subiendo…" : "Subir candidato"}
      </button>
    </form>
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
