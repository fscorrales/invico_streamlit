"""Página: Otros Gastos - Cruce Fondos Permanentes (mensual).

Capa 2 del cruce SIIF <-> SGF: control mes a mes de los fondos
permanentes (SIIF rendido vs SGF pagado, con acumulados).
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.pages.controles.control_otros_gastos.subtotales import render_subtotales
from src.services import get_control_otros_gastos_cruce_mensual, get_ejercicios_list
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
REPORTE = "control_otros_gastos_cruce_mensual"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1EBzBz17mtVzBmpAFznDyJf2RAJNspQyJQJaRD_WI5dE"
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
def _render_subtotales_cruce_fondos(df: pd.DataFrame) -> None:
    """Franja de subtotales del mensual de fondos permanentes.

    Los acumulados (``siif_acum``/``sgf_acum``/``dif_acum``/``dif_pct``)
    se toman de la ÚLTIMA fila (son acumulados, no se suman); los
    rendido/pagado sí se suman sobre todas las filas visibles.

    Args:
        df: DataFrame mensual (``siif_rendido``, ``sgf_pagado``,
            ``dif_acum``, ``dif_pct``).
    """
    columnas_requeridas = {"siif_rendido", "sgf_pagado"}
    if not columnas_requeridas.issubset(df.columns):
        return

    total_rendido: float = df["siif_rendido"].apply(parse_moneda_ar).sum()
    total_pagado: float = df["sgf_pagado"].apply(parse_moneda_ar).sum()

    items: list[tuple[str, str, str]] = [
        (
            "SIIF Rendido",
            formato_moneda_us(total_rendido),
            "Suma de siif_rendido de todos los meses visibles",
        ),
        (
            "SGF Pagado",
            formato_moneda_us(total_pagado),
            "Suma de sgf_pagado de todos los meses visibles",
        ),
    ]

    if "dif_acum" in df.columns and len(df):
        dif_acum = df["dif_acum"].iloc[-1]
        items.append(
            (
                "Dif. Acumulada",
                formato_moneda_us(parse_moneda_ar(dif_acum)),
                "dif_acum del último mes (siif_acum - sgf_acum)",
            )
        )

    if "dif_pct" in df.columns and len(df):
        dif_pct = df["dif_pct"].iloc[-1]
        valor = "—" if dif_pct is None or pd.isna(dif_pct) else f"{dif_pct:.2f}%"
        items.append(
            (
                "Dif. %",
                valor,
                "dif_pct del último mes (dif_acum sobre el SGF acumulado)",
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
        title="Otros Gastos - Cruce Fondos Permanentes",
        endpoint=ENDPOINT,
        description=(
            "La actualización (Ejecutar u Omitir) y la exportación "
            "impactan en las 4 pestañas. Capa 2 del cruce: control "
            "mensual de fondos permanentes (SIIF rendido vs SGF "
            f"pagado, con acumulados). Exportado en [Google Sheet]({URL_SHEET})."
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
        df = get_control_otros_gastos_cruce_mensual(
            filtro_actual,
            update_trigger=trigger,
        )

        if df.empty:
            st.info(
                "Sin datos persistidos para el ejercicio/filtro seleccionado. "
                "Use el botón 'Actualizar' (Ejecutar u Omitir) para "
                "recalcular y congelar el cruce de fondos permanentes."
            )

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")

    # 2. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
            "mes",
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
            key=f"{REPORTE}_df_control_otros_gastos_cruce_fondos",
            column_order=orden_dinamico,
            columnas_importe=(
                "siif_rendido",
                "sgf_pagado",
                "dif_mes",
                "siif_acum",
                "sgf_acum",
                "dif_acum",
            ),
        )

        # Franja de subtotales: siempre visible fuera de la grilla.
        _render_subtotales_cruce_fondos(df)


if __name__ == "__main__":
    render()

