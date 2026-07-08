import os

import pandas as pd
import requests
import streamlit as st

from components.filters import render_offer_filters
from components.metrics import render_offer_metrics


API_BASE_URL = os.getenv("JOBRADAR_API_URL", "http://localhost:8000").rstrip("/")


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


def render_page_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"## {title}")
    if subtitle:
        st.caption(subtitle)


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
    st.title("JobRadar")
    st.caption("Tus ofertas recomendadas en un solo lugar")

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

    return filtered


def render_offers() -> None:
    render_page_header(
        "Ofertas recomendadas",
        "Revisa oportunidades que coinciden con tu perfil y guarda el estado de cada una.",
    )

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
        st.info("Todavía no hay ofertas guardadas para tu búsqueda.")
        return

    keyword, empresa, ubicacion = render_offer_filters(offers)
    filtered_offers = apply_filters(offers, keyword, empresa, ubicacion)

    render_offer_metrics(filtered_offers)

    for offer in filtered_offers.head(50).to_dict("records"):
        current_status = offer["estado"] if offer["estado"] in STATUS_LABELS else "guardado"
        current_label = STATUS_LABELS[current_status]
        with st.container(border=True):
            top_col, status_col = st.columns([5, 2])
            top_col.markdown(f"### {offer['titulo']}")
            top_col.caption(
                " · ".join(
                    value
                    for value in [
                        str(offer.get("empresa") or "Empresa confidencial"),
                        str(offer.get("ubicacion") or "Ubicación no indicada"),
                        str(offer.get("modalidad") or "Modalidad no indicada"),
                    ]
                    if value
                )
            )
            if offer.get("salario") and offer["salario"] != "No especificado":
                top_col.write(f"Salario: {offer['salario']}")
            if offer.get("descripcion"):
                top_col.write(str(offer["descripcion"])[:260] + ("..." if len(str(offer["descripcion"])) > 260 else ""))
            if offer.get("enlace"):
                top_col.link_button("Ver oferta", offer["enlace"])

            new_label = status_col.selectbox(
                "Estado",
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
        st.info("Todavía no hay actividad registrada.")
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
        st.info("No tienes búsquedas guardadas.")
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

    with st.form("create_channel_form"):
        col_type, col_destination = st.columns([1, 3])
        channel_type_label = col_type.selectbox("Canal", ["Telegram", "Email"])
        channel_type = channel_type_label.lower()
        destination = col_destination.text_input("Destino", placeholder="Chat ID o email")
        submitted = st.form_submit_button("Agregar aviso")
    if submitted:
        try:
            api_request(
                "POST",
                "/notificaciones/canales",
                json={"type": channel_type, "destination": destination, "is_active": True},
            )
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))

    if not channels:
        st.info("No tienes avisos configurados.")
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
        st.info("Todavía no hay avisos enviados.")
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
        col_avatar, col_info = st.columns([1, 6])
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
    if "access_token" not in st.session_state:
        render_auth()
        return

    st.sidebar.title("JobRadar")
    st.sidebar.caption("Búsqueda de empleo")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("access_token", None)
        st.rerun()

    section = st.sidebar.radio(
        "Sección",
        ["Mi perfil", "Ofertas", "Búsquedas", "Avisos", "Actividad"],
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
