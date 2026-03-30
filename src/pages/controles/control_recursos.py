"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: SIIF Recursos vs SSCC depósitos
Data required:
    - SIIF rci02
    - SIIF ri102 (no obligatorio)
    - SSCC Consulta General de Movimiento
    - SSCC ctas_ctes (manual data)
Google Sheet:
    - https://docs.google.com/spreadsheets/d/1u_I5wN3w_rGX6rWIsItXkmwfIEuSox6ZsmKYbMZ2iUY
"""

import os
import subprocess
import sys

import streamlit as st

from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.views.aux_tables import report_template
from src.views.modals import request_siif_and_sscc_credentials_modal

ENDPONT = Endpoints.CONTROL_RECURSOS.value
REPORTE = "recursos"


# --------------------------------------------------
async def run_automation(
    siif_username: str, siif_password: str, sscc_username: str, sscc_password: str
) -> None:

    # 1. Obtenemos los ejercicios seleccionados en el estado de sesión
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    ejercicios_str = ",".join(map(str, ejercicios))

    # 2. Iniciamos la descarga automática
    results = []
    # 2.a. Ejecutamos el módulo runner de SSCC en un proceso separado
    modulo_runner = "src.automation.sscc.banco_invico_runner"

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    results = subprocess.Popen(
        [
            sys.executable,
            "-m",
            modulo_runner,
            sscc_username,
            sscc_password,
            st.session_state.get("token"),
            ejercicios_str,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )
    # 2.b. Ejecutamos la automatización de SIIF
    # async with async_playwright() as p:
    #     siif = Rf602()
    #     # The Rf602 class handles login via SIIFReportManager.login
    #     await siif.login(
    #         username=username,
    #         password=password,
    #         playwright=p,
    #         headless=False,
    #     )
    #     await siif.go_to_reports()

    #     results = []
    #     for ej in ejercicios:
    #         df_clean = await siif.download_and_process_report(ejercicio=ej)
    #         if df_clean is not None and not df_clean.empty:
    #             # Send to backend
    #             json_data = df_clean.to_dict(orient="records")
    #             response = post_request(ENDPONT, json_body=json_data)
    #             results.append(f"Ejercicio {ej}: {response}")

    #     await siif.logout()

    return results


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios_list(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios_list()[-1],
        },
    ]

    report_template(
        key=REPORTE,
        title="Control " + REPORTE.capitalize(),
        endpoint=ENDPONT,
        description="Cruce de recursos SIIF vs Depósitos Bancarios por tipo de recurso y cta. cte.",
        filters_config=mis_filtros,
        on_update=lambda: request_siif_and_sscc_credentials_modal(run_automation),
    )


if __name__ == "__main__":
    render()

# """Página: Control Recursos.

# Muestra el DataFrame del control de recursos obtenido vía
# GET /control/controlRecursos/ con filtro por ejercicio fiscal.
# """

# import streamlit as st

# from src.constants.endpoints import Endpoints
# from src.services.api_client import (
#     APIConnectionError,
#     APIResponseError,
#     fetch_dataframe,
# )

# ENDPOINT = Endpoints.CONTROL_RECURSOS.value


# st.markdown("# Control Recursos")
# st.write(
#     "Cruce de recursos SIIF vs depósitos bancarios. "
#     "Permite filtrar por ejercicio fiscal y actualizar los datos."
# )

# # --- Filtros y Actualización ---
# col1, col2 = st.columns([1, 3])
# with col1:
#     ejercicio = st.number_input(
#         "Ejercicio",
#         min_value=2010,
#         max_value=2030,
#         value=2025,
#         step=1,
#     )
# with col2:
#     st.write("")
#     st.write("")
#     if st.button("🔄 Actualizar desde fuentes"):
#         st.info(
#             "Automatización no implementada aún. Se lanzará el script correspondiente."
#         )

# # --- Carga y visualización de datos ---
# try:
#     with st.spinner("Cargando datos de Control Recursos..."):
#         df = fetch_dataframe(
#             ENDPOINT,
#             params={"ejercicio": ejercicio, "limit": None},
#         )

#     if df.empty:
#         st.info(f"No se encontraron datos para el ejercicio {ejercicio}.")
#     else:
#         st.write(f"### Registros encontrados: {len(df)}")
#         st.dataframe(df, width="stretch")

# except APIConnectionError as e:
#     st.error(f"⚠️ Error de conexión: {e}")
# except APIResponseError as e:
#     st.error(f"⚠️ Error de API: {e}")
