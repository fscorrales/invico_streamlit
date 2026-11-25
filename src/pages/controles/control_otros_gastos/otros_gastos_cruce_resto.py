"""Página: Otros Gastos - Cruce Resto (pareo 1:1).

Capa 1 del cruce SIIF <-> SGF: pareo fila a fila de los registros que
NO son fondos permanentes, con estados PAREADO / SIIF_SIN_SGF /
SGF_SIN_SIIF.
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.pages.controles.control_otros_gastos.subtotales import render_subtotales
from src.services import get_control_otros_gastos_cruce_resto, get_ejercicios_list
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
REPORTE = "control_otros_gastos_cruce_resto"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1EBzBz17mtVzBmpAFznDyJf2RAJNspQyJQJaRD_WI5dE"
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")
# Estados del pareo (espejo de los valores que emite el backend)
ESTADO_PAREADO = "PAREADO"
ESTADO_SIIF_SIN_SGF = "SIIF_SIN_SGF"
ESTADO_SGF_SIN_SIIF = "SGF_SIN_SIIF"


# --------------------------------------------------
def _render_subtotales_cruce_resto(df: pd.DataFrame) -> None:
    """Franja de subtotales del pareo 1:1: conteos por estado, el
    importe de SIIF sin respaldo SGF y la diferencia de los pareados.

    Args:
        df: DataFrame de pareos (``estado``, ``siif_importe``, ``dif``).
    """
    if "estado" not in df.columns:
        return

    mask_pareado = df["estado"] == ESTADO_PAREADO
    mask_siif_sin = df["estado"] == ESTADO_SIIF_SIN_SGF
    mask_sgf_sin = df["estado"] == ESTADO_SGF_SIN_SIIF

    items: list[tuple[str, str, str]] = [
        (
            "Pareados",
            str(int(mask_pareado.sum())),
            "Filas con pareja exacta SIIF ↔ SGF (estado PAREADO)",
        ),
        (
            "SIIF sin SGF",
            str(int(mask_siif_sin.sum())),
            "Comprobantes SIIF sin contrapartida en SGF",
        ),
        (
            "SGF sin SIIF",
            str(int(mask_sgf_sin.sum())),
            "Libramientos SGF sin contrapartida en SIIF",
        ),
    ]

    if "siif_importe" in df.columns:
        importe_siif_sin: float = (
            df.loc[mask_siif_sin, "siif_importe"].apply(parse_moneda_ar).sum()
        )
        items.append(
            (
                "Importe SIIF sin SGF",
                formato_moneda_us(importe_siif_sin),
                "Suma de siif_importe de las filas en estado SIIF_SIN_SGF",
            )
        )

    if "dif" in df.columns:
        dif_pareados: float = df.loc[mask_pareado, "dif"].apply(parse_moneda_ar).sum()
        items.append(
            (
                "Dif. en pareados",
                formato_moneda_us(dif_pareados),
                "Suma de (siif_importe - sgf_importe_bruto) de los pareados",
            )
        )

    render_subtotales(items)


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
        title="Otros Gastos - Cruce Resto (1:1)",
        endpoint=ENDPOINT,
        description=(
            "La actualización (Ejecutar u Omitir) y la exportación "
            "impactan en las 4 pestañas. Capa 1 del cruce: pareo 1:1 "
            "de los NO fondos permanentes (PAREADO / SIIF_SIN_SGF / "
            f"SGF_SIN_SIIF). Exportado en [Google Sheet]({URL_SHEET})."
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
        df = get_control_otros_gastos_cruce_resto(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info(
                "Sin datos persistidos para el ejercicio/filtro seleccionado. "
                "Use el botón 'Actualizar' (Ejecutar u Omitir) para "
                "recalcular y congelar el cruce resto."
            )

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "estado",
            "siif_nro_comprobante",
            "sgf_libramiento",
        ]

        # Generamos el orden dinámico: todas las de la vista que no estén
        # en la lista negra ni en CAMPOS_OCULTOS (id/_id se ocultan en la
        # grilla)
        orden_dinamico = first_cols + [
            col
            for col in df.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_otros_gastos_cruce_resto",
            column_order=orden_dinamico,
            columnas_importe=("siif_importe", "sgf_importe_bruto", "dif"),
        )

        # Franja de subtotales: siempre visible fuera de la grilla.
        _render_subtotales_cruce_resto(df)


if __name__ == "__main__":
    render()

