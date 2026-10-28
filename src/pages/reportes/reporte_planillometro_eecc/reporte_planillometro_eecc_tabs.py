import streamlit as st

from src.pages.reportes.reporte_planillometro_eecc import (
    obras_recuperadas,
    reporte_planillometro_eecc,
)


def main() -> None:
    tab_reporte_planillometro_eecc, tab_obras_recuperadas = st.tabs(
        ["Planillometro EECC", "Obras Recuperadas"], on_change="rerun"
    )

    if tab_reporte_planillometro_eecc.open:
        reporte_planillometro_eecc.render()

    if tab_obras_recuperadas.open:
        obras_recuperadas.render()


if __name__ == "__main__":
    main()
