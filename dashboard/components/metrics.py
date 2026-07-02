import pandas as pd
import streamlit as st


def render_offer_metrics(offers: pd.DataFrame) -> None:
    """Muestra metricas principales del listado de ofertas."""
    total_offers = len(offers)
    total_companies = offers["empresa"].nunique() if not offers.empty else 0
    total_locations = offers["ubicacion"].nunique() if not offers.empty else 0

    col_offers, col_companies, col_locations = st.columns(3)

    col_offers.metric("Total de ofertas", total_offers)
    col_companies.metric("Total de empresas", total_companies)
    col_locations.metric("Total de ubicaciones", total_locations)
