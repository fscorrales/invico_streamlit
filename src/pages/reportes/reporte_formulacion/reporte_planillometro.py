"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Reportes base para la formulación presupuestaria
Data required:
    - Icaro
    - SIIF rf602
    - SIIF rf610
    - SIIF ri102
    - SIIF rfp_p605b
    - SSCC ctas_ctes
    - Planillomtro Histórico (Patricia)
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_ejercicios, get_reporte_formulacion_planillometro
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPONT = Endpoints.REPORTE_FORMULACION_PLANILLOMETRO.value
REPORTE = "reporte_formulacion_planillometro"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1hJyBOkA8sj5otGjYGVOzYViqSpmv_b4L8dXNju_GJ5Q/edit?gid=793724089#gid=793724089"


# --------------------------------------------------
def render(automation_func: Optional[Any] = None) -> None:

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
        description=f"La automatización y la exportación impactan en los 4 subreportes/pestañas. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            automation_func, key=REPORTE
        ),
        export_endpoint=Endpoints.REPORTE_FORMULACION.value + "/export",
        has_advanced_filter=False,
        max_selections=1,  # Limitar a un solo ejercicio por vez
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
        df = get_reporte_formulacion_planillometro(
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
            key=f"{REPORTE}_df_reporte_formulacion_planillometro",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
