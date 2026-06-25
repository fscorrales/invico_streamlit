"""Página Principal: Tablas Auxiliares - SIIF."""

import streamlit as st

from src.pages.tablas_auxiliares.siif import (
    gto_rpa03g,
    rcg01_uejp,
    rci02,
    rcocc31,
    rdeu012,
    rf602,
    rf610,
    rfondo07tp,
    rfondos04,
    rfp_p605b,
    ri102,
    rog01,
    rvicon03,
)


def main() -> None:

    (
        tab_rog01,
        tab_rvicon03,
        tab_rcocc31,
        tab_ri102,
        tab_rci02,
        tab_rfp_p605b,
        tab_rf602,
        tab_rf610,
        tab_rcg01_uejp,
        tab_gto_rpa03g,
        tab_rdeu012,
        tab_rfondo07tp,
        tab_rfondos04,
    ) = st.tabs(
        [
            "rog01",
            "rvicon03",
            "rcocc31",
            "ri102",
            "rci02",
            "rfp_p605b",
            "rf602",
            "rf610",
            "rcg01_uejp",
            "gto_rpa03g",
            "rdeu012",
            "rfondo07tp",
            "rfondos04",
        ],
        on_change="rerun",
    )

    if tab_rog01.open:
        rog01.render()

    if tab_rvicon03.open:
        rvicon03.render()

    if tab_rcocc31.open:
        rcocc31.render()

    if tab_ri102.open:
        ri102.render()

    if tab_rci02.open:
        rci02.render()

    if tab_rfp_p605b.open:
        rfp_p605b.render()

    if tab_rf602.open:
        rf602.render()

    if tab_rf610.open:
        rf610.render()

    if tab_rcg01_uejp.open:
        rcg01_uejp.render()

    if tab_gto_rpa03g.open:
        gto_rpa03g.render()

    if tab_rdeu012.open:
        rdeu012.render()

    if tab_rfondo07tp.open:
        rfondo07tp.render()

    if tab_rfondos04.open:
        rfondos04.render()


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
