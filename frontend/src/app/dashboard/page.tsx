"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import { ExternalLink, Building2, MapPin } from "lucide-react";

type Oferta = {
  id: number;
  titulo: string;
  empresa: string;
  ubicacion: string;
  modalidad: string;
  salario: string;
  descripcion: string;
  enlace: string;
  fuente: string;
  estado: "guardado" | "aplicado" | "descartado";
  fecha_publicacion: string;
  creado_en: string;
};

export default function DashboardPage() {
  const queryClient = useQueryClient();

  const { data: ofertas, isLoading } = useQuery<Oferta[]>({
    queryKey: ["ofertas"],
    queryFn: async () => {
      const res = await api.get("/ofertas/?limit=50");
      return res.data;
    },
  });

  const mutation = useMutation({
    mutationFn: async ({ id, estado }: { id: number; estado: string }) => {
      await api.patch(`/ofertas/${id}/estado`, { estado });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ofertas"] });
    },
  });

  if (isLoading) return <div>Cargando ofertas...</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Tus Ofertas</h1>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {ofertas?.map((oferta) => (
          <div key={oferta.id} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-6">
            <div className="flex-1">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                <a href={oferta.enlace} target="_blank" rel="noopener noreferrer" className="hover:text-indigo-600 flex items-center gap-2">
                  {oferta.titulo}
                  <ExternalLink className="w-4 h-4 text-gray-400" />
                </a>
              </h2>

              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-4">
                <div className="flex items-center gap-1">
                  <Building2 className="w-4 h-4" />
                  {oferta.empresa}
                </div>
                <div className="flex items-center gap-1">
                  <MapPin className="w-4 h-4" />
                  {oferta.ubicacion} • {oferta.modalidad}
                </div>
              </div>

              <p className="text-gray-600 text-sm line-clamp-2">{oferta.descripcion}</p>
            </div>

            <div className="flex flex-row md:flex-col justify-end gap-2 shrink-0 md:w-32 border-t md:border-t-0 md:border-l border-gray-100 pt-4 md:pt-0 md:pl-4">
              <button
                onClick={() => mutation.mutate({ id: oferta.id, estado: "guardado" })}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  oferta.estado === "guardado"
                    ? "bg-yellow-100 text-yellow-800"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100"
                }`}
              >
                Guardado
              </button>
              <button
                onClick={() => mutation.mutate({ id: oferta.id, estado: "aplicado" })}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  oferta.estado === "aplicado"
                    ? "bg-green-100 text-green-800"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100"
                }`}
              >
                Aplicado
              </button>
              <button
                onClick={() => mutation.mutate({ id: oferta.id, estado: "descartado" })}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  oferta.estado === "descartado"
                    ? "bg-red-100 text-red-800"
                    : "bg-gray-50 text-gray-600 hover:bg-gray-100"
                }`}
              >
                Descartado
              </button>
            </div>
          </div>
        ))}
        {ofertas?.length === 0 && (
          <div className="text-center py-12 text-gray-500">
            No tienes ofertas todavía. ¡Crea una alerta o busca manualmente!
          </div>
        )}
      </div>
    </div>
  );
}
