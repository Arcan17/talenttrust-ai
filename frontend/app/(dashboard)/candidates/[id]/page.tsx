"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  ApiError,
  createDecision,
  exportDossierPdf,
  generateDossier,
  getCandidate,
  getDecision,
  getDossier,
  getScore,
} from "@/lib/api";
import type {
  Candidate,
  Decision,
  DecisionOutcome,
  Dossier,
  Score,
} from "@/lib/types";

const OUTCOME_LABELS: Record<DecisionOutcome, string> = {
  interview: "Entrevistar",
  review: "Revisar",
  reject: "Rechazar",
  hold: "En espera",
};

async function tryGet<T>(fn: () => Promise<T>): Promise<T | null> {
  try {
    return await fn();
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null;
    throw err;
  }
}

export default function CandidatePage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const [candidate, setCandidate] = useState<Candidate | null>(null);
  const [dossier, setDossier] = useState<Dossier | null>(null);
  const [score, setScore] = useState<Score | null>(null);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const [cand, dos, sco, dec] = await Promise.all([
        getCandidate(id),
        tryGet(() => getDossier(id)),
        tryGet(() => getScore(id)),
        tryGet(() => getDecision(id)),
      ]);
      setCandidate(cand);
      setDossier(dos);
      setScore(sco);
      setDecision(dec);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar el candidato.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) return <p className="text-sm text-slate-500">Cargando…</p>;
  if (error)
    return (
      <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
        {error}
      </p>
    );
  if (!candidate) return <p className="text-sm text-slate-500">Candidato no encontrado.</p>;

  return (
    <div className="space-y-6">
      <header className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold text-slate-900">
            {candidate.display_name ?? "Candidato"}
          </h1>
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {candidate.status}
          </span>
        </div>
        {candidate.document && (
          <p className="mt-1 text-xs text-slate-500">
            {candidate.document.filename} · {candidate.document.content_type.toUpperCase()} ·
            idioma {candidate.document.parsed.language.toUpperCase()} · skills:{" "}
            {candidate.document.parsed.skills.join(", ") || "—"}
          </p>
        )}
      </header>

      <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">
        This dossier is advisory only. Final hiring decisions must be made by a human reviewer.
      </p>

      <DossierSection
        candidateId={candidate.id}
        dossier={dossier}
        score={score}
        onGenerated={load}
      />

      {dossier && (
        <>
          <DecisionSection candidateId={candidate.id} decision={decision} onSaved={load} />
          <ExportSection candidateId={candidate.id} />
        </>
      )}
    </div>
  );
}

