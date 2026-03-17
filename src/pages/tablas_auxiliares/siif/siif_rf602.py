import streamlit as st
from playwright.async_api import async_playwright

from src.automation.siif.rf602 import Rf602
from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.services.api_client import post_request
from src.views.aux_tables import report_template


@st.dialog("Credenciales SIIF")
# --------------------------------------------------
def request_credentials_modal():
    st.write("Ingrese sus credenciales de SIIF para iniciar la descarga.")
    username = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")

    if st.button("Iniciar Automatización"):
        if not username or not password:
            st.error("Debe ingresar usuario y contraseña.")
            return

        ejercicios = st.session_state.get("ejercicios_rf602", [])
        if not ejercicios:
            st.error("No hay ejercicios seleccionados.")
            return

        # Ensure we have a list of integers
        if isinstance(ejercicios, int):
            ejercicios = [ejercicios]

        try:
            with st.spinner("Ejecutando automatización..."):
                import asyncio
                import sys

                # SOLUCIÓN PARA WINDOWS
                if sys.platform == "win32":
                    asyncio.set_event_loop_policy(
                        asyncio.WindowsProactorEventLoopPolicy()
                    )

                async def run_automation():
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
                            df_clean = await rf602.download_and_process_report(
                                ejercicio=ej
                            )
                            if df_clean is not None and not df_clean.empty:
                                # Send to backend
                                json_data = df_clean.to_dict(orient="records")
                                response = post_request(
                                    Endpoints.SIIF_RF602.value, json_body=json_data
                                )
                                results.append(f"Ejercicio {ej}: {response}")

                        await rf602.logout()
                        return results

                # En lugar de crear un loop manual con new_event_loop(),
                # usá asyncio.run() que es más limpio y maneja el cierre del loop.
                try:
                    results = asyncio.run(run_automation())
                except RuntimeError:
                    # Si ya hay un loop corriendo (común en Streamlit)
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    results = loop.run_until_complete(run_automation())

                st.success(f"Proceso finalizado: {len(results)} reportes procesados.")
                st.rerun()

        except Exception as e:
            st.error(f"Error durante la automatización: {e}")


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
        on_update=request_credentials_modal,
    )
