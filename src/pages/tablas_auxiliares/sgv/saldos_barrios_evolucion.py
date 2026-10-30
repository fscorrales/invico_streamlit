from typing import Any

import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

from src.automation.sgv.saldos_barrios_evolucion import SaldosBarriosEvolucion
from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ejercicios_list, post_request
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_sgv_credentials_modal,
)

ENDPOINT = Endpoints.SALDOS_BARRIOS_EVOLUCION.value
REPORTE = "saldos_barrios_evolucion"


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_sgv_barrios_saldo_evolucion(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    df = fetch_dataframe(ENDPOINT, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cod_barrio"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
async def run_automation(username: str, password: str, reporte: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    async with async_playwright() as p:
        sgv = SaldosBarriosEvolucion()
        await sgv.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await sgv.go_to_specific_report()

        results = []
        for ej in ejercicios:
            df_clean = await sgv.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(ENDPOINT, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await sgv.logout()
        return results


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-2],
        },
    ]

    report_template(
        key=REPORTE,
        title="SGV - Saldos por Barrios (evolución)",
        endpoint=ENDPOINT,
        description="Saldos por Barrios del Sistema Recuperos",
        filters_config=mis_filtros,
        update_func=lambda: request_sgv_credentials_modal(run_automation, key=REPORTE),
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
        df = get_sgv_barrios_saldo_evolucion(
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
            key=f"{REPORTE}_df_saldos_barrios_evolucion",
            column_order=orden_dinamico,
        )
