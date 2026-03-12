"""Página Principal: Tablas Auxiliares - SIIF."""

import streamlit as st

from src.pages.tablas_auxiliares import siif_rf602, siif_rf610


def main() -> None:
    # Sidebar menu logic
    st.sidebar.markdown("### Menú SIIF")
    
    # We use radio buttons as they match the list style closely
    menu_selection = st.sidebar.radio(
        "Reportes Disponibles",
        options=["RF602", "RF610"],
        label_visibility="collapsed",
    )
    
    # Divider for visual separation if needed
    st.sidebar.divider()
    
    # Render selected sub-page
    if menu_selection == "RF602":
        siif_rf602.render()
    elif menu_selection == "RF610":
        siif_rf610.render()


if __name__ == "__main__":
    main()
