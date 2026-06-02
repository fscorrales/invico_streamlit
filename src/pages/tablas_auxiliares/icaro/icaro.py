"""Página Principal: Tablas Auxiliares - ICARO."""

import streamlit as st

from src.pages.tablas_auxiliares.icaro import carga, estructuras, obras


def main() -> None:
    tab_carga, tab_estructura, tab_obras = st.tabs(["Carga", "Estructura", "Obras"])

    with tab_carga:
        carga.render()

    with tab_estructura:
        estructuras.render()

    with tab_obras:
        obras.render()


if __name__ == "__main__":
    main()
