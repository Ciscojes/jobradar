"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Pencil, Plus, Power, Trash2, X } from "lucide-react";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

type Alert = {
  id: number;
  termino: string;
  ubicacion?: string;
  categoria?: string;
  salario_minimo?: number;
  modalidad?: string;
  fuente?: string;
  activo: boolean;
  creado_en: string;
};

type AlertForm = {
  termino: string;
  ubicacion: string;
  categoria: string;
  salario_minimo: string;
  modalidad: string;
  fuente: string;
  activo: boolean;
};

const emptyForm: AlertForm = {
  termino: "",
  ubicacion: "Cualquiera",
  categoria: "",
  salario_minimo: "",
  modalidad: "Cualquiera",
  fuente: "Cualquiera",
  activo: true,
};

function toPayload(form: AlertForm) {
  return {
    termino: form.termino.trim(),
    ubicacion: form.ubicacion.trim() || "Cualquiera",
    categoria: form.categoria.trim() || null,
    salario_minimo: form.salario_minimo ? Number(form.salario_minimo) : null,
    modalidad: form.modalidad,
    fuente: form.fuente,
    activo: form.activo,
  };
}

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AlertForm>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const alertsQuery = useQuery<Alert[]>({
    queryKey: ["alerts"],
    queryFn: async () => (await api.get("/alertas/")).data,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = toPayload(form);
      if (editingId) return api.patch(`/alertas/${editingId}`, payload);
      return api.post("/alertas/", payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setMessage(editingId ? "Búsqueda actualizada." : "Búsqueda guardada y lista para ejecutarse.");
      setError("");
      setEditingId(null);
      setForm(emptyForm);
    },
    onError: (mutationError) => {
      setMessage("");
      setError(getApiErrorMessage(mutationError, "No se pudo guardar la búsqueda."));
    },
  });

  const toggleMutation = useMutation({
    mutationFn: async (alert: Alert) =>
      api.patch(`/alertas/${alert.id}/${alert.activo ? "desactivar" : "activar"}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["alerts"] }),
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo cambiar el estado.")),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/alertas/${id}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setMessage("Búsqueda eliminada.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo eliminar la búsqueda.")),
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    saveMutation.mutate();
  }

  function editAlert(alert: Alert) {
    setEditingId(alert.id);
    setForm({
      termino: alert.termino,
      ubicacion: alert.ubicacion || "Cualquiera",
      categoria: alert.categoria || "",
      salario_minimo: alert.salario_minimo?.toString() || "",
      modalidad: alert.modalidad || "Cualquiera",
      fuente: alert.fuente || "Cualquiera",
      activo: alert.activo,
    });
    setMessage("");
    setError("");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Búsquedas y alertas</h1>
        <p className="mt-1 text-gray-500">Define qué oportunidades buscará JobRadar en segundo plano.</p>
      </div>

      <form onSubmit={submit} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {editingId ? "Editar búsqueda" : "Nueva búsqueda"}
          </h2>
          {editingId && (
            <button
              type="button"
              onClick={() => { setEditingId(null); setForm(emptyForm); }}
              className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-800"
            >
              <X className="h-4 w-4" /> Cancelar
            </button>
          )}
        </div>

        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm font-medium text-gray-700">
            Puesto o palabra clave *
            <input
              required
              maxLength={160}
              value={form.termino}
              onChange={(event) => setForm({ ...form, termino: event.target.value })}
              placeholder="Python, React, Data"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Ubicación
            <input
              maxLength={160}
              value={form.ubicacion}
              onChange={(event) => setForm({ ...form, ubicacion: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Modalidad
            <select
              value={form.modalidad}
              onChange={(event) => setForm({ ...form, modalidad: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            >
              {['Cualquiera', 'Remoto', 'Híbrido', 'Presencial'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
          <label className="text-sm font-medium text-gray-700">
            Categoría
            <input
              maxLength={120}
              value={form.categoria}
              onChange={(event) => setForm({ ...form, categoria: event.target.value })}
              placeholder="Tecnología"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Salario mínimo
            <input
              type="number"
              min="0"
              max="100000000"
              value={form.salario_minimo}
              onChange={(event) => setForm({ ...form, salario_minimo: event.target.value })}
              placeholder="Opcional"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            />
          </label>
          <label className="text-sm font-medium text-gray-700">
            Fuente
            <select
              value={form.fuente}
              onChange={(event) => setForm({ ...form, fuente: event.target.value })}
              className="mt-1 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 outline-none focus:border-indigo-500"
            >
              {['Cualquiera', 'Adzuna', 'Indeed', 'InfoJobs'].map((option) => <option key={option}>{option}</option>)}
            </select>
          </label>
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input
              type="checkbox"
              checked={form.activo}
              onChange={(event) => setForm({ ...form, activo: event.target.checked })}
              className="h-4 w-4 rounded border-gray-300 text-indigo-600"
            />
            Activar esta búsqueda
          </label>
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
          >
            {editingId ? <Pencil className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
            {saveMutation.isPending ? "Guardando..." : editingId ? "Guardar cambios" : "Guardar búsqueda"}
          </button>
        </div>
      </form>

      {message && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      {alertsQuery.isLoading ? (
        <p className="text-gray-500">Cargando búsquedas...</p>
      ) : alertsQuery.isError ? (
        <p className="rounded-lg bg-red-50 p-4 text-red-700">No se pudieron cargar tus búsquedas.</p>
      ) : alertsQuery.data?.length ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {alertsQuery.data.map((alert) => (
            <article key={alert.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-gray-900">{alert.termino}</h3>
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${alert.activo ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"}`}>
                      {alert.activo ? "Activa" : "Pausada"}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-gray-500">
                    {alert.ubicacion || "Cualquiera"} · {alert.modalidad || "Cualquiera"} · {alert.fuente || "Cualquiera"}
                  </p>
                  {(alert.categoria || alert.salario_minimo) && (
                    <p className="mt-1 text-sm text-gray-500">
                      {alert.categoria && `Categoría: ${alert.categoria}`}
                      {alert.categoria && alert.salario_minimo ? " · " : ""}
                      {alert.salario_minimo && `Desde ${alert.salario_minimo.toLocaleString()}`}
                    </p>
                  )}
                </div>
                <BellRing className={`h-5 w-5 shrink-0 ${alert.activo ? "text-indigo-500" : "text-gray-300"}`} />
              </div>
              <div className="mt-4 flex flex-wrap gap-2 border-t border-gray-100 pt-4">
                <button onClick={() => editAlert(alert)} className="flex items-center gap-1 rounded-lg bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-100">
                  <Pencil className="h-4 w-4" /> Editar
                </button>
                <button onClick={() => toggleMutation.mutate(alert)} disabled={toggleMutation.isPending} className="flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-60">
                  <Power className="h-4 w-4" /> {alert.activo ? "Pausar" : "Activar"}
                </button>
                <button
                  onClick={() => window.confirm(`¿Eliminar la búsqueda “${alert.termino}”?`) && deleteMutation.mutate(alert.id)}
                  disabled={deleteMutation.isPending}
                  className="ml-auto flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-60"
                >
                  <Trash2 className="h-4 w-4" /> Eliminar
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-10 text-center">
          <BellRing className="mx-auto h-10 w-10 text-gray-300" />
          <h2 className="mt-3 font-semibold text-gray-900">Aún no tienes búsquedas guardadas</h2>
          <p className="mt-1 text-sm text-gray-500">Crea la primera para que el scheduler encuentre ofertas por ti.</p>
        </div>
      )}
    </div>
  );
}
