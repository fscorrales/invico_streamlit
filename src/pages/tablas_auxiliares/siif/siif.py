"""Página Principal: Tablas Auxiliares - SIIF."""

import streamlit as st

from src.pages.tablas_auxiliares.siif import rf602, rf610, rfondo07tp


def main() -> None:

    tab1, tab2, tab3 = st.tabs(["rf602", "rf610", "rfondo07tp"])

    with tab1:
        rf602.render()

    with tab2:
        rf610.render()

    with tab3:
        rfondo07tp.render()


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
