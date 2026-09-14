"use client";

import { useAuth } from "@/context/AuthContext";
import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import Link from "next/link";
import { Activity, Bell, Briefcase, BarChart2, FileUser, LogOut, Search, UserRound } from "lucide-react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const navigation = [
    { href: "/dashboard", label: "Ofertas", icon: Briefcase, exact: true },
    { href: "/dashboard/cv", label: "Mi CV", icon: FileUser },
    { href: "/dashboard/alerts", label: "Búsquedas", icon: Search },
    { href: "/dashboard/notifications", label: "Avisos", icon: Bell },
    { href: "/dashboard/activity", label: "Actividad", icon: Activity },
    { href: "/dashboard/stats", label: "Estadísticas", icon: BarChart2 },
    { href: "/dashboard/profile", label: "Mi perfil", icon: UserRound },
  ];

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
      <div className="flex min-h-screen bg-gray-50">
        <aside className="fixed inset-y-0 left-0 z-10 w-20 bg-white border-r border-gray-200 md:w-64">
          <div className="h-full flex flex-col">
            <div className="flex items-center justify-center h-16 border-b border-gray-200">
              <span className="hidden text-xl font-bold text-indigo-600 md:inline">JobRadar</span>
              <span className="text-xl font-bold text-indigo-600 md:hidden">JR</span>
            </div>
            <nav className="flex-1 space-y-2 overflow-y-auto px-4 py-6">
              {navigation.map(({ href, label, icon: Icon, exact }) => {
                const active = exact ? pathname === href : pathname.startsWith(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    title={label}
                    className={`flex items-center justify-center rounded-lg px-4 py-2 transition-colors md:justify-start ${
                      active
                        ? "bg-indigo-50 font-medium text-indigo-700"
                        : "text-gray-700 hover:bg-gray-100"
                    }`}
                  >
                    <Icon className="h-5 w-5 shrink-0 md:mr-3" />
                    <span className="hidden md:inline">{label}</span>
                  </Link>
                );
              })}
            </nav>
            <div className="p-4 border-t border-gray-200">
              <div className="flex items-center justify-between">
                <div className="hidden min-w-0 text-sm md:block">
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
        <main className="ml-20 min-h-screen flex-1 overflow-auto bg-gray-50 p-4 md:ml-64 md:p-8">
          {children}
        </main>
      </div>
    </QueryClientProvider>
  );
}
