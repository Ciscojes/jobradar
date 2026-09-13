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

type ColumnProps = {
  title: string;
  status: "guardado" | "aplicado" | "descartado";
  ofertas: Oferta[];
  onStatusChange: (id: number, nuevoEstado: "guardado" | "aplicado" | "descartado") => void;
  colorClass: string;
};

function KanbanColumn({ title, status, ofertas, onStatusChange, colorClass }: ColumnProps) {
  return (
    <div className={`flex flex-col bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden h-[calc(100vh-140px)]`}>
      <div className={`px-4 py-3 border-b border-gray-100 font-semibold text-sm uppercase tracking-wider flex justify-between items-center ${colorClass}`}>
        <span>{title}</span>
        <span className="bg-white/50 text-gray-800 px-2 py-0.5 rounded-full text-xs">{ofertas.length}</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50/50">
        {ofertas.map((oferta) => (
          <div key={oferta.id} className="bg-white p-4 rounded-lg shadow-sm border border-gray-200 hover:border-indigo-300 transition-all group">
            <a href={oferta.enlace} target="_blank" rel="noopener noreferrer" className="block mb-2 group-hover:text-indigo-600 transition-colors">
              <h3 className="font-medium text-gray-900 line-clamp-2 leading-tight flex items-start gap-1">
                {oferta.titulo}
                <ExternalLink className="w-3.5 h-3.5 text-gray-400 shrink-0 mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
              </h3>
            </a>

            <div className="text-xs text-gray-500 mb-3 space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Building2 className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{oferta.empresa}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">{oferta.ubicacion} • {oferta.modalidad}</span>
              </div>
            </div>

            <div className="flex justify-end gap-1.5 pt-3 border-t border-gray-100">
              {status !== "guardado" && (
                <button
                  onClick={() => onStatusChange(oferta.id, "guardado")}
                  className="px-2.5 py-1 text-xs font-medium bg-yellow-50 text-yellow-700 hover:bg-yellow-100 rounded transition-colors"
                  title="Mover a Guardado"
                >
                  Guardar
                </button>
              )}
              {status !== "aplicado" && (
                <button
                  onClick={() => onStatusChange(oferta.id, "aplicado")}
                  className="px-2.5 py-1 text-xs font-medium bg-green-50 text-green-700 hover:bg-green-100 rounded transition-colors"
                  title="Mover a Aplicado"
                >
                  Aplicar
                </button>
              )}
              {status !== "descartado" && (
                <button
                  onClick={() => onStatusChange(oferta.id, "descartado")}
                  className="px-2.5 py-1 text-xs font-medium bg-red-50 text-red-700 hover:bg-red-100 rounded transition-colors"
                  title="Mover a Descartado"
                >
                  Descartar
                </button>
              )}
            </div>
          </div>
        ))}
        {ofertas.length === 0 && (
          <div className="h-full flex items-center justify-center text-sm text-gray-400 italic">
            Columna vacía
          </div>
        )}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const queryClient = useQueryClient();

  const { data: ofertas, isLoading } = useQuery<Oferta[]>({
    queryKey: ["ofertas"],
    queryFn: async () => {
      const res = await api.get("/ofertas/?limit=100");
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

  if (isLoading) return <div className="flex h-full items-center justify-center text-gray-500">Cargando tablero...</div>;

  const safeOfertas = ofertas || [];
  const guardadas = safeOfertas.filter(o => o.estado === "guardado");
  const aplicadas = safeOfertas.filter(o => o.estado === "aplicado");
  const descartadas = safeOfertas.filter(o => o.estado === "descartado");

  const handleStatusChange = (id: number, estado: "guardado" | "aplicado" | "descartado") => {
    mutation.mutate({ id, estado });
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex justify-between items-center shrink-0">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Tablero de Ofertas</h1>
          <p className="text-sm text-gray-500">Organiza y haz seguimiento a tus oportunidades.</p>
        </div>
      </div>

      {safeOfertas.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-white rounded-xl border border-dashed border-gray-300">
          <div className="text-gray-400 mb-2"><Building2 className="w-12 h-12" /></div>
          <h3 className="text-lg font-medium text-gray-900">No tienes ofertas todavía</h3>
          <p className="text-gray-500 text-sm mt-1">Configura una alerta o haz una búsqueda manual para empezar.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
          <KanbanColumn
            title="🎯 Guardadas"
            status="guardado"
            ofertas={guardadas}
            onStatusChange={handleStatusChange}
            colorClass="bg-yellow-50 text-yellow-800 border-b-yellow-200"
          />
          <KanbanColumn
            title="🚀 Aplicadas"
            status="aplicado"
            ofertas={aplicadas}
            onStatusChange={handleStatusChange}
            colorClass="bg-green-50 text-green-800 border-b-green-200"
          />
          <KanbanColumn
            title="❌ Descartadas"
            status="descartado"
            ofertas={descartadas}
            onStatusChange={handleStatusChange}
            colorClass="bg-red-50 text-red-800 border-b-red-200"
          />
        </div>
      )}
    </div>
  );
}
