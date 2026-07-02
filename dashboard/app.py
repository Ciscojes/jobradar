import os
from typing import Any

import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")


st.set_page_config(
    page_title="JobRadar Dashboard",
    layout="wide",
)


def get_token() -> str | None:
    return st.session_state.get("access_token")


def auth_headers() -> dict[str, str]:
    token = get_token()
    return {"Authorization": f"Bearer {token}"} if token else {}


def api_request(method: str, path: str, **kwargs: Any) -> Any:
    headers = {**auth_headers(), **kwargs.pop("headers", {})}
    response = requests.request(
        method,
        f"{API_URL}{path}",
        headers=headers,
        timeout=15,
        **kwargs,
    )

    if response.status_code == 401:
        st.session_state.pop("access_token", None)
        st.error("Sesion expirada. Inicia sesion de nuevo.")
        st.stop()

    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(detail)

    if response.status_code == 204:
        return None
    return response.json()


def render_login() -> None:
    st.subheader("Iniciar sesion")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Contrasena", type="password")
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
        except requests.RequestException as error:
            st.error(f"No se pudo conectar con la API: {error}")


def render_register() -> None:
    st.subheader("Registro")
    with st.form("register_form"):
        nombre = st.text_input("Nombre")
        email = st.text_input("Email", key="register_email")
        password = st.text_input("Contrasena", type="password", key="register_password")
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
        except requests.RequestException as error:
            st.error(f"No se pudo conectar con la API: {error}")


def render_auth_screen() -> None:
    st.title("JobRadar")
    st.caption("Gestiona tus alertas de empleo")

    auth_screen = st.radio("Acceso", ["Login", "Registro"], horizontal=True)
    if auth_screen == "Login":
        render_login()
    else:
        render_register()


def get_current_user() -> dict[str, Any] | None:
    try:
        return api_request("GET", "/auth/me")
    except RuntimeError as error:
        st.error(str(error))
    except requests.RequestException as error:
        st.error(f"No se pudo conectar con la API: {error}")
    return None


def alert_payload(
    termino: str,
    ubicacion: str,
    categoria: str | None,
    salario_minimo: int | None,
    modalidad: str,
    fuente: str,
    activo: bool,
) -> dict[str, Any]:
    return {
        "termino": termino.strip(),
        "ubicacion": ubicacion.strip() or "Cualquiera",
        "categoria": categoria.strip() if categoria else None,
        "salario_minimo": salario_minimo,
        "modalidad": modalidad.strip() or "Cualquiera",
        "fuente": fuente.strip() or "Cualquiera",
        "activo": activo,
    }


def render_create_alert() -> None:
    st.subheader("Crear alerta")
    with st.form("create_alert_form"):
        col1, col2, col3 = st.columns(3)
        termino = col1.text_input("Keyword")
        ubicacion = col2.text_input("Provincia", value="Cualquiera")
        categoria = col3.text_input("Categoria")

        col4, col5, col6 = st.columns(3)
        salario_minimo = col4.number_input("Salario minimo", min_value=0, step=1000)
        modalidad = col5.text_input("Modalidad", value="Cualquiera")
        fuente = col6.text_input("Fuente", value="Cualquiera")

        activo = st.checkbox("Activa", value=True)
        submitted = st.form_submit_button("Crear alerta")

    if submitted:
        if not termino.strip():
            st.error("Keyword es obligatorio.")
            return
        try:
            api_request(
                "POST",
                "/alertas/",
                json=alert_payload(
                    termino,
                    ubicacion,
                    categoria,
                    salario_minimo or None,
                    modalidad,
                    fuente,
                    activo,
                ),
            )
            st.success("Alerta creada.")
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))
        except requests.RequestException as error:
            st.error(f"No se pudo conectar con la API: {error}")


def render_alert_list(alerts: list[dict[str, Any]]) -> int | None:
    st.subheader("Mis alertas")
    if not alerts:
        st.info("No tienes alertas configuradas.")
        return None

    for alert in alerts:
        status = "activa" if alert.get("activo") else "inactiva"
        st.write(
            f"#{alert['id']} - {alert['termino']} - "
            f"{alert.get('ubicacion') or 'Cualquiera'} - {status}"
        )

    options = {f"#{alert['id']} - {alert['termino']}": alert["id"] for alert in alerts}
    selected_label = st.selectbox("Selecciona una alerta", list(options.keys()))
    return options[selected_label]


