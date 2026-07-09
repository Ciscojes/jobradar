import html
import os

import pandas as pd
import requests
import streamlit as st

from components.filters import render_offer_filters
from components.metrics import render_offer_metrics


API_BASE_URL = os.getenv("JOBRADAR_API_URL", "http://localhost:8000").rstrip("/")
TELEGRAM_BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME", "jobradar_alertas_bot").strip().lstrip("@")


st.set_page_config(
    page_title="JobRadar",
    layout="wide",
)


STATUS_LABELS = {
    "guardado": "Me interesa",
    "aplicado": "Ya apliqué",
    "descartado": "No encaja",
}

STATUS_VALUES = {label: value for value, label in STATUS_LABELS.items()}


APP_CSS = """
<style>
    .block-container {
        max-width: 1180px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }
    section[data-testid="stSidebar"] {
        background: #f8faf8;
        border-right: 1px solid #e5e7eb;
    }
    section[data-testid="stSidebar"] h1 {
        color: #14532d;
        font-size: 1.45rem;
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 0.95rem 1rem;
    }
    .jr-header {
        border-bottom: 1px solid #e5e7eb;
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
    }
    .jr-header h2 {
        margin-bottom: 0.15rem;
    }
    .jr-muted {
        color: #64748b;
        font-size: 0.95rem;
    }
    .jr-empty {
        background: #f8fafc;
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 1.25rem;
        margin-top: 1rem;
    }
    .jr-kicker {
        color: #166534;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .jr-card-title {
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .jr-chip {
        display: inline-block;
        border: 1px solid #d1d5db;
        border-radius: 999px;
        color: #374151;
        font-size: 0.8rem;
        margin: 0.15rem 0.2rem 0.15rem 0;
        padding: 0.18rem 0.55rem;
    }
    .jr-status {
        background: #ecfdf5;
        border: 1px solid #bbf7d0;
        border-radius: 999px;
        color: #166534;
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.22rem 0.65rem;
    }
</style>
"""


