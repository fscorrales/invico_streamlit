"""Página Principal: Tablas Auxiliares - ICARO."""

import streamlit as st

from src.pages.tablas_auxiliares.icaro import carga, estructuras


def main() -> None:
    tab_carga, tab_estructura = st.tabs(["Carga", "Estructura"])

    with tab_carga:
        carga.render()

    with tab_estructura:
        estructuras.render()


if __name__ == "__main__":
    main()
