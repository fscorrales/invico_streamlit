"""Página Principal: Control Honorarios (SGF vs Slave / SIIF vs Slave)."""

from collections.abc import Callable

import streamlit as st

from src.automation.analysis import control_honorarios
from src.pages.controles.control_honorarios import (
    control_sgf_vs_slave,
    control_siif_vs_slave,
)

# Fuente única de verdad de la familia: qué compute congela el snapshot
# de cada subreporte. Las claves son los REPORTE de cada pestaña, que es
# exactamente lo que el modal envía como key. Las páginas son agnósticas:
# reciben run_automation/run_skip como callbacks (mismo patrón que la
# familia control_icaro) y no nombran sus compute.
COMPUTE_FUNCTIONS: dict[str, Callable[..., list[str]]] = {
    control_sgf_vs_slave.REPORTE: control_honorarios.compute_control_sgf_vs_slave,
    control_siif_vs_slave.REPORTE: control_honorarios.compute_control_siif_vs_slave,
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
    """Recalcula y persiste los snapshots de las 2 pestañas.

    Ambos cruces se calculan con el MISMO rango de ejercicios: el de la
    pestaña que abrió el modal (el filtro de la otra pestaña se ignora
    para el cómputo). Los POST son idempotentes por ejercicio, por lo
    que solo se reemplazan las filas de ese rango en cada colección.

    Args:
        ejercicios: Rango que gobierna ambos computes.

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
    Botón "Omitir": omite la descarga de reportes (SIIF, SSCC y SGF) y
    recalcula los snapshots de las 2 pestañas con los datos ya
    presentes en la API (simétrico con run_automation, que congela los
    2 tras el sync).

    Args:
        reporte: Clave de la pestaña que disparó el modal; el rango de
            ejercicios de ESTA pestaña es el que gobierna el cómputo.

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
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
    sgf_username: str,
    sgf_password: str,
    reporte: str,
) -> list[str]:
    # 1. El rango de ejercicios que gobierna la descarga Y ambos
    #    cómputos es el de la pestaña que abrió el modal (el filtro de
    #    la otra pestaña se ignora para el cómputo).
    ejercicios = _read_ejercicios(reporte)
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # 2. Iniciamos la descarga automática (auxiliares compartidos por
    #    ambos cruces: SIIF, SSCC y SGF)
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

    # 2.c. Ejecutamos el módulo runner de SGF en un proceso separado
    control_honorarios.sync_control_honorarios_from_sgf(
        sgf_username=sgf_username,
        sgf_password=sgf_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SGF ejecutado correctamente.")

    # 3. El backend recalcula AMBOS cruces (GET /generate*) con el
    #    mismo rango y congelamos los snapshots en Mongo con un POST
    #    por ejercicio (patrón conjunto de control_icaro).
    results.extend(_compute_all_snapshots(ejercicios))

    return results


# --------------------------------------------------
def _refresh_family_after_update() -> None:
    """Refresco conjunto de la familia tras una actualización.

    El modal solo setea ``{clave}_automation_success`` en la pestaña que
    lo disparó; sin esta pasada, la otra pestaña serviría su cache de
    ``@st.cache_data`` (mismo ``update_trigger``) con datos viejos hasta
    el TTL. Al detectar el flag: se limpian los flags de la familia y se
    incrementa el trigger de AMBAS pestañas para que ambas grillas hagan
    cache-miss y muestren los snapshots recién persistidos.

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

    tab_control_sgf, tab_control_siif = st.tabs(
        ["SGF vs Slave", "SIIF vs Slave"], on_change="rerun"
    )

    if tab_control_sgf.open:
        control_sgf_vs_slave.render(run_automation, run_skip)

    if tab_control_siif.open:
        control_siif_vs_slave.render(run_automation, run_skip)


# --------------------------------------------------
if __name__ == "__main__":
    main()
