import streamlit as st

from src.pages.reportes.reporte_formulacion import (
    reporte_carga_formulacion,
    reporte_gastos,
    reporte_planillometro,
    reporte_recursos,
)


# --------------------------------------------------
async def run_automation(siif_username: str, siif_password: str, reporte: str) -> None:
    pass
    # # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    # ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    # if not ejercicios:
    #     st.error("No hay ejercicios seleccionados.")
    #     return

    # # Ensure we have a list of integers
    # if isinstance(ejercicios, int):
    #     ejercicios = [ejercicios]

    # # 2. Iniciamos la descarga automática
    # results = []
    # # # 2.a. Ejecutamos la automatización de SIIF
    # results = await control_icaro.sync_control_icaro_from_siif(
    #     siif_username=siif_username,
    #     siif_password=siif_password,
    #     ejercicios=ejercicios,
    # )

    # # 3. Combinamos las tablas y actualizamos los reportes
    # control_icaro.compute_control_anual(ejercicios=ejercicios)
    # control_icaro.compute_control_comprobantes(ejercicios=ejercicios)
    # control_icaro.compute_control_pa6(ejercicios=ejercicios)

    # return results


def main() -> None:
    tab_carga_formulacion, tab_recursos, tab_gastos, tab_planillometro = st.tabs(
        [
            "Carga Formulación",
            "Ejecución de Recursos",
            "Ejecución de Gastos",
            "Planillómetro Obras",
        ],
        on_change="rerun",
    )

    if tab_carga_formulacion.open:
        reporte_carga_formulacion.render(run_automation)

    if tab_recursos.open:
        reporte_recursos.render(run_automation)

    if tab_gastos.open:
        reporte_gastos.render(run_automation)

    if tab_planillometro.open:
        reporte_planillometro.render(run_automation)


if __name__ == "__main__":
    main()
