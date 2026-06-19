"""Página Principal: Tablas Auxiliares - SGF."""

import streamlit as st

from src.pages.tablas_auxiliares.sgf import resumen_rend_obras, resumen_rend_prov


def main() -> None:
    tab_resumen_rend_prov, tab_resumen_rend_obras = st.tabs(
        ["Resumen Rend. Prov.", "Resumen Rend. Obras"], on_change="rerun"
    )

    if tab_resumen_rend_prov.open:
        resumen_rend_prov.render()

    if tab_resumen_rend_obras.open:
        resumen_rend_obras.render()


if __name__ == "__main__":
    main()
