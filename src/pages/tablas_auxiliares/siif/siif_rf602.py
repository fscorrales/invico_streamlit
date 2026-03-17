import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rf602 import Rf602
from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.services.api_client import post_request
from src.views.aux_tables import report_template
from src.views.modal_siif import request_credentials_modal


# --------------------------------------------------
async def run_rf602_automation(username: str, password: str) -> None:
    ejercicios = st.session_state.get("ejercicios_rf602", [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    async with async_playwright() as p:
        rf602 = Rf602()
        # The Rf602 class handles login via SIIFReportManager.login
        await rf602.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await rf602.go_to_reports()

        results = []
        for ej in ejercicios:
            df_clean = await rf602.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF602.value, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await rf602.logout()
        return results


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_rf602",
            "default": get_ejercicios_list()[-1],
        },
    ]

    report_template(
        key="rf602",
        title="SIIF - Reporte RF602",
        endpoint=Endpoints.SIIF_RF602.value,
        description="Ejecución presupuestaria por estructura programática y "
        "partida. Datos extraídos del Sistema Integrado de "
        "Información Financiera (SIIF).",
        filters_config=mis_filtros,
        on_update=lambda: request_credentials_modal(run_rf602_automation),
    )
