import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_icaro_estructuras
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views.aux_tables import report_template_with_uploader

ENDPONT = Endpoints.ICARO_ESTRUCTURAS.value
REPORTE = "icaro_estructuras"


# --------------------------------------------------
def render() -> None:

    report_template_with_uploader(
        key=REPORTE,
        title="Icaro - Reporte " + REPORTE,
        description="Tabla de Estructuras Presupuestarias de ICARO",
        endpoint=ENDPONT,
        has_export=True,
        has_upload=False,
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
    try:
        df = get_icaro_estructuras(
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
            "estructura",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_icaro_estructuras",
            column_order=orden_dinamico,
        )
