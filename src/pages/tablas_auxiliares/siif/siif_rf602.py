"""Página: SIIF RF602.

Muestra el DataFrame del reporte RF602 del SIIF obtenido vía
GET /siif/rf602/ con filtro por ejercicio fiscal.
"""

import datetime as dt

import pandas as pd
import streamlit as st

from src.components.buttons import button_export, button_update
from src.components.multiselects import multiselect_filter
from src.components.text_inputs import text_input_advance_filter
from src.services.api_client import (
    APIConnectionError,
    APIResponseError,
    fetch_dataframe,
)

ENDPOINT = "/siif/rf602/"


def render() -> None:
    st.markdown("# SIIF - Reporte RF602")
    st.write(
        "Ejecución presupuestaria por estructura programática y "
        "partida. Datos extraídos del Sistema Integrado de "
        "Información Financiera (SIIF)."
    )

    # --- Filtros y Actualización ---
    with st.container(horizontal=True, vertical_alignment="bottom"):
        ejercicios = multiselect_filter(
            "Elija los ejercicios a consultar",
            list(range(2010, dt.date.today().year + 1)),
            dt.date.today().year,
        )
        filtro_avanzado = text_input_advance_filter()
        button_update("Actualizar desde SIIF")
        # st.info(
        #     "Automatización Playwright no implementada aún. "
        #     "Se lanzará el script de scraping del SIIF."
        # )
        button_export("Exportar a Excel y GS")

    # --- Carga y visualización de datos ---
    try:
        if not ejercicios:
            st.error("Favor de elegir al menos un ejercicio.")
            st.stop()
        with st.spinner("Cargando datos RF602..."):
            lista_ejercicios = ",".join(str(ejercicio) for ejercicio in ejercicios)
            print(f"Rf602: Fetching data for ejercicios {lista_ejercicios}...")
            df_acum = pd.DataFrame()
            for ejercicio in ejercicios:
                df = fetch_dataframe(
                    ENDPOINT,
                    params={
                        "ejercicio": ejercicio,
                        "limit": 0,
                        "queryFilter": filtro_avanzado,
                    },
                )
                df_acum = pd.concat([df_acum, df], ignore_index=True)

        if df_acum.empty:
            st.info(
                f"No se encontraron datos RF602 para los ejercicios {lista_ejercicios}."
            )
        else:
            # st.write(f"### Registros encontrados: {len(df_acum)}")
            st.dataframe(df_acum, width="stretch")

    except APIConnectionError as e:
        st.error(f"⚠️ Error de conexión: {e}")
    except APIResponseError as e:
        st.error(f"⚠️ Error de API: {e}")
