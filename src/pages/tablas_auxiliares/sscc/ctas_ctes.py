import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.constants.options import get_ctas_ctes_list
from src.services import get_sscc_ctas_ctes
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
)

ENDPONT = Endpoints.CTAS_CTES.value
REPORTE = "ctas_ctes"


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija la Cta. Cte. a consultar",
            "options": get_ctas_ctes_list(),
            "query_param": "cta_cte",
            "key": "ctas_ctes_" + REPORTE,
            "default": None,
        },
    ]

    report_template(
        key=REPORTE,
        title="SSCC - Reporte " + REPORTE,
        endpoint=ENDPONT,
        description="Unificador de Cuentas Corrientes",
        filters_config=mis_filtros,
        update_func=None,
        has_export=False,  # Asumo que este reporte no tiene exportación por ahora
        has_update=False,  # Asumo que este reporte no necesita actualización manual por ahora
        allow_no_filters=True,  # Permitimos que el usuario deje este filtro vacío
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
    try:
        df = get_sscc_ctas_ctes(
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
