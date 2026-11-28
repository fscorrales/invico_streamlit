"""Página: Otros Gastos - SGF depurado.

Resumen de Rendiciones Proveedores con lo que ya cubren los demás
controles removido (obras, honorarios y escribanos).
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.pages.controles.control_otros_gastos.subtotales import render_subtotales
from src.services import (
    apply_text_filters,
    get_control_otros_gastos_sgf,
    get_ejercicios_list,
)
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_us, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_and_sgf_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_OTROS_GASTOS.value
REPORTE = "control_otros_gastos_sgf"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1EBzBz17mtVzBmpAFznDyJf2RAJNspQyJQJaRD_WI5dE"
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "CUIT",
        "column": "cuit",
        "placeholder": "Ej: 20111222333",
        "help": "Búsqueda parcial del CUIT, sin distinguir mayúsculas.",
    },
    {
        "label": "Destino",
        "column": "destino",
        "placeholder": "Ej: OBRAS",
        "help": "Búsqueda parcial del destino del rendimiento.",
    },
    {
        "label": "Libramiento",
        "column": "libramiento",
        "placeholder": "Ej: 12345",
        "help": "Búsqueda parcial del número de libramiento SGF.",
    },
]


# --------------------------------------------------
def _render_subtotales_sgf(df: pd.DataFrame) -> None:
    """Franja de subtotales: registros, bruto, retenciones y neto.

    Args:
        df: DataFrame SGF depurado (``importe_bruto``, ``retenciones``,
            ``importe_neto``).
    """
    columnas_requeridas = {"importe_bruto", "retenciones", "importe_neto"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_bruto: float = df["importe_bruto"].apply(parse_moneda_ar).sum()
    total_retenciones: float = df["retenciones"].apply(parse_moneda_ar).sum()
    total_neto: float = df["importe_neto"].apply(parse_moneda_ar).sum()
    render_subtotales(
        [
            ("Registros", str(len(df)), "Filas visibles de la tabla SGF"),
            (
                "Total Bruto",
                formato_moneda_us(total_bruto),
                "Suma de importe_bruto de las filas visibles",
            ),
            (
                "Total Retenciones",
                formato_moneda_us(total_retenciones),
                "Suma de retenciones de las filas visibles",
            ),
            (
                "Total Neto",
                formato_moneda_us(total_neto),
                "Suma de importe_neto de las filas visibles",
            ),
        ]
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
        title="Otros Gastos - SGF Depurado",
        endpoint=ENDPOINT,
        description=(
            "La actualización (Ejecutar u Omitir) y la exportación "
            "impactan en las 4 pestañas. Tabla SGF depurada (lo que "
            "quedó por fuera de los demás controles). Datos exportados "
            f"en [Google Sheet]({URL_SHEET})."
        ),
        filters_config=mis_filtros,
        update_func=lambda: request_siif_and_sgf_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info=(
                "SIIF: rcg01_uejp, gto_rpa03g (grupos 1-4) y "
                "rfondo07tp (PA6). SGF: Resumen de Rendiciones "
                "Proveedores (todos los orígenes)."
            ),
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
        df = get_control_otros_gastos_sgf(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info(
                "Sin datos persistidos para el ejercicio/filtro seleccionado. "
                "Use el botón 'Actualizar' (Ejecutar u Omitir) para "
                "recalcular y congelar la tabla SGF depurada."
            )

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        # ``columns=len(FILTROS_TABLA)`` (= 3) deja las 3 cajas en una
        # sola fila y solo afecta a ESTA página.
        valores_filtro = text_filters_bar(
            FILTROS_TABLA, key_prefix=REPORTE, columns=len(FILTROS_TABLA)
        )
        df_vista = apply_text_filters(df, valores_filtro)

        if df_vista.empty:
            st.info("No se encontraron resultados con los filtros de la barra.")

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
            "mes",
            "fecha",
            "libramiento",
        ]

        # Generamos el orden dinámico: todas las de la vista que no estén
        # en la lista negra ni en CAMPOS_OCULTOS (id/_id se ocultan en la
        # grilla)
        orden_dinamico = first_cols + [
            col
            for col in df_vista.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df_vista,
            key=f"{REPORTE}_df_control_otros_gastos_sgf",
            column_order=orden_dinamico,
            columnas_importe=("importe_bruto", "retenciones", "importe_neto"),
        )

        # Franja de subtotales: siempre visible fuera de la grilla, y
        # calculada sobre la vista filtrada para que registros y totales
        # coincidan con lo que muestra la grilla.
        _render_subtotales_sgf(df_vista)


if __name__ == "__main__":
    render()
