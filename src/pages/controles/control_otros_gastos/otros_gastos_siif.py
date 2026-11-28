"""Página: Otros Gastos - SIIF depurado.

Tabla SIIF (gto_rpa03g ⟕ rcg01_uejp) con todo lo que ya cubren los
demás controles removido (es_aprobado, MAP, PA6, obras Icaro, haberes,
honorarios, viáticos, débitos bancarios y ART). Las cajas chicas NO se
depuran: SÍ están en SGF y se cruzan uno a uno en el cruce.
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe, text_filters_bar
from src.constants.endpoints import Endpoints
from src.pages.controles.control_otros_gastos.subtotales import render_subtotales
from src.services import (
    apply_text_filters,
    get_control_otros_gastos_siif,
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
REPORTE = "control_otros_gastos_siif"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1EBzBz17mtVzBmpAFznDyJf2RAJNspQyJQJaRD_WI5dE"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo). Se excluyen de ``column_order``, lo que hace que Streamlit las
# oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Filtros particulares de la grilla (frontend puro): se renderizan con
# text_filters_bar() y se aplican en cascada con apply_text_filters()
# sobre el DataFrame ya obtenido de la API, sin volver a tocar la API.
FILTROS_TABLA: list[dict[str, str]] = [
    {
        "label": "CUIT",
        "column": "cuit",
        "placeholder": "Ej: 20111222333",
        "help": "Búsqueda parcial del CUIT del beneficiario, sin distinguir mayúsculas.",
    },
    {
        "label": "Nro. de fondo",
        "column": "nro_fondo",
        "placeholder": "Ej: 123",
        "help": "Búsqueda parcial del número de fondo (rfondo07tp / PA6).",
    },
    {
        "label": "Nro. de entrada",
        "column": "nro_entrada",
        "placeholder": "Ej: 45",
        "help": "Búsqueda parcial del número de entrada.",
    },
    {
        "label": "Partida",
        "column": "partida",
        "placeholder": "Ej: 412",
        "help": "Búsqueda parcial del código de partida presupuestaria.",
    },
]


# --------------------------------------------------
def _render_subtotales_siif(df: pd.DataFrame) -> None:
    """Franja de subtotales de la tabla SIIF depurada: registros y
    total de importe.

    Args:
        df: DataFrame SIIF depurado (se espera la columna ``importe``).
    """
    if "importe" not in df.columns:
        return

    total_importe: float = df["importe"].apply(parse_moneda_ar).sum()
    render_subtotales(
        [
            (
                "Registros",
                str(len(df)),
                "Filas visibles de la tabla SIIF depurada",
            ),
            (
                "Total Importe",
                formato_moneda_us(total_importe),
                "Suma de la columna importe de todas las filas visibles",
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
        title="Otros Gastos - SIIF Depurado",
        endpoint=ENDPOINT,
        description=(
            "La actualización (Ejecutar u Omitir) y la exportación "
            "impactan en las 4 pestañas. Tabla SIIF depurada (lo que "
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
        df = get_control_otros_gastos_siif(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info(
                "Sin datos persistidos para el ejercicio/filtro seleccionado. "
                "Use el botón 'Actualizar' (Ejecutar u Omitir) para "
                "recalcular y congelar la tabla SIIF depurada."
            )

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Filtros particulares de la grilla (frontend puro, sin llamadas
        # a la API): declarativos en FILTROS_TABLA y aplicados en cascada.
        # ``columns=len(FILTROS_TABLA)`` (= 4) deja las 4 cajas en una
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
            "nro_comprobante",
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
            key=f"{REPORTE}_df_control_otros_gastos_siif",
            column_order=orden_dinamico,
            columnas_importe=("importe",),
        )

        # Franja de subtotales: siempre visible fuera de la grilla, y
        # calculada sobre la vista filtrada para que registros y total
        # coincidan con lo que muestra la grilla.
        _render_subtotales_siif(df_vista)


if __name__ == "__main__":
    render()
