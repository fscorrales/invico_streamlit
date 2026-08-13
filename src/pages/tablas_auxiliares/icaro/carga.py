import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_ejercicios, get_icaro_carga
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views.aux_tables import report_template

ENDPONT = Endpoints.ICARO_CARGA.value
REPORTE = "icaro_carga"


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija el Ejercicio a consultar",
            "options": get_ejercicios(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title="ICARO - Reporte " + REPORTE,
        endpoint=ENDPONT,
        description="Tabla de Carga de Datos en ICARO",
        filters_config=mis_filtros,
        update_func=None,
        has_update=False,  # Asumo que este reporte no necesita actualización manual por ahora
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        df = get_icaro_carga(
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
            "mes",
            "fecha",
            "fuente",
            "nro_comprobante",
            "tipo",
            "actividad",
            "partida",
            "importe",
            "cta_cte",
            "cuit",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_icaro_carga",
            column_order=orden_dinamico,
        )
