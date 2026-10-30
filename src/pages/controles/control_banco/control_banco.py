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
def run_skip(reporte: str) -> None:
    """
    Omite la descarga de reportes (SIIF y SSCC) y recalcula el cruce
    con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_banco_cruzado``)
            usada para leer los ejercicios seleccionados en
            ``st.session_state``.
    """
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # Solo recalculamos: sin sync_control_banco_from_siif() ni
    # sync_control_banco_from_sscc(). compute_control_cruzado() regenera
    # los 3 subreportes (SIIF, SSCC y Cruzado) con los datos ya cargados.
    control_banco.compute_control_cruzado(ejercicios=ejercicios)


# --------------------------------------------------
def main() -> None:
    tab_anual, tab_comprobantes, tab_pa6 = st.tabs(
        ["Control Cruzado", "Banco SIIF", "Banco SSCC"], on_change="rerun"
    )

    if tab_anual.open:
        control_cruzado.render(run_automation, run_skip)

    if tab_comprobantes.open:
        control_siif.render(run_automation, run_skip)

    if tab_pa6.open:
        control_sscc.render(run_automation, run_skip)


if __name__ == "__main__":
    main()
