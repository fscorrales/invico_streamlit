"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Control Anticipo de Viaticos (PA3)
Data required:
    - SIIF rfondos04 (PA3 y REV)
    - SIIF rpa03g
    - SIIF rcg01_uejp
    - SSCC Resumen General de Movimientos
        + 029 Anticipo de Viaticos Pagados (PAV de PA3)
        + 040 Reembolso por Gastos Mayores (Partida 373)
        + 005 Devolución de Fondos no Utilizados (REV)
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1alo5UBd7YRIBhSXqfo_c5Lz8JBfU3CXrVC0XOmtiH8c
"""

import pandas as pd
import streamlit as st

from src.automation.analysis import control_viaticos
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_viaticos, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_and_sscc_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_VIATICOS.value
REPORTE = "control_viaticos"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1alo5UBd7YRIBhSXqfo_c5Lz8JBfU3CXrVC0XOmtiH8c"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Columnas monetarias del cruce (formato moneda AR en la grilla).
COLUMNAS_MONEDA: tuple[str, ...] = (
    "siif_anticipo",
    "siif_rendicion",
    "siif_reversion",
    "siif_saldo_anticipo",
    "siif_reembolso",
    "siif_gasto_total",
    "sscc_anticipo",
    "sscc_reversion",
    "sscc_reembolso",
    "sscc_gasto_total",
    "dif_gasto_total",
)


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
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
    # 2.a. Ejecutamos la automatización de SIIF (rcg01_uejp, rpa03g y
    #      rfondos04 PA3/REV)
    results = await control_viaticos.sync_control_viaticos_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 2.b. Ejecutamos el módulo runner de SSCC en un proceso separado
    control_viaticos.sync_control_viaticos_from_sscc(
        sscc_username=sscc_username,
        sscc_password=sscc_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SSCC ejecutado correctamente.")

    # 3. El backend recalcula el cruce (GET /generate) y congelamos el
    #    snapshot en Mongo con un POST por ejercicio.
    results.extend(control_viaticos.compute_control_viaticos(ejercicios=ejercicios))

    return results


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Omite la descarga de reportes (SIIF y SSCC) y recalcula el cruce
    de viáticos con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_viaticos``)
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

    # Solo recalculamos: sin descargar SIIF/SSCC.
    # compute_control_viaticos() pide el cruce al backend
    # (GET /control/controlViaticos/generate) y sincroniza la colección
    # con un POST por ejercicio.
    return control_viaticos.compute_control_viaticos(ejercicios=ejercicios)


# --------------------------------------------------
def _render_totales_control_viaticos(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce de
    viáticos: gasto total SIIF, gasto total SSCC y la diferencia.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de obras
    (``_render_totales_control_obras``). Sin ``nowrap`` ni ellipsis: el
    texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles ``siif_gasto_total``
    y ``sscc_gasto_total`` (con ``parse_moneda_ar``, que acepta tanto el
    número crudo de la API como una cadena ya formateada) y la resta se
    formatea con ``formato_moneda_ar``.

    Args:
        df: DataFrame del control de viáticos (se espera que tenga las
            columnas ``siif_gasto_total`` y ``sscc_gasto_total``).
    """
    columnas_requeridas = {"siif_gasto_total", "sscc_gasto_total"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_siif_gasto: float = df["siif_gasto_total"].apply(parse_moneda_ar).sum()
    total_sscc_gasto: float = df["sscc_gasto_total"].apply(parse_moneda_ar).sum()
    diferencia: float = total_siif_gasto - total_sscc_gasto

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total SIIF Gasto",
            total_siif_gasto,
            "Suma de la columna siif_gasto_total de todas las filas visibles",
        ),
        (
            "Total SSCC Gasto",
            total_sscc_gasto,
            "Suma de la columna sscc_gasto_total de todas las filas visibles",
        ),
        (
            "Diferencia",
            diferencia,
            "Total SIIF Gasto - Total SSCC Gasto",
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
        description=f"Control Anticipo/Rendición de Viáticos (PA3). Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_and_sscc_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="SIIF: rcg01_uejp, gto_rpa03g y rfondos04 (PA3 y REV). SSCC's Banco INVICO (029, 040 y 005).",
            skip_callback=(lambda: run_skip(REPORTE)) if run_skip else None,
        ),
        max_selections=1,
        export_endpoint=ENDPOINT + "/export",
        export_mode="sheet",
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
        df = get_control_viaticos(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info("No se encontraron resultados.")

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
        for columna_moneda in COLUMNAS_MONEDA:
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
            key=f"{REPORTE}_df_control_viaticos",
            column_order=orden_dinamico,
        )

        # Franja de totales: gasto total SIIF vs SSCC y diferencia,
        # siempre visible fuera de la grilla.
        _render_totales_control_viaticos(df)


if __name__ == "__main__":
    render()