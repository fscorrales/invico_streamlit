"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Haberes vs SSCC
Data required:
    - SLAVE (manual data)
    - SIIF rcg01_uejp
    - SIIF rpa03g
    - SGF Resumen de Rendiciones Proveedores
    - SSCC Resumen General de Movimientos
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1fQhp1CdESnvqzrp3QMV5bFSHmGdi7SNoaBRWtmw-JgA
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_sgf_vs_slave, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_sscc_and_sgf_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_HONORARIOS.value
REPORTE = "control_sgf_vs_slave"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1fQhp1CdESnvqzrp3QMV5bFSHmGdi7SNoaBRWtmw-JgA"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
def _render_totales_sgf_vs_slave(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce
    SGF vs Slave: importe bruto de cada sistema y sus diferencias
    bruta y neta.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de obras
    (``_render_totales_control_obras``). Sin ``nowrap`` ni ellipsis: el
    texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles con
    ``parse_moneda_ar`` (acepta tanto el número crudo de la API como una
    cadena ya formateada) y las diferencias se formatean con
    ``formato_moneda_ar``.

    Args:
        df: DataFrame del cruce SGF vs Slave (se espera que tenga las
            columnas ``sgf_importe_bruto``, ``slave_importe_bruto``,
            ``dif_importe_bruto`` y ``dif_importe_neto``).
    """
    columnas_requeridas = {
        "sgf_importe_bruto",
        "slave_importe_bruto",
        "dif_importe_bruto",
        "dif_importe_neto",
    }
    if not columnas_requeridas.issubset(df.columns):
        return

    total_sgf_bruto: float = df["sgf_importe_bruto"].apply(parse_moneda_ar).sum()
    total_slave_bruto: float = df["slave_importe_bruto"].apply(parse_moneda_ar).sum()
    dif_bruto: float = df["dif_importe_bruto"].apply(parse_moneda_ar).sum()
    dif_neto: float = df["dif_importe_neto"].apply(parse_moneda_ar).sum()

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total SGF Bruto",
            total_sgf_bruto,
            "Suma de la columna sgf_importe_bruto de todas las filas visibles",
        ),
        (
            "Total Slave Bruto",
            total_slave_bruto,
            "Suma de la columna slave_importe_bruto de todas las filas visibles",
        ),
        (
            "Diferencia Bruto",
            dif_bruto,
            "Suma de la columna dif_importe_bruto de todas las filas visibles",
        ),
        (
            "Diferencia Neto",
            dif_neto,
            "Suma de la columna dif_importe_neto de todas las filas visibles",
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
def render(
    automation_func: Optional[Any] = None,
    skip_func: Optional[Any] = None,
) -> None:

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
        description=f"La actualización (Ejecutar u Omitir) y la exportación impactan en las 2 pestañas. Cruce de SGF vs SLAVE. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_sscc_and_sgf_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF: rcg01_uejp y rpa03g. SSCC's Resumen General de Movimientos y ctas_ctes. SGF: Resumen de Rendiciones Proveedores.",
            skip_callback=(lambda: skip_func(REPORTE)) if skip_func else None,
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
        df = get_control_sgf_vs_slave(
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
        columnas_moneda = (
            "sgf_importe_bruto",
            "slave_importe_bruto",
            "dif_importe_bruto",
            "sgf_importe_neto",
            "slave_importe_neto",
            "dif_importe_neto",
        )
        for columna_moneda in columnas_moneda:
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
            key=f"{REPORTE}_df_control_sgf_vs_slave",
            column_order=orden_dinamico,
        )

        # Franja de totales: bruto SGF vs Slave y diferencias bruta/neta,
        # siempre visible fuera de la grilla.
        _render_totales_sgf_vs_slave(df)


if __name__ == "__main__":
    render()
