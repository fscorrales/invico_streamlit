"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Recursos vs SSCC depósitos
Data required:
    - SIIF rcocc31
    - SIIF rci02
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1bZnvl9YkHC-N1HbIbnFNrqU3Iq03PG81u7fdHe_v_pw
"""

import pandas as pd
import streamlit as st

from src.automation.analysis import control_aporte_empresario
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_control_aporte_empresario, get_ejercicios
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPONT = Endpoints.CONTROL_APORTE_EMPRESARIO.value
REPORTE = "control_aporte_empresario"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1rbc5eMwJeW1fB5F5eKpczFmTrC6rpiJu89xTdhkWfZY"


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    reporte: str,
) -> None:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + reporte, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    # 2. Iniciamos la descarga automática
    results = []
    # 2.a. Ejecutamos la automatización de SIIF
    results = await control_aporte_empresario.sync_control_aporte_empresario_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    return results


# --------------------------------------------------
def render() -> None:

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
        description=f"Cruce de recursos SIIF vs Depósitos Bancarios por tipo de recurso y cta. cte. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="rci02 - rcocc31 (1112-2-6 y 2122-1-2)",
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
        df = get_control_aporte_empresario(
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
            key=f"{REPORTE}_df_control_aporte_empresario",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
