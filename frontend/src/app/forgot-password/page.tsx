"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { ArrowLeft, LoaderCircle, Mail } from "lucide-react";
import AuthShell from "@/components/AuthShell";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setError("");
    try {
      const response = await api.post("/auth/forgot-password", { email });
      setMessage(response.data.message);
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, "No se pudo procesar la solicitud."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xl shadow-slate-200/60 sm:p-8">
        <div className="mb-5 inline-flex rounded-xl bg-indigo-50 p-3 text-indigo-600"><Mail className="h-6 w-6" /></div>
        <h2 className="text-2xl font-bold text-slate-900">Recupera tu contraseña</h2>
        <p className="mt-2 text-sm leading-6 text-slate-500">Escribe el correo de tu cuenta. Te enviaremos un enlace de un solo uso que caduca en 30 minutos.</p>
        {message ? (
          <div className="mt-6 space-y-4"><p role="status" className="rounded-xl border border-green-100 bg-green-50 p-4 text-sm leading-6 text-green-800">{message}</p>{process.env.NODE_ENV === "development" && <a href="http://localhost:8025" target="_blank" rel="noopener noreferrer" className="block w-full rounded-xl bg-slate-900 px-4 py-3 text-center font-semibold text-white hover:bg-slate-800">Abrir correo local</a>}</div>
        ) : (
          <form onSubmit={submit} className="mt-6 space-y-5">
            <label className="block text-sm font-medium text-slate-700">Correo electrónico<input type="email" required autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="tu@correo.com" className="mt-1.5 w-full rounded-xl border border-slate-300 px-3.5 py-2.5 text-slate-900 outline-none focus:border-indigo-500 focus:ring-4 focus:ring-indigo-100" /></label>
            {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
            <button disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-3 font-semibold text-white hover:bg-indigo-700 disabled:opacity-60">{submitting && <LoaderCircle className="h-5 w-5 animate-spin" />}{submitting ? "Enviando..." : "Enviar enlace"}</button>
          </form>
        )}
        <Link href="/login" className="mt-6 flex items-center justify-center gap-2 text-sm font-medium text-indigo-600 hover:text-indigo-800"><ArrowLeft className="h-4 w-4" /> Volver al inicio de sesión</Link>
      </div>
    </AuthShell>
  );
}
