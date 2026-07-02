import pandas as pd
import streamlit as st


def _sorted_options(values: pd.Series) -> list[str]:
    clean_values = values.dropna().astype(str)
    return ["Todas"] + sorted(value for value in clean_values.unique() if value)


def render_offer_filters(offers: pd.DataFrame) -> tuple[str, str, str]:
    """Muestra filtros para palabra clave, empresa y ubicacion."""
    st.subheader("Filtros")

    col_keyword, col_empresa, col_ubicacion = st.columns(3)

    with col_keyword:
        keyword = st.text_input(
            "Palabra clave",
            placeholder="Ejemplo: Python, FastAPI, React",
        )

    with col_empresa:
        empresa = st.selectbox(
            "Empresa",
            options=_sorted_options(offers["empresa"]),
        )

    with col_ubicacion:
        ubicacion = st.selectbox(
            "Ubicacion",
            options=_sorted_options(offers["ubicacion"]),
        )

    return keyword.strip(), empresa, ubicacion
