"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Icaro vs SIIF budget execution
Data required:
    - Icaro
    - SIIF rf602
    - SIIF rf610
    - SIIF gto_rpa03g
    - SIIF rcg01_uejp
    - SIIF rfondo07tp
    - SSCC ctas_ctes (manual data)
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.automation.analysis import control_icaro
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_ICARO.value
REPORTE = "control_icaro_anual"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1KKeeoop_v_Nf21s7eFp4sS6SmpxRZQ9DPa1A5wVqnZ0"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo / correlativo SQL). Se excluyen de ``column_order``, lo que hace
# que Streamlit las oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_icaro_anual(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    # Lee el snapshot persistido (POST posterior a /computeControlAnual)
    # en la colección control_icaro_anual, igual que el resto de los
    # controles. El cómputo on-demand vive en /control/controlIcaro/
    # computeControlAnual, al que solo llama
    # compute_control_icaro_anual() (Ejecutar u Omitir).
    df = fetch_dataframe(Endpoints.CONTROL_ICARO_ANUAL.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
def run_skip(reporte: str) -> list[str]:
    """
    Omite la descarga de reportes (SIIF) y recalcula el Control Anual
    con los datos ya presentes en la API.

    Args:
        reporte: Clave del reporte (p.ej. ``control_icaro_anual``)
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

    # Solo recalculamos: sin sync_control_icaro_from_siif().
    # compute_control_icaro_anual() pide el control al backend
    # (GET /control/controlIcaro/computeControlAnual) y sincroniza la
    # colección control_icaro_anual con un POST por ejercicio.
    return control_icaro.compute_control_icaro_anual(ejercicios=ejercicios)


# --------------------------------------------------
def render(
    automation_func: Optional[Any] = None,
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
        description=f"La automatización y la exportación impactan en los 3 subreportes/pestañas. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF's rf602, rf610, gto_rpa03g, rcg01_uejp y rfondo07tp",
            skip_callback=(lambda: run_skip(REPORTE)) if run_skip else None,
        ),
        export_endpoint=Endpoints.CONTROL_ICARO.value + "/export",
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
        df = get_control_icaro_anual(
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

    # 4. Mostrar resultados (usando session_state para que no desaparezcan)
    if not df.empty:
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col
            for col in df.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_icaro_anual",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
