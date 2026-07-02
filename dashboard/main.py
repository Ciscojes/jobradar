import os

import pandas as pd
import requests
import streamlit as st

from components.filters import render_offer_filters
from components.metrics import render_offer_metrics
from components.tables import render_offers_table


API_BASE_URL = os.getenv("JOBRADAR_API_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(
    page_title="jobradar Dashboard",
    layout="wide",
)


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
    st.title("jobradar")
    st.caption("Accede para gestionar tus alertas y ofertas")

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
            nombre = st.text_input("Nombre")
            email = st.text_input("Email", key="register_email")
            password = st.text_input("Contraseña", type="password", key="register_password")
            submitted = st.form_submit_button("Crear cuenta")
        if submitted:
            try:
                api_request(
                    "POST",
                    "/auth/register",
                    json={"nombre": nombre, "email": email, "password": password},
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
    st.subheader("Búsqueda de prueba")
    with st.form("sync_form"):
        query = st.text_input("Término de búsqueda", value="python")
        submitted = st.form_submit_button("Ejecutar scraper")
    if submitted:
        try:
            result = api_request(
                "POST",
                "/scraper/sync",
                params={"query": query.strip() or "python"},
            )
            st.success(result["message"])
        except RuntimeError as error:
            st.error(str(error))

    offers = load_offers()
    if offers.empty:
        render_offer_metrics(offers)
        st.info("Todavía no hay ofertas que coincidan con tus alertas.")
        return

    keyword, empresa, ubicacion = render_offer_filters(offers)
    filtered_offers = apply_filters(offers, keyword, empresa, ubicacion)

    render_offer_metrics(filtered_offers)
    render_offers_table(filtered_offers)

    st.subheader("Estados")
    for offer in filtered_offers.to_dict("records"):
        cols = st.columns([4, 2, 2])
        cols[0].write(f"{offer['titulo']} - {offer['empresa']}")
        status_options = ["guardado", "aplicado", "descartado"]
        current_status = offer["estado"] if offer["estado"] in status_options else "guardado"
        new_status = cols[1].selectbox(
            "Estado",
            status_options,
            index=status_options.index(current_status),
            key=f"offer_status_{offer['id']}_{offer.get('user_oferta_id')}",
            label_visibility="collapsed",
        )
        if cols[2].button("Guardar", key=f"save_offer_status_{offer['id']}_{offer.get('user_oferta_id')}"):
            try:
                api_request(
                    "PATCH",
                    f"/ofertas/{offer['id']}/estado",
                    json={"estado": new_status},
                )
                st.rerun()
            except RuntimeError as error:
                st.error(str(error))


def render_scraper_runs() -> None:
    st.subheader("Ejecuciones del scraper")
    try:
        runs = api_request("GET", "/scraper/runs")
    except RuntimeError as error:
        st.error(str(error))
        return

    if not runs:
        st.info("Todavía no hay ejecuciones registradas.")
        return

    st.dataframe(
        pd.DataFrame(runs)[
            [
                "started_at",
                "finished_at",
                "query",
                "status",
                "offers_found",
                "new_offers",
                "new_matches",
                "error_message",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )


def render_alerts() -> None:
    st.subheader("Alertas")
    alerts = api_request("GET", "/alertas/")

    with st.form("create_alert_form"):
        col_term, col_location, col_modality = st.columns(3)
        termino = col_term.text_input("Término", placeholder="python, react, data")
        ubicacion = col_location.text_input("Ubicación", value="Cualquiera")
        modalidad = col_modality.text_input("Modalidad", value="Cualquiera")
        submitted = st.form_submit_button("Crear alerta")
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
        st.info("No tienes alertas configuradas.")
        return

    for alert in alerts:
        with st.form(f"edit_alert_{alert['id']}"):
            cols = st.columns([3, 2, 2, 1, 1])
            termino = cols[0].text_input(
                "Término",
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
    st.subheader("Canales")
    channels = api_request("GET", "/notificaciones/canales")

    with st.form("create_channel_form"):
        col_type, col_destination = st.columns([1, 3])
        channel_type = col_type.selectbox("Tipo", ["telegram", "email"])
        destination = col_destination.text_input("Destino", placeholder="chat_id o email")
        submitted = st.form_submit_button("Agregar canal")
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
        st.info("No tienes canales de notificación.")
        return

    for channel in channels:
        cols = st.columns([1, 3, 1, 1, 1])
        cols[0].write(channel["type"])
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

    st.subheader("Historial")
    logs = api_request("GET", "/notificaciones/logs")
    if not logs:
        st.info("Todavía no hay notificaciones registradas.")
        return

    st.dataframe(
        pd.DataFrame(logs)[
            ["created_at", "channel_type", "destination", "status", "error_message"]
        ],
        hide_index=True,
        use_container_width=True,
    )


def main() -> None:
    if "access_token" not in st.session_state:
        render_auth()
        return

    st.title("jobradar")
    st.caption("Dashboard personal de búsqueda de empleo")

    if st.sidebar.button("Cerrar sesión"):
        st.session_state.pop("access_token", None)
        st.rerun()

    offers_tab, alerts_tab, channels_tab, scraper_tab = st.tabs(
        ["Ofertas", "Alertas", "Canales", "Scraper"]
    )
    with offers_tab:
        render_offers()
    with alerts_tab:
        render_alerts()
    with channels_tab:
        render_channels()
    with scraper_tab:
        render_scraper_runs()


if __name__ == "__main__":
    main()