def render_alert_detail(alerta_id: int) -> None:
    try:
        alert = api_request("GET", f"/alertas/{alerta_id}")
    except RuntimeError as error:
        st.error(str(error))
        return
    except requests.RequestException as error:
        st.error(f"No se pudo conectar con la API: {error}")
        return

    st.subheader("Detalle de alerta")
    st.caption(f"ID {alert['id']} - Usuario {alert['user_id']}")

    with st.form(f"edit_alert_form_{alerta_id}"):
        col1, col2, col3 = st.columns(3)
        termino = col1.text_input("Keyword", value=alert.get("termino") or "")
        ubicacion = col2.text_input("Provincia", value=alert.get("ubicacion") or "Cualquiera")
        categoria = col3.text_input("Categoria", value=alert.get("categoria") or "")

        col4, col5, col6 = st.columns(3)
        salario_minimo = col4.number_input(
            "Salario minimo",
            min_value=0,
            step=1000,
            value=alert.get("salario_minimo") or 0,
        )
        modalidad = col5.text_input("Modalidad", value=alert.get("modalidad") or "Cualquiera")
        fuente = col6.text_input("Fuente", value=alert.get("fuente") or "Cualquiera")

        activo = st.checkbox("Activa", value=bool(alert.get("activo")))
        submitted = st.form_submit_button("Guardar cambios")

    if submitted:
        if not termino.strip():
            st.error("Keyword es obligatorio.")
            return
        try:
            api_request(
                "PUT",
                f"/alertas/{alerta_id}",
                json=alert_payload(
                    termino,
                    ubicacion,
                    categoria,
                    salario_minimo or None,
                    modalidad,
                    fuente,
                    activo,
                ),
            )
            st.success("Alerta actualizada.")
            st.rerun()
        except RuntimeError as error:
            st.error(str(error))
        except requests.RequestException as error:
            st.error(f"No se pudo conectar con la API: {error}")

    col_active, col_inactive, col_delete = st.columns(3)
    if col_active.button("Activar", disabled=bool(alert.get("activo"))):
        update_alert_status(alerta_id, "activar")
    if col_inactive.button("Desactivar", disabled=not bool(alert.get("activo"))):
        update_alert_status(alerta_id, "desactivar")
    if col_delete.button("Eliminar", type="primary"):
        delete_alert(alerta_id)


def update_alert_status(alerta_id: int, action: str) -> None:
    try:
        api_request("PATCH", f"/alertas/{alerta_id}/{action}")
        st.rerun()
    except RuntimeError as error:
        st.error(str(error))
    except requests.RequestException as error:
        st.error(f"No se pudo conectar con la API: {error}")


def delete_alert(alerta_id: int) -> None:
    try:
        api_request("DELETE", f"/alertas/{alerta_id}")
        st.success("Alerta eliminada.")
        st.rerun()
    except RuntimeError as error:
        st.error(str(error))
    except requests.RequestException as error:
        st.error(f"No se pudo conectar con la API: {error}")


def render_alerts_dashboard() -> None:
    try:
        alerts = api_request("GET", "/alertas/")
    except RuntimeError as error:
        st.error(str(error))
        return
    except requests.RequestException as error:
        st.error(f"No se pudo conectar con la API: {error}")
        return

    left, right = st.columns([1, 1])
    with left:
        render_create_alert()
        selected_alert_id = render_alert_list(alerts)
    with right:
        if selected_alert_id is not None:
            render_alert_detail(selected_alert_id)


def render_authenticated_dashboard() -> None:
    user = get_current_user()
    if not user:
        return

    st.title("JobRadar")
    st.caption("Dashboard autenticado")

    col_user, col_logout = st.columns([4, 1])
    col_user.write(f"Usuario: {user['email']}")
    if col_logout.button("Cerrar sesion"):
        st.session_state.pop("access_token", None)
        st.rerun()

    render_alerts_dashboard()


def main() -> None:
    if not get_token():
        render_auth_screen()
        return
    render_authenticated_dashboard()


if __name__ == "__main__":
    main()
