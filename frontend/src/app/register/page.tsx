"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Eye, EyeOff, LoaderCircle, Radar, UserPlus } from "lucide-react";
import AuthShell from "@/components/AuthShell";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

export default function RegisterPage() {
  const { login } = useAuth();
  const [form, setForm] = useState({ nombre: "", email: "", password: "", confirmPassword: "", puesto_deseado: "", ubicacion_preferida: "Cualquiera", modalidad_preferida: "Cualquiera" });
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) return setError("Las contraseñas no coinciden.");
    if (form.password.length < 8) return setError("La contraseña debe tener al menos 8 caracteres.");
    setSubmitting(true);
    try {
      await api.post("/auth/register", {
        nombre: form.nombre.trim() || null,
        email: form.email,
        password: form.password,
        puesto_deseado: form.puesto_deseado.trim() || null,
        ubicacion_preferida: form.ubicacion_preferida.trim() || "Cualquiera",
        modalidad_preferida: form.modalidad_preferida,
      });
      const response = await api.post("/auth/login", { email: form.email, password: form.password });
      await login(response.data.access_token);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, "No se pudo crear la cuenta."));
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="mb-6 flex items-center justify-center gap-2 text-xl font-bold text-indigo-600 lg:hidden"><Radar className="h-6 w-6" /> JobRadar</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900">Crea tu cuenta</h2>
        <p className="mt-2 text-sm text-slate-500">Configura tu objetivo y recibe recomendaciones desde el primer ingreso.</p>
        {error && <p role="alert" className="mt-5 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <form onSubmit={submit} className="mt-6 space-y-5">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">Nombre<input maxLength={120} autoComplete="name" value={form.nombre} onChange={(event) => setForm({ ...form, nombre: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /></label>
            <label className="text-sm font-medium text-slate-700">Correo electrónico *<input type="email" required autoComplete="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /></label>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-medium text-slate-700">Contraseña *<span className="relative mt-1.5 block"><input type={showPassword ? "text" : "password"} minLength={8} maxLength={128} required autoComplete="new-password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 pr-11 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} className="absolute inset-y-0 right-0 px-3 text-slate-400">{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}</button></span><span className="mt-1 block text-xs font-normal text-slate-400">Mínimo 8 caracteres</span></label>
            <label className="text-sm font-medium text-slate-700">Confirmar contraseña *<input type={showPassword ? "text" : "password"} minLength={8} required autoComplete="new-password" value={form.confirmPassword} onChange={(event) => setForm({ ...form, confirmPassword: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /></label>
          </div>
          <div className="border-t border-slate-100 pt-5">
            <p className="mb-4 text-sm font-semibold text-slate-900">Tu búsqueda inicial</p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-slate-700">Puesto que buscas<input maxLength={160} value={form.puesto_deseado} onChange={(event) => setForm({ ...form, puesto_deseado: event.target.value })} placeholder="Python Developer" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500" /></label>
              <label className="text-sm font-medium text-slate-700">Ubicación<input maxLength={160} value={form.ubicacion_preferida} onChange={(event) => setForm({ ...form, ubicacion_preferida: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500" /></label>
            </div>
            <label className="mt-4 block text-sm font-medium text-slate-700">Modalidad<select value={form.modalidad_preferida} onChange={(event) => setForm({ ...form, modalidad_preferida: event.target.value })} className="mt-1.5 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500">{["Cualquiera", "Remoto", "Híbrido", "Presencial"].map((option) => <option key={option}>{option}</option>)}</select></label>
          </div>
          <button disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{submitting ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <UserPlus className="h-5 w-5" />}{submitting ? "Creando cuenta..." : "Crear cuenta y entrar"}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">¿Ya tienes cuenta? <Link href="/login" className="font-semibold text-indigo-600 hover:text-indigo-800">Iniciar sesión</Link></p>
      </div>
    </AuthShell>
  );
}
