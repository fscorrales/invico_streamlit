"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Haberes vs SSCC
Data required:
    - SIIF rcg01_uejp
    - SIIF rpa03g
    - SIIF rdeu012
    - SIIF rcocc31 (2122-1-2)
    - SSCC Resumen General de Movimientos
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1A9ypUkwm4kfLqUAwr6-55crcFElisOO9fOdI6iflMAc
"""

from typing import Any

import pandas as pd
import streamlit as st

from src.automation.analysis import control_haberes
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ejercicios
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_and_sscc_credentials_modal,
)

ENDPONT = Endpoints.CONTROL_HABERES.value
REPORTE = "control_haberes"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1A9ypUkwm4kfLqUAwr6-55crcFElisOO9fOdI6iflMAc"


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_haberes(params: dict[str, Any] | None = None, update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(ENDPONT + "/compute", params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
async def run_automation(
    siif_username: str,
    siif_password: str,
    sscc_username: str,
    sscc_password: str,
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
    results = await control_haberes.sync_control_haberes_from_siif(
        siif_username=siif_username,
        siif_password=siif_password,
        ejercicios=ejercicios,
    )

    # 2.b. Ejecutamos el módulo runner de SSCC en un proceso separado
    control_haberes.sync_control_haberes_from_sscc(
        sscc_username=sscc_username,
        sscc_password=sscc_password,
        ejercicios=ejercicios,
        token=st.session_state.get("token"),
    )
    results.append("SSCC ejecutado correctamente.")

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
        description=f"SIIF Haberes vs SSCC. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_and_sscc_credentials_modal(
            run_automation,
            key=REPORTE,
            downloaded_info="SIIF's rdeu012, rcocc31 (2122-1-2), gto_rpa03g y rcg01_uejp. SSCC's Banco INVICO",
        ),
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
        df = get_control_haberes(
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
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_recursos",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