def apply_global_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_page_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = f'<div class="jr-muted">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="jr-header">
            <h2>{title}</h2>
            {subtitle_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_empty_state(title: str, body: str, button_label: str | None = None, target_section: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="jr-empty">
            <div class="jr-card-title">{title}</div>
            <div class="jr-muted">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if button_label and target_section:
        st.button(button_label, on_click=set_active_section, args=(target_section,))


def set_active_section(section: str) -> None:
    st.session_state["section"] = section


def format_status(status: str | None) -> str:
    return STATUS_LABELS.get(status or "guardado", "Me interesa")


def truncate_text(value: str | None, limit: int = 260) -> str:
    if not value:
        return ""
    clean_value = " ".join(str(value).split())
    if len(clean_value) <= limit:
        return clean_value
    return clean_value[: limit - 3].rstrip() + "..."


def safe_html(value: object, fallback: str = "") -> str:
    return html.escape(str(value or fallback), quote=True)


def api_headers() -> dict[str, str]:
    token = st.session_state.get("access_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(method: str, path: str, **kwargs):
    response = requests.request(
        method,
        f"{API_BASE_URL}{path}",
        headers={**api_headers(), **kwargs.pop("headers", {})},
        timeout=20,
        **kwargs,
    )
    if response.status_code == 401:
        st.session_state.pop("access_token", None)
        st.error("La sesión expiró. Inicia sesión de nuevo.")
        st.stop()
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(detail)
    if response.status_code == 204:
        return None
    return response.json()


def render_auth() -> None:
    left_col, right_col = st.columns([1, 1], gap="large")
    with left_col:
        st.markdown(
            """
            <div class="jr-kicker">JobRadar</div>
            <h1>Tus ofertas recomendadas en un solo lugar</h1>
            <p class="jr-muted">
                Configura tu búsqueda, revisa oportunidades y guarda el avance de cada candidatura.
            </p>
            """,
            unsafe_allow_html=True,
        )
    with right_col:
        st.markdown("### Acceso")
        login_tab, register_tab = st.tabs(["Iniciar sesión", "Registro"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Entrar")
        if submitted:
            try:
                token = api_request(
                    "POST",
                    "/auth/login",
                    json={"email": email, "password": password},
                )
                st.session_state["access_token"] = token["access_token"]
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))

    with register_tab:
        with st.form("register_form"):
            st.markdown("**Datos de acceso**")
            nombre = st.text_input("Nombre")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Contraseña", type="password", key="register_password")

            st.markdown("---")
            st.markdown("**Tu búsqueda**")
            col_puesto, col_ubicacion, col_modalidad = st.columns(3)
            puesto_deseado = col_puesto.text_input("Puesto que buscas", placeholder="Python Developer")
            ubicacion_preferida = col_ubicacion.text_input("Ubicación preferida", value="Cualquiera")
            modalidad_preferida = col_modalidad.selectbox(
                "Modalidad", ["Cualquiera", "Remoto", "Híbrido", "Presencial"]
            )
            submitted = st.form_submit_button("Crear cuenta")
        if submitted:
            try:
                api_request(
                    "POST",
                    "/auth/register",
                    json={
                        "nombre": nombre,
                        "email": email,
                        "password": password,
                        "puesto_deseado": puesto_deseado or None,
                        "ubicacion_preferida": ubicacion_preferida or "Cualquiera",
                        "modalidad_preferida": modalidad_preferida,
                    },
                )
                token = api_request(
                    "POST",
                    "/auth/login",
                    json={"email": email, "password": password},
                )
                st.session_state["access_token"] = token["access_token"]
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))


def load_offers() -> pd.DataFrame:
    offers = api_request("GET", "/ofertas/")
    return pd.DataFrame(offers)


def apply_filters(
    offers: pd.DataFrame,
    keyword: str,
    empresa: str,
    ubicacion: str,
    estado: str,
) -> pd.DataFrame:
    filtered = offers.copy()

    if keyword:
        keyword_mask = (
            filtered["titulo"].fillna("").str.contains(keyword, case=False, na=False)
            | filtered["descripcion"].fillna("").str.contains(keyword, case=False, na=False)
        )
        filtered = filtered[keyword_mask]

    if empresa != "Todas":
        filtered = filtered[filtered["empresa"] == empresa]

    if ubicacion != "Todas":
        filtered = filtered[filtered["ubicacion"] == ubicacion]

    if estado != "Todas":
        filtered = filtered[filtered["estado"] == STATUS_VALUES[estado]]

    return filtered


def render_offers() -> None:
    render_page_header(
        "Ofertas recomendadas",
        "Revisa oportunidades que coinciden con tu perfil y guarda el estado de cada una.",
    )
    saved_message = st.session_state.pop("offer_saved_message", None)
    if saved_message:
        st.success(saved_message)

    with st.expander("Buscar nuevas ofertas", expanded=False):
        with st.form("sync_form"):
            query = st.text_input("Puesto o palabra clave", value="python")
            submitted = st.form_submit_button("Actualizar recomendaciones")
    if submitted:
        try:
            result = api_request(
                "POST",
                "/scraper/sync",
                params={"query": query.strip() or "python"},
            )
            st.success(result["message"].replace("Sincronización", "Búsqueda"))
        except RuntimeError as error:
            st.error(str(error))

    offers = load_offers()
    if offers.empty:
        render_offer_metrics(offers)
        render_empty_state(
            "Aún no hay ofertas para revisar",
            "Completa tu perfil o guarda una búsqueda para que JobRadar empiece a traer oportunidades relevantes.",
            "Completar mi perfil",
            "Mi perfil",
        )
        return

    status_counts = offers["estado"].fillna("guardado").value_counts().to_dict()
    status_cols = st.columns(4)
    status_cols[0].metric("Todas", len(offers))
    for index, (status, label) in enumerate(STATUS_LABELS.items(), start=1):
        status_cols[index].metric(label, int(status_counts.get(status, 0)))

    with st.container(border=True):
        keyword, empresa, ubicacion = render_offer_filters(offers)
        estado = st.radio(
            "Estado",
            ["Todas", *STATUS_VALUES.keys()],
            horizontal=True,
        )
    filtered_offers = apply_filters(offers, keyword, empresa, ubicacion, estado)

    render_offer_metrics(filtered_offers)

    if filtered_offers.empty:
        render_empty_state(
            "No hay resultados con esos filtros",
            "Prueba con otra palabra clave, empresa o ubicación para ampliar la lista.",
        )
        return

    for offer in filtered_offers.head(50).to_dict("records"):
        current_status = offer["estado"] if offer["estado"] in STATUS_LABELS else "guardado"
        current_label = STATUS_LABELS[current_status]
        with st.container(border=True):
            top_col, status_col = st.columns([5, 2])
            top_col.markdown(
                f"""
                <div class="jr-kicker">{safe_html(offer.get("empresa"), "Empresa confidencial")}</div>
                <div class="jr-card-title">{safe_html(offer.get("titulo"), "Oferta sin título")}</div>
                """,
                unsafe_allow_html=True,
            )
            top_col.markdown(
                "".join(
                    f'<span class="jr-chip">{safe_html(value)}</span>'
                    for value in [
                        offer.get("ubicacion") or "Ubicación no indicada",
                        offer.get("modalidad") or "Modalidad no indicada",
                        offer.get("salario") if offer.get("salario") != "No especificado" else None,
                    ]
                    if value
                ),
                unsafe_allow_html=True,
            )
            if offer.get("descripcion"):
                top_col.write(truncate_text(offer.get("descripcion")))
            if offer.get("enlace"):
                top_col.link_button("Ver oferta", offer["enlace"])

            status_col.markdown(
                f'<span class="jr-status">{format_status(current_status)}</span>',
                unsafe_allow_html=True,
            )
            new_label = status_col.selectbox(
                "Seguimiento",
                list(STATUS_VALUES),
                index=list(STATUS_VALUES).index(current_label),
                key=f"offer_status_{offer['id']}_{offer.get('user_oferta_id')}",
            )
            if status_col.button(
                "Guardar",
                key=f"save_offer_status_{offer['id']}_{offer.get('user_oferta_id')}",
            ):
                try:
                    api_request(
                        "PATCH",
                        f"/ofertas/{offer['id']}/estado",
                        json={"estado": STATUS_VALUES[new_label]},
                    )
                    st.session_state["offer_saved_message"] = (
                        f"Estado guardado: {offer.get('titulo') or 'Oferta'} -> {new_label}"
                    )
                    st.rerun()
                except RuntimeError as error:
                    st.error(str(error))


def render_scraper_runs() -> None:
    render_page_header("Actividad reciente", "Últimas búsquedas automáticas y manuales.")
    try:
        runs = api_request("GET", "/scraper/runs")
    except RuntimeError as error:
        st.error(str(error))
        return

    if not runs:
        render_empty_state(
            "Sin actividad todavía",
            "Cuando actualices recomendaciones o se ejecuten búsquedas guardadas, verás aquí el historial.",
        )
        return

    runs_df = pd.DataFrame(runs)
    runs_df = runs_df.rename(
        columns={
            "started_at": "Inicio",
            "finished_at": "Fin",
            "status": "Resultado",
            "duration_seconds": "Duración",
            "offers_found": "Encontradas",
            "new_offers": "Nuevas",
            "new_matches": "Coincidencias",
            "error_message": "Detalle",
        }
    )
    columnas_deseadas = ["Inicio", "Fin", "Resultado", "Duración", "Encontradas", "Nuevas", "Coincidencias", "Detalle"]
    columnas_disponibles = [column for column in columnas_deseadas if column in runs_df.columns]
    st.dataframe(
        runs_df[columnas_disponibles],
        hide_index=True,
        width="stretch",
    )


def render_alerts() -> None:
    render_page_header("Búsquedas guardadas", "Define qué tipo de ofertas quieres recibir.")
    alerts = api_request("GET", "/alertas/")

    with st.form("create_alert_form"):
        col_term, col_location, col_modality = st.columns(3)
        termino = col_term.text_input("Puesto o palabra clave", placeholder="python, react, data")
        ubicacion = col_location.text_input("Ubicación", value="Cualquiera")
        modalidad = col_modality.selectbox("Modalidad", ["Cualquiera", "Remoto", "Híbrido", "Presencial"])
        submitted = st.form_submit_button("Guardar búsqueda")
    if submitted:
        try:
            api_request(
                "POST",
                "/alertas/",
                json={
                    "termino": termino,
                    "ubicacion": ubicacion or "Cualquiera",
                    "modalidad": modalidad or "Cualquiera",
                    "activo": True,
                },
            )
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))

    if not alerts:
        render_empty_state(
            "No tienes búsquedas guardadas",
            "Guarda una búsqueda para revisar nuevas ofertas sin tener que escribir los mismos filtros cada vez.",
        )
        return

    for alert in alerts:
        with st.form(f"edit_alert_{alert['id']}"):
            cols = st.columns([3, 2, 2, 1, 1])
            termino = cols[0].text_input(
                "Puesto o palabra clave",
                value=alert["termino"],
                key=f"alert_term_{alert['id']}",
                label_visibility="collapsed",
            )
            ubicacion = cols[1].text_input(
                "Ubicación",
                value=alert["ubicacion"],
                key=f"alert_location_{alert['id']}",
                label_visibility="collapsed",
            )
            modalidad = cols[2].text_input(
                "Modalidad",
                value=alert["modalidad"],
                key=f"alert_modality_{alert['id']}",
                label_visibility="collapsed",
            )
            activo = cols[3].checkbox(
                "Activa",
                value=alert["activo"],
                key=f"alert_active_{alert['id']}",
            )
            save = cols[4].form_submit_button("Guardar")
        if save:
            api_request(
                "PATCH",
                f"/alertas/{alert['id']}",
                json={
                    "termino": termino,
                    "ubicacion": ubicacion or "Cualquiera",
                    "modalidad": modalidad or "Cualquiera",
                    "activo": activo,
                },
            )
            st.rerun()

        if st.button("Eliminar", key=f"delete_alert_{alert['id']}"):
            api_request("DELETE", f"/alertas/{alert['id']}")
            st.rerun()


