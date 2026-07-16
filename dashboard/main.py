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
    :root {
        --jr-bg: #f6f8fb;
        --jr-surface: #ffffff;
        --jr-surface-muted: #f1f5f9;
        --jr-border: #e2e8f0;
        --jr-text: #111827;
        --jr-muted: #64748b;
        --jr-green: #10b981;
        --jr-green-dark: #047857;
        --jr-green-soft: #dcfce7;
        --jr-sidebar: #111827;
        --jr-sidebar-soft: #1f2937;
        --jr-danger: #ef4444;
    }
    .stApp {
        background: var(--jr-bg);
        color: var(--jr-text);
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2.25rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3, h4, h5, h6, p, label, span {
        letter-spacing: 0;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #0f172a 100%);
        border-right: 1px solid #1f2937;
    }
    section[data-testid="stSidebar"] h1 {
        color: var(--jr-green);
        font-size: 1.35rem;
        letter-spacing: 0;
    }
    section[data-testid="stSidebar"] p {
        color: #cbd5e1;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] span {
        color: #e5e7eb;
    }
    section[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.7rem;
    }
    section[data-testid="stSidebar"] button {
        background: transparent;
        border: 1px solid #334155;
        color: #f8fafc;
        justify-content: flex-start;
        min-height: 2.65rem;
        width: 100%;
    }
    section[data-testid="stSidebar"] button:hover {
        background: rgba(16, 185, 129, 0.12);
        border-color: var(--jr-green);
        color: #d1d5db;
    }
    section[data-testid="stSidebar"] hr {
        border-color: #1f2937;
        margin: 1.25rem 0;
    }
    .jr-sidebar-brand {
        padding: 1.35rem 0 0.6rem;
    }
    .jr-sidebar-brand-title {
        color: var(--jr-green);
        font-size: 1.45rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .jr-sidebar-brand-subtitle,
    .jr-sidebar-section {
        color: #94a3b8;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .jr-sidebar-user {
        align-items: center;
        background: #1f2937;
        border: 1px solid #263244;
        border-radius: 8px;
        display: flex;
        gap: 0.75rem;
        margin: 0.8rem 0 1.1rem;
        padding: 0.78rem;
    }
    .jr-sidebar-avatar {
        align-items: center;
        background: var(--jr-green);
        border-radius: 999px;
        color: #ffffff;
        display: flex;
        font-weight: 800;
        height: 2.4rem;
        justify-content: center;
        min-width: 2.4rem;
        width: 2.4rem;
    }
    .jr-sidebar-user-name {
        color: #ffffff;
        font-size: 0.9rem;
        font-weight: 800;
        line-height: 1.2;
    }
    .jr-sidebar-user-role {
        color: #cbd5e1;
        font-size: 0.76rem;
        line-height: 1.25;
        margin-top: 0.1rem;
    }
    .jr-nav-current {
        border: 1px solid transparent;
        border-radius: 8px;
        color: #d1d5db;
        display: block;
        font-size: 0.92rem;
        font-weight: 700;
        margin: 0.32rem 0;
        padding: 0.72rem 0.75rem;
        text-decoration: none;
    }
    .jr-nav-current {
        background: rgba(16, 185, 129, 0.16);
        border-color: var(--jr-green);
        color: #d1d5db;
    }
    .jr-main-shell {
        max-width: 980px;
        margin: 0 auto;
    }
    div[data-testid="stMetric"] {
        background: var(--jr-surface);
        border: 1px solid var(--jr-border);
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
        color: var(--jr-text);
        min-height: 5.4rem;
        padding: 0.95rem 1rem 1.05rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"],
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        color: var(--jr-muted);
        font-size: 0.82rem;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"],
    div[data-testid="stMetric"] [data-testid="stMetricValue"] div {
        color: var(--jr-text);
        font-size: 1.75rem;
        font-weight: 500;
    }
    div[data-testid="stTextInput"] input,
    div[data-testid="stTextArea"] textarea,
    div[data-baseweb="select"] > div {
        background-color: var(--jr-surface-muted);
        border-color: transparent;
        color: var(--jr-text);
    }
    div[data-testid="stTextInput"] input::placeholder,
    div[data-testid="stTextArea"] textarea::placeholder {
        color: var(--jr-muted);
        opacity: 1;
    }
    div[data-testid="stForm"],
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: var(--jr-surface);
        border-color: var(--jr-border);
        border-radius: 8px;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .jr-header {
        border-bottom: 1px solid var(--jr-border);
        margin-bottom: 1.25rem;
        padding-bottom: 1rem;
    }
    .jr-header h2 {
        color: var(--jr-text);
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.15rem;
    }
    .jr-muted {
        color: var(--jr-muted);
        font-size: 0.95rem;
    }
    .jr-empty {
        background: var(--jr-surface);
        border: 1px dashed #cbd5e1;
        border-radius: 8px;
        padding: 1.25rem;
        margin-top: 1rem;
    }
    .jr-kicker {
        color: var(--jr-green-dark);
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: uppercase;
    }
    .jr-card-title {
        color: var(--jr-text);
        font-size: 1.08rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }
    .jr-chip {
        display: inline-block;
        border: 1px solid #cbd5e1;
        border-radius: 999px;
        color: #475569;
        font-size: 0.8rem;
        margin: 0.15rem 0.2rem 0.15rem 0;
        padding: 0.18rem 0.55rem;
    }
    .jr-status {
        background: var(--jr-green-soft);
        border: 1px solid #bbf7d0;
        border-radius: 999px;
        color: #047857;
        display: inline-block;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 0.22rem 0.65rem;
    }
    .jr-status-marker {
        align-items: center;
        display: inline-flex;
        gap: 0.35rem;
        margin: 0.25rem 0 0.45rem;
    }
    .jr-status-marker-label {
        color: var(--jr-muted);
        font-size: 0.8rem;
        font-weight: 700;
    }
    .jr-status-aplicado {
        background: #dbeafe;
        border-color: #bfdbfe;
        color: #1d4ed8;
    }
    .jr-status-descartado {
        background: #fee2e2;
        border-color: #fecaca;
        color: #b91c1c;
    }
    .jr-insight-card {
        background: var(--jr-surface);
        border: 1px solid var(--jr-border);
        border-radius: 8px;
        min-height: 8rem;
        padding: 1rem;
    }
    .jr-insight-title {
        color: var(--jr-text);
        font-size: 0.95rem;
        font-weight: 800;
        margin-bottom: 0.35rem;
    }
    .jr-check-item {
        align-items: flex-start;
        display: flex;
        gap: 0.55rem;
        margin: 0.45rem 0;
    }
    .jr-check-dot {
        align-items: center;
        border-radius: 999px;
        display: flex;
        font-size: 0.7rem;
        font-weight: 800;
        height: 1.1rem;
        justify-content: center;
        margin-top: 0.12rem;
        min-width: 1.1rem;
        width: 1.1rem;
    }
    .jr-check-ok {
        background: var(--jr-green-soft);
        color: #047857;
    }
    .jr-check-missing {
        background: #fee2e2;
        color: #b91c1c;
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


def format_notification_status(status: str | None) -> str:
    labels = {
        "sent": "Enviado",
        "simulated": "Simulado",
        "failed": "Falló",
        None: "Sin envíos",
    }
    return labels.get(status, status or "Sin envíos")


def truncate_text(value: str | None, limit: int = 260) -> str:
    if not value:
        return ""
    clean_value = " ".join(str(value).split())
    if len(clean_value) <= limit:
        return clean_value
    return clean_value[: limit - 3].rstrip() + "..."


def safe_html(value: object, fallback: str = "") -> str:
    return html.escape(str(value or fallback), quote=True)


def sync_section_from_query(section_options: list[str]) -> None:
    query_section = st.query_params.get("section")
    if isinstance(query_section, list):
        query_section = query_section[0] if query_section else None
    if query_section in section_options:
        st.session_state["section"] = query_section


def render_sidebar(user: dict, section_options: list[str]) -> None:
    current_section = st.session_state.get("section", "Ofertas")
    user_name = user.get("nombre") or user.get("email", "Usuario").split("@")[0]
    desired_role = user.get("puesto_deseado") or "Sin puesto definido"
    initial = safe_html(user_name[:1].upper(), "U")

    st.sidebar.markdown(
        f"""
        <div class="jr-sidebar-brand">
            <div class="jr-sidebar-brand-title">JobRadar</div>
            <div class="jr-sidebar-brand-subtitle">Tu radar de empleo tech</div>
        </div>
        <div class="jr-sidebar-user">
            <div class="jr-sidebar-avatar">{initial}</div>
            <div>
                <div class="jr-sidebar-user-name">{safe_html(user_name)}</div>
                <div class="jr-sidebar-user-role">{safe_html(desired_role)}</div>
            </div>
        </div>
        <div class="jr-sidebar-section">Navegación</div>
        """,
        unsafe_allow_html=True,
    )

    icons = {
        "Ofertas": "▣",
        "Mi CV": "◧",
        "Búsquedas": "⌕",
        "Avisos": "◖",
        "Actividad": "▥",
        "Mi perfil": "◉",
    }
    for option in section_options:
        label = f"{icons.get(option, '•')} {option}"
        if option == current_section:
            st.sidebar.markdown(
                f'<div class="jr-nav-current">{safe_html(label)}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.sidebar.button(
                label,
                key=f"nav_{option}",
                on_click=set_active_section,
                args=(option,),
                use_container_width=True,
            )
    st.sidebar.markdown("<hr />", unsafe_allow_html=True)

    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.pop("access_token", None)
        st.query_params.clear()
        st.rerun()


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


def load_offers(limit: int = 50) -> pd.DataFrame:
    offers = api_request("GET", "/ofertas/", params={"limit": limit})
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
        # La API guarda valores tecnicos (p. ej. ``guardado``), mientras la
        # interfaz muestra etiquetas (``Me interesa``). Normalizar ambos lados
        # evita que espacios, mayusculas o valores nulos oculten ofertas
        # correctamente guardadas.
        estados_normalizados = (
            filtered["estado"]
            .fillna("guardado")
            .astype(str)
            .str.strip()
            .str.lower()
        )
        estado_seleccionado = STATUS_VALUES[estado].strip().lower()
        filtered = filtered[estados_normalizados == estado_seleccionado]

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
            "Todavía no tienes ofertas recomendadas",
            "Completa tu perfil o crea una búsqueda. JobRadar traerá oportunidades y te avisará cuando encuentre coincidencias.",
        )
        col_profile, col_alert = st.columns(2)
        col_profile.button("Completar perfil", on_click=set_active_section, args=("Mi perfil",))
        col_alert.button("Crear búsqueda", on_click=set_active_section, args=("Búsquedas",))
        return

    status_counts = (
        offers["estado"]
        .fillna("guardado")
        .astype(str)
        .str.strip()
        .str.lower()
        .value_counts()
        .to_dict()
    )
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
        status_class = f"jr-status-{safe_html(current_status)}"
        with st.container(border=True):
            top_col, status_col = st.columns([5, 2])
            top_col.markdown(
                f"""
                <div class="jr-kicker">{safe_html(offer.get("empresa"), "Empresa confidencial")}</div>
                <div class="jr-card-title">{safe_html(offer.get("titulo"), "Oferta sin título")}</div>
                <div class="jr-status-marker">
                    <span class="jr-status-marker-label">Marcada como</span>
                    <span class="jr-status {status_class}">{safe_html(current_label)}</span>
                </div>
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
                f'<span class="jr-status {status_class}">{format_status(current_status)}</span>',
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
    render_page_header("Búsquedas guardadas", "Dile a JobRadar qué ofertas quieres encontrar.")
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
            "Aún no tienes búsquedas guardadas",
            "Crea tu primera búsqueda con un puesto, ubicación y modalidad. Si hay coincidencias, JobRadar las guardará y te enviará avisos por tus canales activos.",
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
    render_page_header("Avisos", "Conecta Telegram para recibir nuevas oportunidades.")
    channels = api_request("GET", "/notificaciones/canales")
    bot_url = f"https://t.me/{TELEGRAM_BOT_USERNAME}"
    created_message = st.session_state.pop("channel_created_message", None)
    if created_message:
        st.success(created_message)

    st.markdown("### Telegram")
    st.info(
        "Abre el bot oficial de JobRadar, pulsa Start y vuelve aquí para conectar tu cuenta. "
        "No necesitas copiar tokens ni configurar nada técnico."
    )
    col_bot, col_detect = st.columns([2, 1])
    col_bot.link_button(f"Abrir @{TELEGRAM_BOT_USERNAME}", bot_url)
    if col_detect.button("Detectar mi chat ID"):
        try:
            result = api_request("GET", "/notificaciones/telegram/chats")
            st.session_state["telegram_chats"] = result["chats"]
            if result["chats"]:
                st.success("Chat detectado. Selecciona tu Telegram y agrega el aviso.")
            else:
                st.warning("No encontré chats recientes. Abre el bot, pulsa Start y vuelve a detectar.")
        except RuntimeError as error:
            st.error(str(error))

    with st.form("create_channel_form"):
        channel_type = "telegram"
        detected_chats = st.session_state.get("telegram_chats", [])

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

        submitted = st.form_submit_button("Agregar aviso")
    if submitted:
        if not destination.strip():
            st.error("Falta seleccionar o ingresar el destino del aviso.")
        else:
            try:
                api_request(
                    "POST",
                    "/notificaciones/canales",
                    json={
                        "type": channel_type,
                        "destination": destination,
                        "is_active": True,
                    },
                )
                st.session_state["channel_created_message"] = (
                    "Aviso de Telegram conectado. Usa Probar para enviar un mensaje."
                    if channel_type == "telegram"
                    else "Aviso conectado."
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
            "No tienes avisos activos",
            "Conecta Telegram para recibir ofertas aunque no tengas el dashboard abierto. Después de agregarlo, usa Enviar prueba para confirmar que llega.",
        )
        return

    for channel in channels:
        with st.container(border=True):
            info_col, action_col = st.columns([3, 2])
            info_col.markdown(f"**{channel['type'].title()}**")
            info_col.caption(channel["destination"])
            info_col.write(
                f"Último aviso: {format_notification_status(channel.get('last_notification_status'))}"
            )
            if channel.get("last_notification_at"):
                info_col.caption(f"Registrado: {channel['last_notification_at']}")
            if channel.get("last_notification_error"):
                info_col.error(channel["last_notification_error"])

            active = action_col.toggle(
                "Activo",
                value=channel["is_active"],
                key=f"channel_{channel['id']}",
            )
            if active != channel["is_active"]:
                api_request(
                    "PATCH",
                    f"/notificaciones/canales/{channel['id']}",
                    json={"is_active": active},
                )
                st.rerun()

            if action_col.button(
                "Enviar prueba",
                key=f"test_channel_{channel['id']}",
                use_container_width=True,
            ):
                try:
                    api_request("POST", f"/notificaciones/canales/{channel['id']}/test")
                    st.success("Prueba enviada. Revisa el canal o el historial de avisos.")
                    st.rerun()
                except RuntimeError as error:
                    st.error(str(error))
            if action_col.button(
                "Eliminar aviso",
                key=f"delete_channel_{channel['id']}",
                use_container_width=True,
            ):
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


def render_check_item(done: bool, label: str, detail: str) -> None:
    dot_class = "jr-check-ok" if done else "jr-check-missing"
    symbol = "✓" if done else "!"
    st.markdown(
        f"""
        <div class="jr-check-item">
            <div class="jr-check-dot {dot_class}">{symbol}</div>
            <div>
                <div class="jr-insight-title">{safe_html(label)}</div>
                <div class="jr-muted">{safe_html(detail)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_cv() -> None:
    render_page_header(
        "Mi CV",
        "Prepara tu candidatura con un perfil claro, consistente y alineado a tus ofertas objetivo.",
    )
    user = api_request("GET", "/auth/me")
    try:
        offers = load_offers(limit=100)
    except RuntimeError:
        offers = pd.DataFrame()

    desired_role = user.get("puesto_deseado") or ""
    location = user.get("ubicacion_preferida") or "Cualquiera"
    modality = user.get("modalidad_preferida") or "Cualquiera"
    level = user.get("nivel_experiencia") or ""
    bio = user.get("bio") or ""

    total_offers = len(offers)
    saved = 0
    applied = 0
    dismissed = 0
    if not offers.empty and "estado" in offers:
        normalized_status = offers["estado"].fillna("guardado").astype(str).str.strip().str.lower()
        saved = int((normalized_status == "guardado").sum())
        applied = int((normalized_status == "aplicado").sum())
        dismissed = int((normalized_status == "descartado").sum())

    readiness_checks = [
        bool(desired_role),
        bool(level),
        bool(bio and len(bio.strip()) >= 80),
        applied > 0,
    ]
    readiness_score = round(sum(readiness_checks) / len(readiness_checks) * 100)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total ofertas", total_offers)
    metric_cols[1].metric("Me interesa", saved)
    metric_cols[2].metric("Ya apliqué", applied)
    metric_cols[3].metric("No encaja", dismissed)

    summary_col, checklist_col = st.columns([1.15, 1], gap="large")
    with summary_col:
        st.markdown(
            f"""
            <div class="jr-insight-card">
                <div class="jr-kicker">Resumen profesional</div>
                <div class="jr-card-title">{safe_html(desired_role, "Puesto objetivo pendiente")}</div>
                <span class="jr-status">Preparación {readiness_score}%</span>
                <div class="jr-muted">
                    {safe_html(bio, "Agrega un resumen de 3 a 5 líneas: especialidad, años de experiencia, stack principal y tipo de producto donde aportas valor.")}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("### Preferencias de búsqueda")
        st.markdown(
            f"""
            <span class="jr-chip">{safe_html(level, "Nivel pendiente")}</span>
            <span class="jr-chip">{safe_html(location)}</span>
            <span class="jr-chip">{safe_html(modality)}</span>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Enfoque recomendado")
        st.markdown(
            """
            - Personaliza el resumen para el rol objetivo.
            - Prioriza logros medibles en tus últimas experiencias.
            - Mantén el stack técnico alineado a las ofertas guardadas.
            - Revisa cada aplicación después de enviarla.
            """
        )

    with checklist_col:
        st.markdown("### Checklist de candidatura")
        render_check_item(
            bool(desired_role),
            "Puesto objetivo",
            "Define el cargo principal para que las recomendaciones y el CV hablen el mismo idioma.",
        )
        render_check_item(
            bool(level),
            "Nivel de experiencia",
            "Ayuda a filtrar ofertas y a presentar expectativas realistas.",
        )
        render_check_item(
            bool(bio and len(bio.strip()) >= 80),
            "Resumen profesional",
            "Un buen resumen evita que el perfil parezca vacío ante reclutadores.",
        )
        render_check_item(
            applied > 0,
            "Primeras aplicaciones",
            "Marca ofertas como aplicadas para medir avance real, no solo intención.",
        )

        st.button("Editar datos base", on_click=set_active_section, args=("Mi perfil",), use_container_width=True)


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

    section_options = ["Ofertas", "Mi CV", "Búsquedas", "Avisos", "Actividad", "Mi perfil"]
    sync_section_from_query(section_options)
    if st.session_state.get("section") not in section_options:
        st.session_state["section"] = "Ofertas"

    current_user = api_request("GET", "/auth/me")
    render_sidebar(current_user, section_options)
    section = st.session_state["section"]

    if section == "Ofertas":
        render_offers()
    elif section == "Mi CV":
        render_cv()
    elif section == "Búsquedas":
        render_alerts()
    elif section == "Avisos":
        render_channels()
    elif section == "Actividad":
        render_scraper_runs()
    elif section == "Mi perfil":
        render_profile()


if __name__ == "__main__":
    main()
