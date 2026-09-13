"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { Briefcase, BarChart2, LogOut } from "lucide-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/login");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return <div className="flex h-screen items-center justify-center">Cargando...</div>;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <div className="flex h-screen bg-gray-50">
        <aside className="w-64 bg-white border-r border-gray-200">
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-center h-16 border-b border-gray-200">
              <span className="text-xl font-bold text-indigo-600">JobRadar</span>
            </div>
            <nav className="flex-1 px-4 py-6 space-y-2">
              <Link
                href="/dashboard"
                className="flex items-center px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
              >
                <Briefcase className="w-5 h-5 mr-3" />
                Ofertas
              </Link>
              <Link
                href="/dashboard/stats"
                className="flex items-center px-4 py-2 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <BarChart2 className="w-5 h-5 mr-3" />
                Estadísticas
              </Link>
            </nav>
            <div className="p-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="text-sm">
                  <p className="font-medium text-gray-900 truncate w-32">{user.nombre || user.email}</p>
                </div>
                <button
                  onClick={logout}
                  className="p-2 text-gray-500 hover:text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                  title="Cerrar sesión"
                >
                  <LogOut className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </aside>
        <main className="flex-1 overflow-auto bg-gray-50 p-8">
          {children}
        </main>
      </div>
    </QueryClientProvider>
  );
}