def render_channels() -> None:
    render_page_header("Avisos", "Elige dónde recibir nuevas oportunidades.")
    channels = api_request("GET", "/notificaciones/canales")
    bot_url = f"https://t.me/{TELEGRAM_BOT_USERNAME}"
    created_message = st.session_state.pop("channel_created_message", None)
    if created_message:
        st.success(created_message)

    st.markdown("### Telegram")
    st.info(
        "Para recibir ofertas por Telegram, abre el bot oficial de JobRadar, pulsa Start y vuelve "
        "a esta pantalla para conectar tu cuenta."
    )
    col_bot, col_detect = st.columns([2, 1])
    col_bot.link_button(f"Abrir @{TELEGRAM_BOT_USERNAME}", bot_url)
    if col_detect.button("Detectar mi chat ID"):
        try:
            result = api_request("GET", "/notificaciones/telegram/chats")
            st.session_state["telegram_chats"] = result["chats"]
            if result["chats"]:
                st.success("Chat detectado. Selecciónalo abajo y agrega el aviso.")
            else:
                st.warning("No encontré chats recientes. Abre el bot, pulsa Start y vuelve a detectar.")
        except RuntimeError as error:
            st.error(str(error))

    with st.form("create_channel_form"):
        channel_type_label = st.selectbox("Canal", ["Telegram", "Email"])
        channel_type = channel_type_label.lower()
        detected_chats = st.session_state.get("telegram_chats", [])

        if channel_type == "telegram":
            if detected_chats:
                selected_chat = st.selectbox(
                    "Tu Telegram",
                    detected_chats,
                    format_func=lambda chat: f"{chat['name']} ({chat['id']})",
                )
                destination = str(selected_chat["id"])
            else:
                st.warning(
                    "Primero abre el bot, pulsa Start y usa Detectar mi chat ID. "
                    "Si ya lo hiciste, vuelve a detectar."
                )
                destination = ""
                with st.expander("Ingresar chat ID manualmente"):
                    destination = st.text_input("Chat ID", placeholder="Ejemplo: 1463980165")
        else:
            destination = st.text_input("Email", placeholder="tu@email.com")

        submitted = st.form_submit_button("Agregar aviso")
    if submitted:
        if not destination.strip():
            st.error("Falta seleccionar o ingresar el destino del aviso.")
        else:
            try:
                api_request(
                    "POST",
                    "/notificaciones/canales",
                    json={"type": channel_type, "destination": destination, "is_active": True},
                )
                st.session_state["channel_created_message"] = (
                    "Aviso de Telegram conectado. Usa Probar para enviar un mensaje."
                    if channel_type == "telegram"
                    else "Aviso por email conectado."
                )
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))

    if st.session_state.get("telegram_chats"):
        with st.expander("Chats detectados recientemente"):
            st.dataframe(
                pd.DataFrame(st.session_state["telegram_chats"]),
                hide_index=True,
                width="stretch",
            )

    if not channels:
        render_empty_state(
            "No tienes avisos configurados",
            "Añade un canal cuando quieras recibir nuevas oportunidades fuera del dashboard.",
        )
        return

    for channel in channels:
        cols = st.columns([1, 3, 1, 1, 1])
        cols[0].write(channel["type"].title())
        cols[1].write(channel["destination"])
        active = cols[2].toggle("Activo", value=channel["is_active"], key=f"channel_{channel['id']}")
        if active != channel["is_active"]:
            api_request(
                "PATCH",
                f"/notificaciones/canales/{channel['id']}",
                json={"is_active": active},
            )
            st.rerun()
        if cols[3].button("Probar", key=f"test_channel_{channel['id']}"):
            try:
                result = api_request("POST", f"/notificaciones/canales/{channel['id']}/test")
                st.success(result["status"])
            except RuntimeError as error:
                st.error(str(error))
        if cols[4].button("Eliminar", key=f"delete_channel_{channel['id']}"):
            api_request("DELETE", f"/notificaciones/canales/{channel['id']}")
            st.rerun()

    st.subheader("Historial de avisos")
    logs = api_request("GET", "/notificaciones/logs")
    if not logs:
        render_empty_state(
            "Sin avisos enviados",
            "Cuando tengas canales activos y lleguen nuevas coincidencias, aparecerán en este historial.",
        )
        return

    logs_df = pd.DataFrame(logs).rename(
        columns={
            "created_at": "Fecha",
            "channel_type": "Canal",
            "destination": "Destino",
            "status": "Resultado",
            "error_message": "Detalle",
        }
    )
    st.dataframe(
        logs_df[["Fecha", "Canal", "Destino", "Resultado", "Detalle"]],
        hide_index=True,
        width="stretch",
    )


