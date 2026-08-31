from datetime import datetime

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, process_slave_honorarios
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import report_template_with_uploader

ENDPONT = Endpoints.SLAVE_HONORARIOS.value
REPORTE = "slave_honorarios"

ayuda_uploader = """
### 📥 Guía de Importación
Simplemente importe el archivo Slave.accdb (es necesario convertirlo desde su versión antigua .mdb a una más moderna .accdb dentro de Access)
"""


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_slave_honorarios(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    if filtro_avanzado == "":
        filtro_avanzado = f"ejercicio={datetime.today().year}"

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    df = fetch_dataframe(Endpoints.SLAVE_HONORARIOS.value, params=params_peticion)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
def render() -> None:

    report_template_with_uploader(
        key=REPORTE,
        title="Slave - Tabla Honorarios",
        description="Tabla Honorarios de Slave",
        endpoint=ENDPONT,
        has_export=True,
        has_upload=True,
        uploader_help=ayuda_uploader,
        uploader_func=process_slave_honorarios,
        upload_file_type="accdb",
        upload_table_name="LIQUIDACIONHONORARIOS",
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
        df = get_slave_honorarios(
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
        first_cols = ["ejercicio"]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_slave_honorarios",
            column_order=orden_dinamico,
        )
