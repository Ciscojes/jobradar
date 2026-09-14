"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCircle2, ExternalLink, MessageCircle, Power, RefreshCw, Send, Trash2 } from "lucide-react";
import api from "@/lib/api";
import { getApiErrorMessage } from "@/lib/errors";

type Channel = {
  id: number;
  type: string;
  destination: string;
  is_active: boolean;
  verified_at?: string;
  last_notification_status?: string;
  last_notification_at?: string;
  last_notification_error?: string;
};

type TelegramChat = {
  id: number | string;
  name: string;
  username?: string;
  verification_token: string;
};

type NotificationLog = {
  id: number;
  channel_type?: string;
  destination?: string;
  status: string;
  error_message?: string;
  created_at: string;
};

const botUsername = (process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME || "jobradar_alertas_bot").replace(/^@/, "");

function formatDate(value?: string) {
  if (!value) return "Sin envíos todavía";
  return new Intl.DateTimeFormat("es", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [linkToken, setLinkToken] = useState("");
  const [chats, setChats] = useState<TelegramChat[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const channelsQuery = useQuery<Channel[]>({
    queryKey: ["notification-channels"],
    queryFn: async () => (await api.get("/notificaciones/canales")).data,
  });

  const logsQuery = useQuery<NotificationLog[]>({
    queryKey: ["notification-logs"],
    queryFn: async () => (await api.get("/notificaciones/logs?limit=10")).data,
  });

  const linkMutation = useMutation({
    mutationFn: async () => (await api.post<{ link_token: string }>("/notificaciones/telegram/link")).data,
    onSuccess: ({ link_token }) => {
      setLinkToken(link_token);
      setChats([]);
      setMessage("Enlace privado creado. Ábrelo en Telegram y pulsa Start.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo crear el enlace de Telegram.")),
  });

  const detectMutation = useMutation({
    mutationFn: async () => (await api.get<{ chats: TelegramChat[] }>("/notificaciones/telegram/chats", { params: { link_token: linkToken } })).data,
    onSuccess: ({ chats: detectedChats }) => {
      setChats(detectedChats);
      setMessage(detectedChats.length ? "Chat detectado. Ya puedes conectarlo." : "Aún no se detectó un chat. Pulsa Start en Telegram y vuelve a intentar.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo detectar tu chat de Telegram.")),
  });

  const createMutation = useMutation({
    mutationFn: async (chat: TelegramChat) => api.post("/notificaciones/canales", {
      type: "telegram",
      destination: String(chat.id),
      is_active: true,
      verification_token: chat.verification_token,
    }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notification-channels"] }),
        queryClient.invalidateQueries({ queryKey: ["notification-logs"] }),
      ]);
      setChats([]);
      setLinkToken("");
      setMessage("Telegram conectado. Se envió un mensaje de bienvenida para confirmar.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo conectar el aviso.")),
  });

  const toggleMutation = useMutation({
    mutationFn: async (channel: Channel) => api.patch(`/notificaciones/canales/${channel.id}`, { is_active: !channel.is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notification-channels"] }),
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo actualizar el aviso.")),
  });

  const testMutation = useMutation({
    mutationFn: async (id: number) => api.post(`/notificaciones/canales/${id}/test`),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["notification-channels"] }),
        queryClient.invalidateQueries({ queryKey: ["notification-logs"] }),
      ]);
      setMessage("Prueba enviada. Revisa Telegram.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo enviar la prueba.")),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => api.delete(`/notificaciones/canales/${id}`),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notification-channels"] });
      setMessage("Aviso eliminado.");
      setError("");
    },
    onError: (mutationError) => setError(getApiErrorMessage(mutationError, "No se pudo eliminar el aviso.")),
  });

  const telegramUrl = linkToken ? `https://t.me/${botUsername}?start=${encodeURIComponent(linkToken)}` : "";

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Avisos por Telegram</h1>
        <p className="mt-1 text-gray-500">Recibe nuevas coincidencias aunque no tengas JobRadar abierto.</p>
      </div>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-start gap-4">
          <div className="rounded-xl bg-sky-50 p-3 text-sky-600"><MessageCircle className="h-6 w-6" /></div>
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-gray-900">Conectar Telegram</h2>
            <p className="mt-1 text-sm text-gray-500">
              JobRadar verifica el Chat ID de forma segura. El enlace privado caduca en 10 minutos.
            </p>
          </div>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-gray-200 p-4">
            <span className="text-xs font-bold uppercase tracking-wide text-indigo-600">Paso 1</span>
            <p className="mt-1 text-sm text-gray-700">Crea un enlace privado para @{botUsername}.</p>
            <button
              onClick={() => linkMutation.mutate()}
              disabled={linkMutation.isPending}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
            >
              <RefreshCw className="h-4 w-4" /> {linkToken ? "Renovar enlace" : "Crear enlace"}
            </button>
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <span className="text-xs font-bold uppercase tracking-wide text-indigo-600">Paso 2</span>
            <p className="mt-1 text-sm text-gray-700">Abre el bot y pulsa <strong>Start</strong>.</p>
            {telegramUrl ? (
              <a href={telegramUrl} target="_blank" rel="noopener noreferrer" className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-sky-500 px-3 py-2 text-sm font-medium text-white hover:bg-sky-600">
                Abrir Telegram <ExternalLink className="h-4 w-4" />
              </a>
            ) : (
              <button disabled className="mt-4 w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-400">Primero crea el enlace</button>
            )}
          </div>

          <div className="rounded-lg border border-gray-200 p-4">
            <span className="text-xs font-bold uppercase tracking-wide text-indigo-600">Paso 3</span>
            <p className="mt-1 text-sm text-gray-700">Detecta y confirma tu Chat ID.</p>
            <button
              onClick={() => detectMutation.mutate()}
              disabled={!linkToken || detectMutation.isPending}
              className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-gray-900 px-3 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-40"
            >
              <Bell className="h-4 w-4" /> {detectMutation.isPending ? "Detectando..." : "Detectar mi chat"}
            </button>
          </div>
        </div>

        {chats.length > 0 && (
          <div className="mt-5 space-y-2 rounded-lg bg-indigo-50 p-4">
            <p className="text-sm font-medium text-indigo-900">Chats verificados recientemente</p>
            {chats.map((chat) => (
              <div key={String(chat.id)} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-white p-3">
                <div>
                  <p className="font-medium text-gray-900">{chat.name}</p>
                  <p className="text-sm text-gray-500">Chat ID: {chat.id}{chat.username ? ` · @${chat.username}` : ""}</p>
                </div>
                <button
                  onClick={() => createMutation.mutate(chat)}
                  disabled={createMutation.isPending}
                  className="flex items-center gap-2 rounded-lg bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60"
                >
                  <CheckCircle2 className="h-4 w-4" /> Conectar
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {message && <p role="status" className="rounded-lg bg-green-50 p-3 text-sm text-green-700">{message}</p>}
      {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <section>
        <h2 className="mb-3 text-lg font-semibold text-gray-900">Canales conectados</h2>
        {channelsQuery.isLoading ? (
          <p className="text-gray-500">Cargando canales...</p>
        ) : channelsQuery.isError ? (
          <p className="rounded-lg bg-red-50 p-4 text-red-700">No se pudieron cargar tus avisos.</p>
        ) : channelsQuery.data?.length ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {channelsQuery.data.map((channel) => (
              <article key={channel.id} className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold capitalize text-gray-900">{channel.type}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${channel.is_active ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-600"}`}>{channel.is_active ? "Activo" : "Pausado"}</span>
                    </div>
                    <p className="mt-1 text-sm text-gray-500">Chat ID: {channel.destination}</p>
                    <p className="mt-2 text-xs text-gray-400">Último aviso: {formatDate(channel.last_notification_at)}</p>
                    {channel.last_notification_error && <p className="mt-2 text-sm text-red-600">{channel.last_notification_error}</p>}
                  </div>
                  <MessageCircle className="h-5 w-5 text-sky-500" />
                </div>
                <div className="mt-4 flex flex-wrap gap-2 border-t border-gray-100 pt-4">
                  <button onClick={() => toggleMutation.mutate(channel)} disabled={toggleMutation.isPending} className="flex items-center gap-1 rounded-lg bg-gray-100 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-60">
                    <Power className="h-4 w-4" /> {channel.is_active ? "Pausar" : "Activar"}
                  </button>
                  <button onClick={() => testMutation.mutate(channel.id)} disabled={testMutation.isPending} className="flex items-center gap-1 rounded-lg bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-60">
                    <Send className="h-4 w-4" /> Enviar prueba
                  </button>
                  <button onClick={() => window.confirm("¿Eliminar este aviso?") && deleteMutation.mutate(channel.id)} disabled={deleteMutation.isPending} className="ml-auto flex items-center gap-1 rounded-lg bg-red-50 px-3 py-1.5 text-sm font-medium text-red-700 hover:bg-red-100 disabled:opacity-60">
                    <Trash2 className="h-4 w-4" /> Eliminar
                  </button>
                </div>
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center text-sm text-gray-500">No tienes avisos conectados.</div>
        )}
      </section>

      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Historial reciente</h2>
        {logsQuery.isLoading ? (
          <p className="mt-4 text-sm text-gray-500">Cargando historial...</p>
        ) : logsQuery.data?.length ? (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 text-gray-500"><tr><th className="py-2 pr-4">Fecha</th><th className="py-2 pr-4">Canal</th><th className="py-2 pr-4">Destino</th><th className="py-2">Resultado</th></tr></thead>
              <tbody className="divide-y divide-gray-100">
                {logsQuery.data.map((log) => (
                  <tr key={log.id}><td className="py-3 pr-4 text-gray-600">{formatDate(log.created_at)}</td><td className="py-3 pr-4 capitalize text-gray-700">{log.channel_type || "—"}</td><td className="py-3 pr-4 text-gray-600">{log.destination || "—"}</td><td className="py-3"><span className={log.status === "sent" ? "text-green-700" : "text-red-700"}>{log.status}</span>{log.error_message && <p className="text-xs text-red-500">{log.error_message}</p>}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-500">Todavía no hay avisos enviados.</p>
        )}
      </section>
    </div>
  );
}
