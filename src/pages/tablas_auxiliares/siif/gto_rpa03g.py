import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.gto_rpa03g import GtoRpa03g
from src.constants.endpoints import Endpoints
from src.constants.options import (
    get_ejercicios_list,
    get_grupos_partidas_str_siif_list,
)
from src.services import get_siif_gto_rpa03g, post_request
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    dataframe_with_buttons,
    report_template,
    request_siif_credentials_modal,
)

ENDPONT = Endpoints.SIIF_GTO_RPA03G.value
REPORTE = "gto_rpa03g"
GRUPOS = get_grupos_partidas_str_siif_list()


# --------------------------------------------------
async def run_automation(username: str, password: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    grupos = st.session_state.get("grupos_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    if isinstance(grupos, int):
        grupos = [grupos]

    async with async_playwright() as p:
        siif = GtoRpa03g()
        # The Rfondos04 class handles login via SIIFReportManager.login
        await siif.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await siif.go_to_reports()

        results = []
        for ej in ejercicios:
            for grupo in grupos:
                df_clean = await siif.download_and_process_report(
                    ejercicio=ej, grupo_partida=grupo
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(ENDPONT, json_body=json_data)
                    results.append(f"Ejercicio {ej}: {response}")

        await siif.logout()
        return results


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
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
        description="Ejecución de Gastos del Ejercicio por Grupo de Partidas",
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
        df = get_siif_gto_rpa03g(
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
            "nro_comprobante",
            "importe",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe_with_buttons(
            df,
            key=f"{REPORTE}_df_gto_rpa03g",
            column_order=orden_dinamico,
            show_buttons=False,
        )
