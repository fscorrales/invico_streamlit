import os
import subprocess
import sys

import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.services import get_sscc_banco_invico
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_sscc_credentials_modal,
)

ENDPONT = Endpoints.SSCC_BANCO_INVICO.value
REPORTE = "banco_invico"


# --------------------------------------------------
def run_automation(username: str, password: str) -> None:
    ejercicios = st.session_state.get("ejercicios_" + REPORTE, [])
    if not ejercicios:
        st.error("No hay ejercicios seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(ejercicios, int):
        ejercicios = [ejercicios]

    ejercicios_str = ",".join(map(str, ejercicios))

    # En lugar de la ruta al archivo, usamos el nombre del módulo
    # Esto equivale a hacer: python -m src.automation.sscc.banco_invico_runner
    modulo_runner = "src.automation.sscc.banco_invico_runner"

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            modulo_runner,
            username,
            password,
            st.session_state.get("token"),
            ejercicios_str,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )
    return process


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
        title="SSCC - Reporte " + REPORTE,
        endpoint=ENDPONT,
        description="",
        filters_config=mis_filtros,
        update_func=lambda: request_sscc_credentials_modal(run_automation),
    )

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
    try:
        df = get_sscc_banco_invico(
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
        first_cols = ["ejercicio", "mes", "fecha", "cta_cte", "importe"]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_banco_invico",
            column_order=orden_dinamico,
        )
