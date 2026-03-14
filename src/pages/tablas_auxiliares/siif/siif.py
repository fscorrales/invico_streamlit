"""Página Principal: Tablas Auxiliares - SIIF."""

import streamlit as st

from src.pages.tablas_auxiliares.siif import siif_rf602, siif_rf610


def main() -> None:
    # # Sidebar menu logic
    # st.sidebar.markdown("### Menú SIIF")

    # # We use radio buttons as they match the list style closely
    # menu_selection = st.sidebar.radio(
    #     "Reportes Disponibles",
    #     options=["RF602", "RF610"],
    #     label_visibility="collapsed",
    # )

    # # Render selected sub-page
    # if menu_selection == "RF602":
    #     siif_rf602.render()
    # elif menu_selection == "RF610":
    #     siif_rf610.render()

    tab1, tab2 = st.tabs(["RF602", "RF610"])

    with tab1:
        siif_rf602.render()

    with tab2:
        siif_rf610.render()


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
