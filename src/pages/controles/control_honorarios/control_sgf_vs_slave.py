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
from src.services import fetch_dataframe, get_ejercicios
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_sscc_and_sgf_credentials_modal,
)

ENDPONT = Endpoints.CONTROL_HONORARIOS.value
REPORTE = "control_sgf_vs_slave"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1fQhp1CdESnvqzrp3QMV5bFSHmGdi7SNoaBRWtmw-JgA"


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_sgf_vs_slave(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(ENDPONT + "/computeSGFVsSlave", params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
def render(
    automation_func: Optional[Any] = None,
) -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title=REPORTE.replace("_", " ").title(),
        endpoint=ENDPONT,
        description=f"Cruce de SGF vs SLAVE. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_sscc_and_sgf_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF: rcg01_uejp y rpa03g. SSCC's Resumen General de Movimientos y ctas_ctes. SGF: Resumen de Rendiciones Proveedores. SLAVE debe ser actualizado en el menu tablas auxiliares.",
        ),
        max_selections=1,
        export_endpoint=ENDPONT + "/export",
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
        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_sgf_vs_slave",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