function DossierSection({
  candidateId,
  dossier,
  score,
  onGenerated,
}: {
  candidateId: string;
  dossier: Dossier | null;
  score: Score | null;
  onGenerated: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onGenerate() {
    setBusy(true);
    setError(null);
    try {
      await generateDossier(candidateId);
      onGenerated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al generar el dossier.");
    } finally {
      setBusy(false);
    }
  }

  if (!dossier) {
    return (
      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-slate-900">Dossier</h2>
        <p className="text-sm text-slate-500">Aún no se ha generado el dossier.</p>
        {error && (
          <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}
        <button
          onClick={onGenerate}
          disabled={busy}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {busy ? "Generando…" : "Generar dossier"}
        </button>
      </section>
    );
  }

  return (
    <section className="space-y-5 rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Dossier</h2>
        <button
          onClick={onGenerate}
          disabled={busy}
          className="rounded-md border border-slate-300 px-3 py-1 text-xs text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          {busy ? "Regenerando…" : "Regenerar"}
        </button>
      </div>

      <ScoreCard score={score} recommendation={dossier.recommendation} />

      <Block title="Resumen">
        <p className="text-sm text-slate-700">{dossier.summary.text}</p>
      </Block>

      <Block title={`Skills con evidencia (${dossier.skills.length})`}>
        <ul className="space-y-1 text-sm text-slate-700">
          {dossier.skills.map((s, i) => (
            <li key={i}>
              <span className="font-medium">{s.name}</span>
              {s.required && <span className="ml-1 text-xs text-emerald-600">[obligatoria]</span>}
              <span className="text-slate-500">
                {" "}
                — {s.evidence.map((e) => `${e.source}: ${e.detail}`).join("; ")}
              </span>
            </li>
          ))}
          {dossier.skills.length === 0 && <li className="text-slate-500">Sin skills detectadas.</li>}
        </ul>
      </Block>

      <Block title={`Brechas (${dossier.gaps.length})`}>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {dossier.gaps.map((g, i) => (
            <li key={i}>
              <span className="font-medium">{g.requirement}</span>: {g.note}
            </li>
          ))}
          {dossier.gaps.length === 0 && <li className="text-slate-500">Sin brechas.</li>}
        </ul>
      </Block>

      <Block title={`Inconsistencias (${dossier.inconsistencies.length})`}>
        <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {dossier.inconsistencies.map((i, idx) => (
            <li key={idx}>
              <span className="text-xs uppercase text-slate-400">[{i.severity}]</span> {i.message}
            </li>
          ))}
          {dossier.inconsistencies.length === 0 && (
            <li className="text-slate-500">Sin inconsistencias.</li>
          )}
        </ul>
      </Block>

      <Block title={`Preguntas de entrevista (${dossier.interview_questions.length})`}>
        <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
          {dossier.interview_questions.map((q, i) => (
            <li key={i}>{q.question}</li>
          ))}
          {dossier.interview_questions.length === 0 && (
            <li className="text-slate-500">Sin preguntas sugeridas.</li>
          )}
        </ol>
      </Block>
    </section>
  );
}

function ScoreCard({
  score,
  recommendation,
}: {
  score: Score | null;
  recommendation: string;
}) {
  if (!score) return null;
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold text-slate-900">{score.value}</span>
        <span className="text-sm text-slate-500">/ 100</span>
        <span className="ml-auto rounded-full bg-white px-2 py-0.5 text-xs text-slate-600">
          IA (no vinculante): {recommendation}
        </span>
      </div>
      <table className="mt-3 w-full text-left text-xs">
        <thead className="text-slate-400">
          <tr>
            <th className="py-1">Factor</th>
            <th className="py-1">Peso</th>
            <th className="py-1">Sub-score</th>
            <th className="py-1">Ponderado</th>
          </tr>
        </thead>
        <tbody className="text-slate-700">
          {score.breakdown.map((b) => (
            <tr key={b.factor} className="border-t border-slate-200">
              <td className="py-1">{b.factor}</td>
              <td className="py-1">{b.weight}</td>
              <td className="py-1">{b.sub_score}</td>
              <td className="py-1">{b.weighted}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DecisionSection({
  candidateId,
  decision,
  onSaved,
}: {
  candidateId: string;
  decision: Decision | null;
  onSaved: () => void;
}) {
  const [outcome, setOutcome] = useState<DecisionOutcome>("interview");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSave() {
    setBusy(true);
    setError(null);
    try {
      await createDecision(candidateId, { human_outcome: outcome, note: note || undefined });
      setNote("");
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al guardar la decisión.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">Decisión humana</h2>
      <p className="text-xs text-slate-500">
        El score y la recomendación de la IA son orientativos. La decisión final es siempre humana
        y queda registrada.
      </p>

      {decision && (
        <div className="rounded-md bg-slate-50 p-3 text-sm text-slate-700">
          Última decisión: <span className="font-medium">{OUTCOME_LABELS[decision.human_outcome]}</span>{" "}
          (IA sugería: {decision.ai_recommendation})
          {decision.note && <span className="block text-slate-500">Nota: {decision.note}</span>}
          <span className="block text-xs text-slate-400">
            {new Date(decision.decided_at).toLocaleString()}
          </span>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="mb-1 block font-medium text-slate-700">Resultado</span>
          <select
            value={outcome}
            onChange={(e) => setOutcome(e.target.value as DecisionOutcome)}
            className="input"
          >
            {(Object.keys(OUTCOME_LABELS) as DecisionOutcome[]).map((o) => (
              <option key={o} value={o}>
                {OUTCOME_LABELS[o]}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm sm:col-span-2">
          <span className="mb-1 block font-medium text-slate-700">Nota / motivo (opcional)</span>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={2}
            className="input"
          />
        </label>
      </div>

      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}

      <button
        onClick={onSave}
        disabled={busy}
        className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
      >
        {busy ? "Guardando…" : "Registrar decisión"}
      </button>
    </section>
  );
}

function ExportSection({ candidateId }: { candidateId: string }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      const { blob, filename } = await exportDossierPdf(candidateId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al exportar el PDF.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-6">
      <h2 className="text-lg font-semibold text-slate-900">Exportar</h2>
      {error && (
        <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {error}
        </p>
      )}
      <button
        onClick={onExport}
        disabled={busy}
        className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
      >
        {busy ? "Generando PDF…" : "Exportar dossier PDF"}
      </button>
    </section>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="mb-1 text-sm font-semibold text-slate-800">{title}</h3>
      {children}
    </div>
  );
}
