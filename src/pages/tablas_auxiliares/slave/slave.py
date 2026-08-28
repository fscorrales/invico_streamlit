"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.pages.tablas_auxiliares.slave import factureros, honorarios


def main() -> None:
    tab_honorarios_prestadores, tab_factureros = st.tabs(
        ["Honorarios SIIF", "Factureros"], on_change="rerun"
    )

    if tab_honorarios_prestadores.open:
        honorarios.render()

    if tab_factureros.open:
        factureros.render()


if __name__ == "__main__":
    main()
