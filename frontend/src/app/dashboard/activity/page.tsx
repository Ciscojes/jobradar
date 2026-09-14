"use client";

import { useQuery } from "@tanstack/react-query";
import { Activity, AlertCircle, CheckCircle2, Clock3, RefreshCw, Search } from "lucide-react";
import api from "@/lib/api";

type ScraperRun = { id: number; source: string; status: string; started_at: string; finished_at?: string; duration_seconds: number; offers_found: number; new_offers: number; new_matches: number; error_message?: string };

function date(value: string) { return new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value)); }

export default function ActivityPage() {
  const runsQuery = useQuery<ScraperRun[]>({ queryKey: ["scraper-runs"], queryFn: async () => (await api.get("/scraper/runs?limit=100")).data, refetchInterval: 30_000 });
  const runs = runsQuery.data || [];
  const successful = runs.filter((run) => run.status === "success").length;
  const matches = runs.reduce((total, run) => total + run.new_matches, 0);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold text-slate-900">Actividad reciente</h1><p className="mt-1 text-slate-500">Ejecuciones automáticas y manuales del buscador.</p></div><button onClick={() => runsQuery.refetch()} disabled={runsQuery.isFetching} className="flex items-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-60"><RefreshCw className={`h-4 w-4 ${runsQuery.isFetching ? "animate-spin" : ""}`} /> Actualizar</button></div>
      <div className="grid gap-4 sm:grid-cols-3"><div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">Ejecuciones mostradas</p><p className="mt-2 text-3xl font-bold text-slate-900">{runs.length}</p></div><div className="rounded-xl border border-green-100 bg-green-50 p-5"><p className="text-sm text-green-700">Completadas</p><p className="mt-2 text-3xl font-bold text-green-900">{successful}</p></div><div className="rounded-xl border border-indigo-100 bg-indigo-50 p-5"><p className="text-sm text-indigo-700">Coincidencias nuevas</p><p className="mt-2 text-3xl font-bold text-indigo-900">{matches}</p></div></div>
      {runsQuery.isLoading ? <div className="flex justify-center py-20 text-slate-500"><RefreshCw className="mr-2 h-5 w-5 animate-spin" /> Cargando actividad...</div> : runsQuery.isError ? <p className="rounded-xl bg-red-50 p-4 text-red-700">No se pudo cargar la actividad.</p> : runs.length ? <div className="space-y-3">{runs.map((run) => { const ok = run.status === "success"; const running = run.status === "running"; return <article key={run.id} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><div className="flex flex-wrap items-start justify-between gap-4"><div className="flex gap-3"><span className={`rounded-xl p-2.5 ${ok ? "bg-green-50 text-green-600" : running ? "bg-amber-50 text-amber-600" : "bg-red-50 text-red-600"}`}>{ok ? <CheckCircle2 className="h-5 w-5" /> : running ? <Clock3 className="h-5 w-5" /> : <AlertCircle className="h-5 w-5" />}</span><div><h2 className="font-semibold text-slate-900">Búsqueda en {run.source}</h2><p className="mt-1 text-sm text-slate-500">{date(run.started_at)} · {run.duration_seconds}s</p></div></div><span className={`rounded-full px-3 py-1 text-xs font-semibold ${ok ? "bg-green-50 text-green-700" : running ? "bg-amber-50 text-amber-700" : "bg-red-50 text-red-700"}`}>{ok ? "Completada" : running ? "En curso" : "Con error"}</span></div><div className="mt-4 grid grid-cols-3 gap-3 border-t border-slate-100 pt-4 text-center"><div><p className="text-xl font-bold text-slate-900">{run.offers_found}</p><p className="text-xs text-slate-500">Encontradas</p></div><div><p className="text-xl font-bold text-slate-900">{run.new_offers}</p><p className="text-xs text-slate-500">Nuevas</p></div><div><p className="text-xl font-bold text-indigo-700">{run.new_matches}</p><p className="text-xs text-slate-500">Coincidencias</p></div></div>{run.error_message && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{run.error_message}</p>}</article>; })}</div> : <div className="rounded-2xl border border-dashed border-slate-300 bg-white py-16 text-center"><Search className="mx-auto h-10 w-10 text-slate-300" /><h2 className="mt-3 font-semibold text-slate-900">Sin actividad todavía</h2><p className="mt-1 text-sm text-slate-500">Las búsquedas aparecerán aquí cuando el scheduler empiece a trabajar.</p></div>}
      <p className="flex items-center justify-center gap-2 text-xs text-slate-400"><Activity className="h-4 w-4" /> Actualización automática cada 30 segundos</p>
    </div>
  );
}
