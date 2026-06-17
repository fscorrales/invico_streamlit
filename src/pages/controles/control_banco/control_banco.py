import streamlit as st

from src.automation.analysis import control_banco
from src.pages.controles.control_banco import (
    control_cruzado,
    control_siif,
    control_sscc,
)


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
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
    # # 2.a. Ejecutamos la automatización de SIIF
    results = await control_banco.sync_control_banco_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )
    # 2.b. Ejecutamos el módulo runner de SSCC en un proceso separado
    control_banco.sync_control_banco_from_sscc(
        sscc_username=sscc_username,
        sscc_password=sscc_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SSCC ejecutado correctamente.")

    # 3. Combinamos las tablas y actualizamos los reportes
    control_banco.compute_control_cruzado(ejercicios=ejercicios)

    return results


# --------------------------------------------------
def main() -> None:
    tab_anual, tab_comprobantes, tab_pa6 = st.tabs(
        ["Control Cruzado", "Banco SIIF", "Banco SSCC"], on_change="rerun"
    )

    if tab_anual.open:
        control_cruzado.render(run_automation)

    if tab_comprobantes.open:
        control_siif.render(run_automation)

    if tab_pa6.open:
        control_sscc.render(run_automation)


if __name__ == "__main__":
    main()