def render_profile() -> None:
    render_page_header("Mi perfil", "Mantén tu búsqueda actualizada para mejorar las recomendaciones.")
    user = api_request("GET", "/auth/me")

    inicial = (user.get("nombre") or user["email"])[0].upper()

    header = st.container(border=True)
    with header:
        col_avatar, col_info, col_state = st.columns([1, 5, 2])
        with col_avatar:
            st.markdown(
                f"""
                <div style="width:64px;height:64px;border-radius:50%;
                background-color:#14532d;color:white;display:flex;
                align-items:center;justify-content:center;font-size:28px;
                font-weight:bold;">{inicial}</div>
                """,
                unsafe_allow_html=True,
            )
        with col_info:
            st.markdown(f"### {user.get('nombre') or 'Sin nombre'}")
            st.caption(user["email"])
            if user.get("puesto_deseado"):
                st.markdown(f"Buscando: **{user['puesto_deseado']}**")
            else:
                st.warning("Aún no has indicado qué puesto buscas. Completa tu perfil para recibir recomendaciones.")
        with col_state:
            st.markdown('<span class="jr-status">Perfil activo</span>', unsafe_allow_html=True)

    st.markdown("### Editar perfil")
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        nombre = col1.text_input("Nombre", value=user.get("nombre") or "")
        nivel_experiencia = col2.selectbox(
            "Nivel de experiencia",
            ["Junior", "Semi-senior", "Senior"],
            index=["Junior", "Semi-senior", "Senior"].index(user.get("nivel_experiencia"))
            if user.get("nivel_experiencia") in ["Junior", "Semi-senior", "Senior"]
            else 0,
        )

        col3, col4, col5 = st.columns(3)
        puesto_deseado = col3.text_input(
            "Puesto que buscas", value=user.get("puesto_deseado") or "", placeholder="Python Developer"
        )
        ubicacion_preferida = col4.text_input(
            "Ubicación preferida", value=user.get("ubicacion_preferida") or "Cualquiera"
        )
        modalidades = ["Cualquiera", "Remoto", "Híbrido", "Presencial"]
        modalidad_actual = user.get("modalidad_preferida") or "Cualquiera"
        modalidad_preferida = col5.selectbox(
            "Modalidad",
            modalidades,
            index=modalidades.index(modalidad_actual) if modalidad_actual in modalidades else 0,
        )

        bio = st.text_area("Sobre ti", value=user.get("bio") or "", placeholder="Breve resumen profesional...")

        guardar = st.form_submit_button("Guardar perfil")

    if guardar:
        try:
            api_request(
                "PATCH",
                "/auth/me",
                json={
                    "nombre": nombre or None,
                    "puesto_deseado": puesto_deseado or None,
                    "ubicacion_preferida": ubicacion_preferida or "Cualquiera",
                    "modalidad_preferida": modalidad_preferida,
                    "nivel_experiencia": nivel_experiencia,
                    "bio": bio or None,
                },
            )
            st.success("Perfil actualizado. Revisa tus ofertas recomendadas.")
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))


def main() -> None:
    apply_global_styles()
    if "access_token" not in st.session_state:
        render_auth()
        return

    section_options = ["Mi perfil", "Ofertas", "Búsquedas", "Avisos", "Actividad"]
    if st.session_state.get("section") not in section_options:
        st.session_state["section"] = "Ofertas"

    st.sidebar.title("JobRadar")
    st.sidebar.caption("Búsqueda de empleo")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("access_token", None)
        st.rerun()

    section = st.sidebar.radio(
        "Sección",
        section_options,
        key="section",
        label_visibility="collapsed",
    )

    if section == "Mi perfil":
        render_profile()
    elif section == "Ofertas":
        render_offers()
    elif section == "Búsquedas":
        render_alerts()
    elif section == "Avisos":
        render_channels()
    elif section == "Actividad":
        render_scraper_runs()


if __name__ == "__main__":
    main()
