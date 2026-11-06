"use client";

import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

type Stats = {
  guardado: number;
  aplicado: number;
  descartado: number;
  total: number;
};

export default function StatsPage() {
  const { data: stats, isLoading } = useQuery<Stats>({
    queryKey: ["stats"],
    queryFn: async () => {
      const res = await api.get("/ofertas/stats");
      return res.data;
    },
  });

  if (isLoading) return <div>Cargando estadísticas...</div>;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Métricas de Empleo</h1>
        <p className="text-gray-500 mt-1">Resumen de tu embudo de búsqueda</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-md border border-gray-200 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-2">Total</p>
          <p className="text-4xl font-bold text-gray-900">{stats?.total || 0}</p>
        </div>

        <div className="bg-white p-6 rounded-md border border-gray-200 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-900 uppercase tracking-wider mb-2">Guardadas</p>
          <p className="text-4xl font-bold text-gray-900">{stats?.guardado || 0}</p>
        </div>

        <div className="bg-white p-6 rounded-md border border-gray-200 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-900 uppercase tracking-wider mb-2">Aplicadas</p>
          <p className="text-4xl font-bold text-gray-900">{stats?.aplicado || 0}</p>
        </div>

        <div className="bg-white p-6 rounded-md border border-gray-200 flex flex-col justify-center">
          <p className="text-sm font-medium text-gray-900 uppercase tracking-wider mb-2">Descartadas</p>
          <p className="text-4xl font-bold text-gray-900">{stats?.descartado || 0}</p>
        </div>
      </div>

      {stats && stats.total > 0 && (
        <div className="bg-white p-6 rounded-md border border-gray-200 mt-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Distribución de ofertas</h2>
          <div className="w-full h-8 flex rounded-lg overflow-hidden">
            <div
              style={{ width: `${(stats.guardado / stats.total) * 100}%` }}
              className="bg-yellow-400 h-full flex items-center justify-center text-xs font-bold text-gray-900"
              title="Guardadas"
            >
              {stats.guardado > 0 ? `${Math.round((stats.guardado / stats.total) * 100)}%` : ""}
            </div>
            <div
              style={{ width: `${(stats.aplicado / stats.total) * 100}%` }}
              className="bg-green-500 h-full flex items-center justify-center text-xs font-bold text-white"
              title="Aplicadas"
            >
              {stats.aplicado > 0 ? `${Math.round((stats.aplicado / stats.total) * 100)}%` : ""}
            </div>
            <div
              style={{ width: `${(stats.descartado / stats.total) * 100}%` }}
              className="bg-red-500 h-full flex items-center justify-center text-xs font-bold text-white"
              title="Descartadas"
            >
              {stats.descartado > 0 ? `${Math.round((stats.descartado / stats.total) * 100)}%` : ""}
            </div>
          </div>
          <div className="flex justify-between mt-4 text-sm text-gray-600">
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-yellow-400 rounded-full"></div> Guardadas</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-green-500 rounded-full"></div> Aplicadas</span>
            <span className="flex items-center gap-1"><div className="w-3 h-3 bg-red-500 rounded-full"></div> Descartadas</span>
          </div>
        </div>
      )}
    </div>
  );
}
