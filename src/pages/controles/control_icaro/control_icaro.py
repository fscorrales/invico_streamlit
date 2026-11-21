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
def _compute_all_snapshots(ejercicios: list[int]) -> list[str]:
    """Recalcula y persiste los snapshots de las 3 pestañas.

    Los 3 cómputos se realizan con el MISMO rango de ejercicios: el de
    la pestaña que abrió el modal (el filtro de las demás pestañas se
    ignora para el cómputo, incluso si nunca se abrieron). Los POST son
    idempotentes por ejercicio, por lo que solo se reemplazan las filas
    de ese rango en cada colección. Tanto la automatización (Ejecutar)
    como el skip (Omitir) impactan en los 3 subreportes, en coherencia
    con la descripción de las páginas ("la automatización y la
    exportación impactan en los 3 subreportes").

    Args:
        ejercicios: Rango que gobierna los 3 computes.

    Returns:
        Lista de mensajes con el resultado de cada pestaña/ejercicio.
    """
    results: list[str] = []
    for compute in COMPUTE_FUNCTIONS.values():
        results.extend(compute(ejercicios=ejercicios))
    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Botón "Omitir": omite la descarga de reportes (SIIF) y recalcula los
    snapshots de las 3 pestañas con los datos ya presentes en la API
    (simétrico con run_automation, que congela los 3 tras el sync).

    Args:
        reporte: Clave de la pestaña que disparó el modal; el rango de
            ejercicios de ESTA pestaña es el que gobierna el cómputo de
            las 3.

    Returns:
        Lista de mensajes con el resultado de cada pestaña/ejercicio.
    """
    ejercicios = _read_ejercicios(reporte)
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []
    return _compute_all_snapshots(ejercicios)


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
    #    colecciones con el MISMO rango de ejercicios (el de la pestaña
    #    que abrió el modal; mismo alcance que run_skip / Omitir).
    results.extend(_compute_all_snapshots(ejercicios))

    return results


# --------------------------------------------------
def _refresh_family_after_update() -> None:
    """Refresco conjunto de la familia tras una actualización.

    El modal solo setea ``{clave}_automation_success`` en la pestaña que
    lo disparó; sin esta pasada, las demás pestañas servirían su cache de
    ``@st.cache_data`` (mismo ``update_trigger``) con datos viejos hasta
    el TTL. Al detectar el flag: se limpian los flags de la familia y se
    incrementa el trigger de LAS 3 pestañas para que sus grillas hagan
    cache-miss y muestren los snapshots recién persistidos. Las
    pestañas nunca abiertas también reciben el trigger, de modo que al
    abrirse muestran datos frescos.

    Se ejecuta al inicio de ``main()``, ANTES de que las pestañas
    instancien sus widgets, por lo que no entra en conflicto con la
    restricción de Streamlit de no modificar ``st.session_state`` de un
    widget clave ya instanciado.
    """
    if not any(
        st.session_state.get(f"{clave}_automation_success")
        for clave in COMPUTE_FUNCTIONS
    ):
        return

    for clave in COMPUTE_FUNCTIONS:
        st.session_state[f"{clave}_automation_success"] = False
        st.session_state[f"{clave}_uploader_iteration"] = (
            st.session_state.get(f"{clave}_uploader_iteration", 0) + 1
        )
    st.rerun()


# --------------------------------------------------
def main() -> None:
    # Si alguna pestaña terminó una actualización (flag de éxito),
    # refrescamos el trigger de TODAS antes de renderizar los widgets.
    _refresh_family_after_update()

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
