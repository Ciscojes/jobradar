"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { CheckCircle2, Eye, EyeOff, KeyRound, LoaderCircle } from "lucide-react";
import AuthShell from "@/components/AuthShell";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => setToken(new URLSearchParams(window.location.search).get("token") || ""), []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (!token) return setError("El enlace no contiene un token válido.");
    if (password.length < 8) return setError("La contraseña debe tener al menos 8 caracteres.");
    if (password !== confirmation) return setError("Las contraseñas no coinciden.");
    setSubmitting(true);
    try {
      await api.post("/auth/reset-password", { token, password });
      setDone(true);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, "No se pudo actualizar la contraseña."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
        {done ? (
          <div className="text-center"><CheckCircle2 className="mx-auto h-14 w-14 text-green-500" /><h2 className="mt-4 text-2xl font-bold text-slate-900">Contraseña actualizada</h2><p className="mt-2 text-sm text-slate-500">Tu enlace ya fue utilizado y las sesiones anteriores quedaron invalidadas.</p><Link href="/login" className="mt-6 block rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-700">Iniciar sesión</Link></div>
        ) : (
          <><div className="mb-5 inline-flex rounded-xl bg-indigo-50 p-3 text-indigo-600"><KeyRound className="h-6 w-6" /></div><h2 className="text-2xl font-bold text-slate-900">Elige una nueva contraseña</h2><p className="mt-2 text-sm text-slate-500">Utiliza al menos 8 caracteres y evita reutilizar contraseñas de otros servicios.</p><form onSubmit={submit} className="mt-6 space-y-5"><label className="block text-sm font-medium text-slate-700">Nueva contraseña<span className="relative mt-1.5 block"><input type={showPassword ? "text" : "password"} required minLength={8} maxLength={128} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} className="w-full rounded-xl border border-slate-300 px-3.5 py-2.5 pr-11 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /><button type="button" onClick={() => setShowPassword(!showPassword)} aria-label={showPassword ? "Ocultar contraseña" : "Mostrar contraseña"} className="absolute inset-y-0 right-0 px-3 text-slate-400">{showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}</button></span></label><label className="block text-sm font-medium text-slate-700">Confirmar contraseña<input type={showPassword ? "text" : "password"} required minLength={8} autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /></label>{error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={submitting || !token} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">{submitting && <LoaderCircle className="h-5 w-5 animate-spin" />}{submitting ? "Actualizando..." : "Guardar nueva contraseña"}</button></form>{!token && <p className="mt-4 text-center text-sm text-red-600">Este enlace está incompleto. Solicita uno nuevo.</p>}<Link href="/forgot-password" className="mt-6 block text-center text-sm font-medium text-indigo-600 hover:text-indigo-800">Solicitar otro enlace</Link></>
        )}
      </div>
    </AuthShell>
  );
}
