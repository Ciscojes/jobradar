"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Check, CircleAlert, FileUser, Lightbulb, Pencil } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";

type Stats = { guardado: number; aplicado: number; descartado: number; total: number };

function CheckItem({ done, title, detail }: { done: boolean; title: string; detail: string }) {
  return <li className="flex gap-3 rounded-xl border border-slate-100 p-4"><span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${done ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-700"}`}>{done ? <Check className="h-4 w-4" /> : <CircleAlert className="h-4 w-4" />}</span><div><p className="font-medium text-slate-900">{title}</p><p className="mt-1 text-sm leading-5 text-slate-500">{detail}</p></div></li>;
}

export default function CvPage() {
  const { user } = useAuth();
  const statsQuery = useQuery<Stats>({ queryKey: ["stats"], queryFn: async () => (await api.get("/ofertas/stats")).data });
  const stats = statsQuery.data || { guardado: 0, aplicado: 0, descartado: 0, total: 0 };
  const checks = [Boolean(user?.puesto_deseado), Boolean(user?.nivel_experiencia), Boolean(user?.bio && user.bio.trim().length >= 80), stats.aplicado > 0];
  const readiness = Math.round(checks.filter(Boolean).length / checks.length * 100);

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold text-slate-900">Mi CV</h1><p className="mt-1 text-slate-500">Evalúa qué tan lista está tu candidatura para el puesto objetivo.</p></div><Link href="/dashboard/profile" className="flex items-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"><Pencil className="h-4 w-4" /> Editar datos base</Link></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[["Total ofertas", stats.total], ["Me interesan", stats.guardado], ["Ya apliqué", stats.aplicado], ["No encajan", stats.descartado]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm font-medium text-slate-500">{label}</p><p className="mt-2 text-3xl font-bold text-slate-900">{value}</p></div>)}</div>
      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <section className="rounded-2xl bg-gradient-to-br from-slate-950 to-indigo-950 p-6 text-white shadow-lg"><div className="flex items-center justify-between"><span className="rounded-lg bg-white/10 p-2"><FileUser className="h-6 w-6" /></span><span className="rounded-full bg-white/10 px-3 py-1 text-sm font-semibold">Preparación {readiness}%</span></div><h2 className="mt-8 text-2xl font-bold">{user?.puesto_deseado || "Puesto objetivo pendiente"}</h2><p className="mt-4 whitespace-pre-line leading-7 text-slate-300">{user?.bio || "Agrega un resumen de 3 a 5 líneas con tu especialidad, años de experiencia, stack principal y el tipo de producto donde aportas valor."}</p><div className="mt-6 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-indigo-400 transition-all" style={{ width: `${readiness}%` }} /></div><div className="mt-6 flex flex-wrap gap-2">{[user?.nivel_experiencia || "Nivel pendiente", user?.ubicacion_preferida || "Ubicación pendiente", user?.modalidad_preferida || "Modalidad pendiente"].map((item) => <span key={item} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-slate-300">{item}</span>)}</div></section>
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h2 className="text-lg font-semibold text-slate-900">Checklist de candidatura</h2><ul className="mt-4 space-y-3"><CheckItem done={checks[0]} title="Puesto objetivo" detail="Define el cargo principal para alinear recomendaciones y CV." /><CheckItem done={checks[1]} title="Nivel de experiencia" detail="Presenta expectativas realistas frente a cada vacante." /><CheckItem done={checks[2]} title="Resumen profesional" detail="Incluye al menos 80 caracteres con experiencia y fortalezas." /><CheckItem done={checks[3]} title="Primera aplicación" detail="Marca una oferta como aplicada para medir avance real." /></ul></section>
      </div>
      <section className="rounded-2xl border border-indigo-100 bg-indigo-50 p-6"><div className="flex gap-3"><Lightbulb className="h-6 w-6 shrink-0 text-indigo-600" /><div><h2 className="font-semibold text-indigo-950">Enfoque recomendado</h2><ul className="mt-2 grid gap-2 text-sm text-indigo-900 md:grid-cols-2"><li>• Personaliza el resumen para tu rol objetivo.</li><li>• Prioriza logros medibles de tus experiencias.</li><li>• Alinea tu stack con las ofertas guardadas.</li><li>• Actualiza el estado después de cada aplicación.</li></ul></div></div></section>
    </div>
  );
}
