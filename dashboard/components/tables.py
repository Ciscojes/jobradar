import pandas as pd
import streamlit as st


VISIBLE_COLUMNS = [
    "titulo",
    "empresa",
    "ubicacion",
    "modalidad",
    "salario",
    "fuente",
    "estado",
    "fecha_publicacion",
    "enlace",
]


def render_offers_table(offers: pd.DataFrame) -> None:
    """Muestra una tabla de ofertas con enlaces clicables."""
    st.subheader("Ofertas")

    if offers.empty:
        st.warning("No hay ofertas que coincidan con los filtros seleccionados.")
        return

    table_data = offers[VISIBLE_COLUMNS].copy()

    st.dataframe(
        table_data,
        hide_index=True,
        use_container_width=True,
        column_config={
            "titulo": st.column_config.TextColumn("Titulo"),
            "empresa": st.column_config.TextColumn("Empresa"),
            "ubicacion": st.column_config.TextColumn("Ubicacion"),
            "modalidad": st.column_config.TextColumn("Modalidad"),
            "salario": st.column_config.TextColumn("Salario"),
            "fuente": st.column_config.TextColumn("Fuente"),
            "estado": st.column_config.TextColumn("Estado"),
            "fecha_publicacion": st.column_config.TextColumn("Fecha publicacion"),
            "enlace": st.column_config.LinkColumn("Oferta"),
        },
    )
