"""Página Principal: Tablas Auxiliares - SIIF."""

import streamlit as st

from src.pages.tablas_auxiliares.sgv import saldos_barrios_evolucion


def main() -> None:

    (tab_saldos_barrios_evolucion, tab_otro) = st.tabs(
        [
            "Saldos x Barrio",
            "EN PROCESO",
        ],
        on_change="rerun",
    )

    if tab_saldos_barrios_evolucion.open:
        saldos_barrios_evolucion.render()

    if tab_otro.open:
        pass


# tab1, tab2 = st.tabs(["Chart", "Data"], on_change="rerun")

# if tab1.open:
#     with st.spinner("Loading Tab 1..."):
#         time.sleep(2)
#     with tab1:
#         st.line_chart({"data": [1, 5, 2, 6]})

# if tab2.open:
#     with st.spinner("Loading Tab 2..."):
#         time.sleep(2)
#     with tab2:
#         st.dataframe({"col1": [1, 2, 3]})

if __name__ == "__main__":
    main()
