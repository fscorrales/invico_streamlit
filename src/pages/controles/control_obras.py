"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: ICARO vs SGF Resumen de Rendiciones Proveedores
Data required:
    - Icaro
    - SIIF rdeu012
    - SGF Resumen de Rendiciones por Proveedor
    - SGF Listado Proveedores (POR LE MONENTO USO PROVEEDORES DE ICARO)
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/16v2ovmQnS1v73-WxTOK6b9Tx9DRugGc70ufpjVi-rPA
"""

import pandas as pd
import streamlit as st

from src.automation.analysis import control_obras
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_obras, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import report_template, request_siif_and_sgf_credentials_modal

ENDPOINT = Endpoints.CONTROL_OBRAS.value
REPORTE = "control_obras"
URL_SHEET = "https://docs.google.com/spreadsheets/d/16v2ovmQnS1v73-WxTOK6b9Tx9DRugGc70ufpjVi-rPA"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sgf_username: str,
    sgf_password: str,
    reporte: str,
) -> list[str]:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # 2. Iniciamos la descarga automática
    results = []
    # 2.a. Ejecutamos la automatización de SIIF
    results = await control_obras.sync_control_obras_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 2.b. Ejecutamos el módulo runner de SGF en un proceso separado
    control_obras.sync_control_obras_from_sgf(
        sgf_username=sgf_username,
        sgf_password=sgf_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SGF ejecutado correctamente.")

    # 3. El backend recalcula el cruce (GET /generate) y congelamos el
    #    snapshot en Mongo con un POST por ejercicio.
    results.extend(control_obras.compute_control_obras(ejercicios=ejercicios))

    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Omite la descarga de reportes (SIIF y SGF) y recalcula el cruce
    con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_obras``)
            usada para leer los ejercicios seleccionados en
            ``st.session_state``.

    Returns:
        Lista de mensajes con el resultado de cada ejercicio.
    """
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return []

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # Solo recalculamos: sin sync_control_obras_from_siif() ni
    # sync_control_obras_from_sgf(). compute_control_obras() pide el
    # cruce al backend (GET /control/controlObras/generate) y sincroniza
    # la colección con un POST por ejercicio.
    return control_obras.compute_control_obras(ejercicios=ejercicios)


# --------------------------------------------------
def _render_totales_control_obras(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce
    ICARO vs SGF: total ejecutado en ICARO, total bruto en SGF y la
    diferencia entre ambos.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de recursos
    (``_render_totales_control_recursos``). Sin ``nowrap`` ni ellipsis:
    el texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles ``ejecutado_icaro`` y
    ``bruto_sgf`` (con ``parse_moneda_ar``, que acepta tanto el número
    crudo de la API como una cadena ya formateada) y la resta se
    formatea con ``formato_moneda_ar``.

    Args:
        df: DataFrame del control de obras (se espera que tenga las
            columnas ``ejecutado_icaro`` y ``bruto_sgf``).
    """
    columnas_requeridas = {"ejecutado_icaro", "bruto_sgf"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_ejecutado_icaro: float = df["ejecutado_icaro"].apply(parse_moneda_ar).sum()
    total_bruto_sgf: float = df["bruto_sgf"].apply(parse_moneda_ar).sum()
    diferencia: float = total_ejecutado_icaro - total_bruto_sgf

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total Ejecutado ICARO",
            total_ejecutado_icaro,
            "Suma de la columna ejecutado_icaro de todas las filas visibles",
        ),
        (
            "Total Bruto SGF",
            total_bruto_sgf,
            "Suma de la columna bruto_sgf de todas las filas visibles",
        ),
        (
            "Diferencia",
            diferencia,
            "Total Ejecutado ICARO - Total Bruto SGF",
        ),
    )

    items: list[str] = []
    for etiqueta, total, ayuda in metricas:
        valor = formato_moneda_ar(total)
        # Dos ítems: etiqueta (línea 1) + valor en negrita (línea 2).
        # Sin nowrap/ellipsis para que el total nunca aparezca cortado.
        items.append(
            f'<div title="{ayuda}" '
            f'style="flex:1 1 0; min-width:0; text-align:center;">'
            f'<div style="font-size:11px; opacity:0.75; '
            f'white-space:normal;">{etiqueta}</div>'
            f'<div style="font-size:13px; font-weight:600;">'
            f"{valor}</div></div>"
        )

    st.markdown(
        '<div style="display:flex; gap:0.75rem; font-size:13px; '
        'align-items:flex-start;">' + "".join(items) + "</div>",
        unsafe_allow_html=True,
    )


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title=REPORTE.replace("_", " ").title(),
        endpoint=ENDPOINT,
        description=f"Cruce de Ejecución Obras entre ICARO y Sistema de Gestión Financiera. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_and_sgf_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="SIIF's rdeu012. SGF: Resumen de Rendiciones por Proveedor y Listado Proveedores (desde ICARO)",
            skip_callback=(lambda: run_skip(REPORTE)) if run_skip else None,
        ),
        max_selections=1,
    )

    if st.session_state.get(f"{REPORTE}_automation_success"):
        # Limpiamos el flag para que no entre en bucle infinito
        st.session_state[f"{REPORTE}_automation_success"] = False

        # Incrementamos el trigger de forma síncrona y segura
        actual = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
        st.session_state[f"{REPORTE}_uploader_iteration"] = actual + 1

        # Forzamos el recálculo total de la página con el nuevo trigger
        st.rerun()

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        df = get_control_obras(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info("No se encontraron resultados.")
        # else:
        #     st.session_state[f"data_{key}_carga"] = df_final
        #     st.session_state[f"data_{key}_retenciones"] = df_final_ret

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Formato moneda AR ($ 1.234,56) para los importes visibles de la
        # grilla. ``parse_moneda_ar`` (franja de totales) es el inverso de
        # ``formato_moneda_ar`` y acepta tanto el número crudo de la API
        # como la cadena ya formateada, por lo que los totales siguen
        # cuadrando con lo que muestra la grilla. El df proviene de
        # ``@st.cache_data`` (copia deserializada por llamada), por lo que
        # mutarlo en el lugar es seguro. Los nulos quedan en blanco y la
        # pasada extra por ``parse_moneda_ar`` hace el formateo idempotente
        # ante cadenas ya formateadas.
        for columna_moneda in ("ejecutado_icaro", "bruto_sgf", "diferencia"):
            if columna_moneda in df.columns:
                df[columna_moneda] = df[columna_moneda].apply(
                    lambda valor: (
                        formato_moneda_ar(parse_moneda_ar(valor))
                        if pd.notna(valor)
                        else ""
                    )
                )

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la
        # lista negra ni en CAMPOS_OCULTOS (id/_id se ocultan en la grilla)
        orden_dinamico = first_cols + [
            col
            for col in df.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_obras",
            column_order=orden_dinamico,
        )

        # Franja de totales: ejecutado ICARO vs bruto SGF, siempre
        # visible fuera de la grilla.
        _render_totales_control_obras(df)


if __name__ == "__main__":
    render()
