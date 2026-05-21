import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rog01 import Rog01
from src.constants.endpoints import Endpoints
from src.constants.options import get_grupos_partidas_str_siif_list
from src.services import get_siif_rog01, post_request
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    dataframe_with_buttons,
    report_template,
    request_siif_credentials_modal,
)

ENDPONT = Endpoints.SIIF_ROG01.value
REPORTE = "rog01"
GRUPOS = [element + "00" for element in get_grupos_partidas_str_siif_list()]


# --------------------------------------------------
async def run_automation(username: str, password: str) -> None:

    async with async_playwright() as p:
        siif = Rog01()
        await siif.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await siif.go_to_reports()

        results = []
        df_clean = await siif.download_and_process_report()
        if df_clean is not None and not df_clean.empty:
            # Send to backend
            json_data = df_clean.to_dict(orient="records")
            response = post_request(ENDPONT, json_body=json_data)
            results.append(f"Reporte: {response}")

        await siif.logout()
        return results


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija el Grupo de Partidas",
            "options": GRUPOS,
            "query_param": "grupo",
            "key": "grupos_" + REPORTE,
            "default": GRUPOS[:4],
        },
    ]

    report_template(
        key=REPORTE,
        title="SIIF - Reporte " + REPORTE,
        endpoint=ENDPONT,
        description="Detalle de Partidas Presupuestarias",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(run_automation),
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    actual = st.session_state.get(f"{REPORTE}_uploader_iteration")
    trigger = st.session_state[f"{REPORTE}_uploader_iteration"] = (
        0 if actual is None else actual + 1
    )
    try:
        df = get_siif_rog01(
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
        first_cols = ["grupo", "part_parcial", "partida"]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe_with_buttons(
            df,
            key=f"{REPORTE}_df_rog01",
            column_order=orden_dinamico,
            show_buttons=False,
        )
