"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.pages.controles.control_icaro import control_anual, control_comprobantes


def main() -> None:
    tab_anual, tab_comprobantes = st.tabs(
        ["Control Anual", "Control Comprobantes"], on_change="rerun"
    )

    if tab_anual.open:
        control_anual.render()

    if tab_comprobantes.open:
        control_comprobantes.render()


if __name__ == "__main__":
    main()
