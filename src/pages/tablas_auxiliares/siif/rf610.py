"""Página: SIIF RF610.

Muestra el DataFrame del reporte RF610 del SIIF obtenido vía
GET /siif/rf610/ con filtro por ejercicio fiscal.
"""

import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rf610 import Rf610
from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.services.api_client import post_request
from src.views.aux_tables import report_template
from src.views.modal_siif import request_credentials_modal


# --------------------------------------------------
async def run_rf610_automation(username: str, password: str) -> None:
    ejercicios = st.session_state.get("ejercicios_rf610", [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    async with async_playwright() as p:
        rf610 = Rf610()
        # The Rf610 class handles login via SIIFReportManager.login
        await rf610.login(
            username=username,
            password=password,
            playwright=p,
            headless=False,
        )
        await rf610.go_to_reports()

        results = []
        for ej in ejercicios:
            df_clean = await rf610.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF610.value, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await rf610.logout()
        return results


# --------------------------------------------------
def render() -> None:
    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_rf610",
            "default": get_ejercicios_list()[-1],
        },
        # {
        #     "label": "Unidades Ejecutoras",
        #     "options": ["Educación", "Salud", "Seguridad", "Obras"],
        #     "query_param": "unidad_id",
        #     "key": "ms_unidades",
        #     "default": ["Salud"]
        # }
    ]

    report_template(
        key="rf610",
        title="SIIF - Reporte RF610",
        endpoint=Endpoints.SIIF_RF610.value,
        description="Ejecución presupuestaria con descripciones de programas, subprogramas, proyectos y actividades. Datos del SIIF.",
        filters_config=mis_filtros,
        on_update=lambda: request_credentials_modal(run_rf610_automation),
    )
