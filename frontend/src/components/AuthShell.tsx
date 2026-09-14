import Link from "next/link";
import { BellRing, ChartNoAxesCombined, Radar } from "lucide-react";

export default function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen bg-slate-950 lg:grid lg:grid-cols-2">
      <section className="relative hidden overflow-hidden p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(99,102,241,0.35),_transparent_42%),radial-gradient(circle_at_bottom_right,_rgba(14,165,233,0.25),_transparent_38%)]" />
        <Link href="/" className="relative flex items-center gap-3 text-xl font-bold">
          <span className="rounded-xl bg-indigo-500 p-2"><Radar className="h-6 w-6" /></span>
          JobRadar
        </Link>
        <div className="relative max-w-xl">
          <p className="mb-4 text-sm font-bold uppercase tracking-[0.3em] text-indigo-300">Tu búsqueda, bajo control</p>
          <h1 className="text-5xl font-bold leading-tight">Convierte oportunidades en aplicaciones reales.</h1>
          <p className="mt-6 text-lg leading-8 text-slate-300">Centraliza ofertas, automatiza búsquedas y recibe avisos sin perder de vista tu progreso.</p>
          <div className="mt-10 grid grid-cols-2 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur"><BellRing className="mb-3 h-6 w-6 text-indigo-300" /><p className="font-semibold">Alertas personalizadas</p><p className="mt-1 text-sm text-slate-400">Las oportunidades llegan a ti.</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur"><ChartNoAxesCombined className="mb-3 h-6 w-6 text-sky-300" /><p className="font-semibold">Datos accionables</p><p className="mt-1 text-sm text-slate-400">Mide el avance de tu búsqueda.</p></div>
          </div>
        </div>
        <p className="relative text-sm text-slate-500">JobRadar · Empleo al gusto</p>
      </section>
      <section className="flex min-h-screen items-center justify-center bg-slate-50 px-5 py-10 sm:px-8">
        <div className="w-full max-w-lg">{children}</div>
      </section>
    </main>
  );
}
