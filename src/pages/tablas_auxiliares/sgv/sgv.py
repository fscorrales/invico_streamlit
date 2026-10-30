"""Página Principal: Tablas Auxiliares - SGV."""

import streamlit as st

from src.pages.tablas_auxiliares.sgv import saldos_barrios_evolucion


def main() -> None:

    (tab_saldos_barrios_evolucion, tab_otro) = st.tabs(
        [
            "Saldos x Barrio (evol.)",
            "EN PROCESO",
        ],
        on_change="rerun",
    )

    if tab_saldos_barrios_evolucion.open:
        saldos_barrios_evolucion.render()

    if tab_otro.open:
        pass


if __name__ == "__main__":
    main()
