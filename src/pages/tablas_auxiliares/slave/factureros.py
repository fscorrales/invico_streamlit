import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_ctas_ctes, process_listado_ctas_ctes
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template_with_uploader,
)

ENDPONT = Endpoints.SLAVE_FACTUREROS.value
REPORTE = "slave_factureros"

ayuda_uploader = """
### 📥 Guía de Importación
Simplemente importe el archivo ctas_ctes.xlsx el cual debe contener las siguientes columnas...
"""


# --------------------------------------------------
def render() -> None:

    report_template_with_uploader(
        key=REPORTE,
        title="SSCC - Reporte " + REPORTE,
        description="Listado de Factureros SLAVE",
        endpoint=ENDPONT,
        has_export=True,
        has_upload=True,
        uploader_help=ayuda_uploader,
        uploader_func=process_listado_ctas_ctes,
        upload_file_type="xlsx",
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
        df = get_ctas_ctes(
            filtro_avanzado=filtro_actual,
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
            "map_to",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_ctas_ctes",
            column_order=orden_dinamico,
        )
