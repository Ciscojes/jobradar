"use client";

import { FormEvent, useEffect, useState } from "react";
import { Save, UserRound } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

type ProfileForm = {
  nombre: string;
  puesto_deseado: string;
  ubicacion_preferida: string;
  modalidad_preferida: string;
  nivel_experiencia: string;
  bio: string;
};

const emptyProfile: ProfileForm = {
  nombre: "",
  puesto_deseado: "",
  ubicacion_preferida: "Cualquiera",
  modalidad_preferida: "Cualquiera",
  nivel_experiencia: "Junior",
  bio: "",
};

export default function ProfilePage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState<ProfileForm>(emptyProfile);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user) return;
    setForm({
      nombre: user.nombre || "",
      puesto_deseado: user.puesto_deseado || "",
      ubicacion_preferida: user.ubicacion_preferida || "Cualquiera",
      modalidad_preferida: user.modalidad_preferida || "Cualquiera",
      nivel_experiencia: user.nivel_experiencia || "Junior",
      bio: user.bio || "",
    });
  }, [user]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      await api.patch("/auth/me", {
        nombre: form.nombre.trim() || null,
        puesto_deseado: form.puesto_deseado.trim() || null,
        ubicacion_preferida: form.ubicacion_preferida.trim() || "Cualquiera",
        modalidad_preferida: form.modalidad_preferida,
        nivel_experiencia: form.nivel_experiencia,
        bio: form.bio.trim() || null,
      });
      await refreshUser();
      setMessage("Perfil actualizado. Tus preferencias ya están listas para personalizar las búsquedas.");
    } catch (submitError) {
      setError(getApiErrorMessage(submitError, "No se pudo actualizar el perfil."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Mi perfil</h1>
        <p className="mt-1 text-gray-500">Mantén tus preferencias y resumen profesional al día.</p>
      </div>

      <section className="flex items-center gap-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="rounded-full bg-indigo-50 p-4 text-indigo-600"><UserRound className="h-8 w-8" /></div>
        <div className="min-w-0">
          <h2 className="truncate text-lg font-semibold text-gray-900">{user?.nombre || "Sin nombre"}</h2>
          <p className="truncate text-sm text-gray-500">{user?.email}</p>
          <span className="mt-2 inline-block rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">Perfil activo</span>
        </div>
      </section>

      <form onSubmit={submit} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="grid gap-5 md:grid-cols-2">
          <label className="text-sm font-medium text-gray-700">
            Nombre
            <input
              maxLength={120}
              value={form.nombre}
              onChange={(event) => setForm({ ...form, nombre: event.target.value })}
              placeholder="Tu nombre"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Nivel de experiencia
            <select
              value={form.nivel_experiencia}
              onChange={(event) => setForm({ ...form, nivel_experiencia: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            >
              {['Junior', 'Semi-senior', 'Senior'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700">
            Puesto que buscas
            <input
              maxLength={160}
              value={form.puesto_deseado}
              onChange={(event) => setForm({ ...form, puesto_deseado: event.target.value })}
              placeholder="Python Developer"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Ubicación preferida
            <input
              maxLength={160}
              value={form.ubicacion_preferida}
              onChange={(event) => setForm({ ...form, ubicacion_preferida: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="text-sm font-medium text-gray-700 md:col-span-2">
            Modalidad preferida
            <select
              value={form.modalidad_preferida}
              onChange={(event) => setForm({ ...form, modalidad_preferida: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            >
              {['Cualquiera', 'Remoto', 'Híbrido', 'Presencial'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700 md:col-span-2">
            Bio / resumen del CV
            <textarea
              maxLength={5000}
              rows={8}
              value={form.bio}
              onChange={(event) => setForm({ ...form, bio: event.target.value })}
              placeholder="Resume tu especialidad, experiencia, tecnologías y el tipo de producto donde aportas valor. También puedes pegar aquí el resumen de tu CV."
              className="mt-1 w-full resize-y rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
            <span className="mt-1 block text-right text-xs font-normal text-gray-400">{form.bio.length}/5000</span>
          </label>
        </div>

        {message && <p role="status" className="mt-5 rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
        {error && <p role="alert" className="mt-5 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

        <div className="mt-6 flex justify-end">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            <Save className="h-4 w-4" /> {saving ? "Guardando..." : "Guardar perfil"}
          </button>
        </div>
      </form>
    </div>
  );
}
