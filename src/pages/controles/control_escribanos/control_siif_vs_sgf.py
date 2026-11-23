"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Escribanos SIIF vs SGF
Data required:
    - SIIF rcocc31 (2113-2-9 Escribanos)
    - SGF Resumen de Rendiciones Proveedores (cta. cte. 130832-08)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1Tz3uvUGBL8ZDSFsYRBP8hgIis-hlhs_sQ6V5bI4LaTg
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_siif_vs_sgf, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_us, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_sscc_and_sgf_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_ESCRIBANOS.value
REPORTE = "control_siif_vs_sgf"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1Tz3uvUGBL8ZDSFsYRBP8hgIis-hlhs_sQ6V5bI4LaTg"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
def _render_totales_siif_vs_sgf(df: pd.DataFrame) -> None:
    """Franja compacta bajo la grilla con los totales del cruce
    SIIF vs SGF: carga FEI, pagos FEI, pagos SGF y la diferencia.

    Los totales quedan FUERA del dataframe —siempre a la vista— para que
    el usuario no tenga que desplazarse hasta la última fila. Es una
    franja HTML flex de dos líneas por ítem (etiqueta arriba, valor en
    negrita abajo), idéntica en estilo a la del control de honorarios
    (``_render_totales_siif_vs_slave``). Sin ``nowrap`` ni ellipsis: el
    texto nunca se recorta. Hereda los colores del tema (no se fijan
    colores en el markup) y los ``title`` nativos del HTML muestran el
    tooltip al hacer hover, sin JS.

    Se suman los valores de las columnas visibles con
    ``parse_moneda_ar`` (acepta tanto el número crudo de la API como una
    cadena ya formateada) y la diferencia se formatea con
    ``formato_moneda_us``.

    Args:
        df: DataFrame del cruce SIIF vs SGF (se espera que tenga las
            columnas ``carga_fei``, ``pagos_fei``, ``pagos_sgf`` y
            ``dif_pagos``).
    """
    columnas_requeridas = {"carga_fei", "pagos_fei", "pagos_sgf", "dif_pagos"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_carga_fei: float = df["carga_fei"].apply(parse_moneda_ar).sum()
    total_pagos_fei: float = df["pagos_fei"].apply(parse_moneda_ar).sum()
    total_pagos_sgf: float = df["pagos_sgf"].apply(parse_moneda_ar).sum()
    dif_pagos: float = df["dif_pagos"].apply(parse_moneda_ar).sum()

    metricas: tuple[tuple[str, float, str], ...] = (
        (
            "Total Carga FEI",
            total_carga_fei,
            "Suma de la columna carga_fei de todas las filas visibles",
        ),
        (
            "Total Pagos FEI",
            total_pagos_fei,
            "Suma de la columna pagos_fei de todas las filas visibles",
        ),
        (
            "Total Pagos SGF",
            total_pagos_sgf,
            "Suma de la columna pagos_sgf de todas las filas visibles",
        ),
        (
            "Diferencia",
            dif_pagos,
            "Suma de la columna dif_pagos (pagos_fei - pagos_sgf)",
        ),
    )

    items: list[str] = []
    for etiqueta, total, ayuda in metricas:
        valor = formato_moneda_us(total)
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
        description=f"La actualización (Ejecutar u Omitir) y la exportación impactan en las 2 pestañas. Cruce de SIIF vs SGF. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_sscc_and_sgf_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF: rcocc31 (cta. contable 2113-2-9 Escribanos). SSCC's Resumen General de Movimientos. SGF: Resumen de Rendiciones Proveedores (cta. cte. 130832-08). Nota: ctas_ctes se carga manual desde Tablas Auxiliares.",
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
        df = get_control_siif_vs_sgf(
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
            key=f"{REPORTE}_df_control_siif_vs_sgf",
            column_order=orden_dinamico,
            columnas_importe=(
                "carga_fei",
                "pagos_fei",
                "fei_impagos",
                "pagos_sgf",
                "dif_pagos",
            ),
        )

        # Franja de totales: carga/pagos FEI, pagos SGF y diferencia,
        # siempre visible fuera de la grilla.
        _render_totales_siif_vs_sgf(df)


if __name__ == "__main__":
    render()