import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rog01 import Rog01
from src.constants.endpoints import Endpoints
from src.constants.options import get_grupos_partidas_str_siif_list
from src.services.api_client import post_request
from src.views.aux_tables import report_template
from src.views.modals import request_siif_credentials_modal

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
        on_update=lambda: request_siif_credentials_modal(run_automation),
    )
