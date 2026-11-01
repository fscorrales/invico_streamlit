import streamlit as st

from src.pages.reportes.reporte_planillometro_eecc import (
    obras_desactivadas,
    obras_recuperadas,
    reporte_planillometro_eecc,
)


def main() -> None:
    (
        tab_reporte_planillometro_eecc,
        tab_obras_recuperadas,
        tab_obras_desactivadas,
    ) = st.tabs(
        ["Planillometro EECC", "Obras Recuperadas", "Obras Desactivadas"],
        on_change="rerun",
    )

    if tab_reporte_planillometro_eecc.open:
        reporte_planillometro_eecc.render()

    if tab_obras_recuperadas.open:
        obras_recuperadas.render()

    if tab_obras_desactivadas.open:
        obras_desactivadas.render()


if __name__ == "__main__":
    main()
