"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { Eye, EyeOff, LoaderCircle, LogIn, Radar } from "lucide-react";
import AuthShell from "@/components/AuthShell";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    try {
      const response = await api.post("/auth/login", { email, password });
      await login(response.data.access_token);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, "No se pudo iniciar sesión."));
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="mb-8 flex items-center justify-center gap-2 text-xl font-bold text-indigo-600 lg:hidden"><Radar className="h-6 w-6" /> JobRadar</div>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
        <h2 className="text-2xl font-bold text-slate-900">Bienvenido de nuevo</h2>
        <p className="mt-2 text-sm text-slate-500">Inicia sesión para continuar tu búsqueda.</p>
        {error && <p role="alert" className="mt-5 rounded-lg border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</p>}
        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <label className="block text-sm font-medium text-slate-700">Correo electrónico
            <input type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} placeholder="tu@correo.com" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" />
          </label>
          <label className="block text-sm font-medium text-slate-700">Contraseña
            <span className="relative mt-1.5 block">
              <input type={showPassword ? "text" : "password"} autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 pr-11 text-slate-900 outline-none transition focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} className="absolute inset-y-0 right-0 px-3 text-slate-400 hover:text-slate-700">{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}</button>
            </span>
          </label>
          <div className="text-right"><Link href="/forgot-password" className="text-sm font-medium text-indigo-600 hover:text-indigo-800">¿Olvidaste tu contraseña?</Link></div>
          <button disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60">{submitting ? <LoaderCircle className="h-5 w-5 animate-spin" /> : <LogIn className="h-5 w-5" />}{submitting ? "Ingresando..." : "Iniciar sesión"}</button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-500">¿Aún no tienes una cuenta? <Link href="/register" className="font-semibold text-indigo-600 hover:text-indigo-800">Crear cuenta</Link></p>
      </div>
    </AuthShell>
  );
}
