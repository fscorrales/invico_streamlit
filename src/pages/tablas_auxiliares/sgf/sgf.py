"""Página Principal: Tablas Auxiliares - SGF."""

import streamlit as st

from src.pages.tablas_auxiliares.sgf import ctas_ctes, resumen_rend_prov


def main() -> None:
    tab_resumen_rend_prov, resumen_rend_obras = st.tabs(
        ["Resumen Rend. Prov.", "Resumen Rend. Obras"], on_change="rerun"
    )

    if tab_resumen_rend_prov.open:
        resumen_rend_prov.render()

    if resumen_rend_obras.open:
        ctas_ctes.render()


if __name__ == "__main__":
    main()
