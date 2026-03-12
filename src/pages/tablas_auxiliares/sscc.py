"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.pages.tablas_auxiliares import sscc_banco_invico


def main() -> None:
    # Sidebar menu logic
    st.sidebar.markdown("### Menú SSCC")
    
    menu_selection = st.sidebar.radio(
        "Reportes Disponibles",
        options=["Banco INVICO"],
        label_visibility="collapsed",
    )
    

    # Render selected sub-page
    if menu_selection == "Banco INVICO":
        sscc_banco_invico.render()


if __name__ == "__main__":
    main()
