import streamlit as st

from src.automation.analysis import control_honorarios
from src.pages.controles.control_honorarios import (
    control_sgf_vs_slave,
    control_siif_vs_slave,
)


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
    sgf_username: str,
    sgf_password: str,
    reporte: str,
) -> None:
    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # 2. Iniciamos la descarga automática
    results = []
    # 2.a. Ejecutamos la automatización de SIIF
    results = await control_honorarios.sync_control_honorarios_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )
    # 2.b. Ejecutamos el módulo runner de SSCC en un proceso separado
    control_honorarios.sync_control_honorarios_from_sscc(
        sscc_username=sscc_username,
        sscc_password=sscc_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SSCC ejecutado correctamente.")

    # 2.b. Ejecutamos el módulo runner de SGF en un proceso separado
    control_honorarios.sync_control_honorarios_from_sgf(
        sgf_username=sgf_username,
        sgf_password=sgf_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SGF ejecutado correctamente.")

    # # 3. Combinamos las tablas y actualizamos los reportes
    # control_banco.compute_control_cruzado(ejercicios=ejercicios)

    return results


# --------------------------------------------------
def main() -> None:
    tab_control_sgf, tab_control_siif = st.tabs(
        ["SGF vs Slave", "SIIF vs Slave"], on_change="rerun"
    )

    if tab_control_sgf.open:
        control_sgf_vs_slave.render(automation_func=run_automation)

    if tab_control_siif.open:
        control_siif_vs_slave.render(automation_func=run_automation)


# --------------------------------------------------
if __name__ == "__main__":
    main()
