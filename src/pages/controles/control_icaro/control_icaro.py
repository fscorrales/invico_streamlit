"""Página Principal: Tablas Auxiliares - SSCC."""

import streamlit as st

from src.automation.analysis import control_icaro
from src.pages.controles.control_icaro import control_anual, control_comprobantes


# --------------------------------------------------
async def run_automation(siif_username: str, siif_password: str, key: str) -> None:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + key, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # 2. Iniciamos la descarga automática
    results = []
    # # 2.a. Ejecutamos la automatización de SIIF
    # results = await control_icaro.sync_control_icaro_from_siif(
    #     siif_username=siif_username,
    #     siif_password=siif_password,
    #     ejercicios=ejercicios,
    # )

    # 3. Combinamos las tablas y actualizamos los reportes
    # control_icaro.compute_control_anual(ejercicios=ejercicios)
    control_icaro.compute_control_anual(ejercicios=ejercicios)

    return results


def main() -> None:
    tab_anual, tab_comprobantes = st.tabs(
        ["Control Anual", "Control Comprobantes"], on_change="rerun"
    )

    if tab_anual.open:
        control_anual.render(run_automation)

    if tab_comprobantes.open:
        control_comprobantes.render()


if __name__ == "__main__":
    main()
