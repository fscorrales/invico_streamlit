"""Página Principal: Tablas Auxiliares - SSCC."""

from collections.abc import Callable

import streamlit as st

from src.automation.analysis import control_icaro
from src.pages.controles.control_icaro import (
    control_anual,
    control_comprobantes,
    control_pa6,
)

# Fuente única de verdad de la familia: qué compute congela el snapshot
# de cada subreporte. Las claves son los REPORTE de cada pestaña, que es
# exactamente lo que el modal envía como key. Las páginas son agnósticas:
# reciben run_automation/run_skip como callbacks (mismo patrón que la
# familia control_banco) y no nombran sus compute.
COMPUTE_FUNCTIONS: dict[str, Callable[..., list[str]]] = {
    control_anual.REPORTE: control_icaro.compute_control_icaro_anual,
    control_comprobantes.REPORTE: control_icaro.compute_control_icaro_comprobantes,
    control_pa6.REPORTE: control_icaro.compute_control_icaro_pa6,
}


# --------------------------------------------------
def _read_ejercicios(clave: str) -> list[int]:
    """Lee y normaliza ``ejercicios_{clave}`` del session_state.

    Args:
        clave: REPORTE de la pestaña (el modal la envía como key).

    Returns:
        Lista de ejercicios; vacía si la pestaña nunca configuró el filtro.
    """
    ejercicios = st.session_state.get("ejercicios_" + clave, [])
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]
    return ejercicios


# --------------------------------------------------
def _compute_snapshot(clave: str) -> list[str]:
    """Compute (GET /computeControl...) + POST del snapshot de una pestaña.

    Las pestañas sin ejercicios (p.ej. nunca abiertas) devuelven un
    mensaje: invocar el compute emitiría un st.error engañoso para una
    pestaña que el usuario nunca configuró.
    """
    ejercicios = _read_ejercicios(clave)
    if not ejercicios:
        return [f"{clave}: sin ejercicios seleccionados; snapshot omitido."]
    return COMPUTE_FUNCTIONS[clave](ejercicios=ejercicios)


# --------------------------------------------------
def _compute_all_snapshots() -> list[str]:
    """Recalcula y persiste los snapshots de las 3 pestañas.

    Tanto la automatización (Ejecutar) como el skip (Omitir) impactan a
    los 3 subreportes, en coherencia con la descripción de las páginas
    ("la automatización y la exportación impactan en los 3 subreportes").
    """
    results: list[str] = []
    for clave in COMPUTE_FUNCTIONS:
        results.extend(_compute_snapshot(clave))
    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Botón "Omitir": omite la descarga de reportes (SIIF) y recalcula los
    snapshots de las 3 pestañas con los datos ya presentes en la API
    (simétrico con run_automation, que congela los 3 tras el sync).

    Args:
        reporte: Clave de la pestaña que disparó el modal; se valida que
            tenga ejercicios seleccionados antes de recalcular.

    Returns:
        Lista de mensajes con el resultado de cada pestaña/ejercicio.
    """
    if not _read_ejercicios(reporte):
        st.error("No hay ejercicios seleccionados.")
        return []
    return _compute_all_snapshots()


# --------------------------------------------------
async def run_automation(
    siif_username: str, siif_password: str, reporte: str
) -> list[str]:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = _read_ejercicios(reporte)
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # 2. Iniciamos la descarga automática
    results = []
    # # 2.a. Ejecutamos la automatización de SIIF
    results = await control_icaro.sync_control_icaro_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 3. El sync refresca las colecciones SIIF que alimentan a los 3
    #    subreportes, así que congelamos los snapshots de las 3
    #    colecciones con los ejercicios seleccionados en cada pestaña
    #    (mismo alcance que run_skip / botón Omitir).
    results.extend(_compute_all_snapshots())

    return results


# --------------------------------------------------
def main() -> None:
    tab_anual, tab_comprobantes, tab_pa6 = st.tabs(
        ["Control Anual", "Control Comprobantes", "Control PA6"], on_change="rerun"
    )

    if tab_anual.open:
        control_anual.render(run_automation, run_skip)

    if tab_comprobantes.open:
        control_comprobantes.render(run_automation, run_skip)

    if tab_pa6.open:
        control_pa6.render(run_automation, run_skip)


if __name__ == "__main__":
    main()
