import os
import subprocess
import sys

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import get_ejercicios, get_sgf_origenes, get_sgf_resumen_rend_prov
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.views import (
    report_template,
    request_sgf_credentials_modal,
)

ENDPONT = Endpoints.SGF_RESUMEN_REND_PROV.value
REPORTE = "sgf_resumen_rend_prov"
ORIGENES = get_sgf_origenes()


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

    origenes = st.session_state.get("origenes_" + REPORTE, [])
    if not origenes:
        st.error("No hay origenes seleccionados.")
        return

    # Ensure we have a list of integers
    if isinstance(origenes, str):
        origenes = [origenes]

    origenes_str = ",".join(map(str, origenes))

    modulo_runner = "src.automation.sgf.resumen_rend_prov_runner"

    is_frozen = getattr(sys, "frozen", False)

    if is_frozen:
        # En PRODUCCIÓN (.exe): Pasamos el flag genérico Y LUEGO el string del módulo
        args = [
            sys.executable,
            "--automation",
            modulo_runner,  # 🚀 Se convierte en sys.argv[1] antes de que el arranque lo limpie
            username,
            password,
            st.session_state.get("token", ""),
            ejercicios_str,
            origenes_str,
        ]
    else:
        # En DESARROLLO (.py): Tu comando tradicional por consola con -m
        args = [
            sys.executable,
            "-m",
            modulo_runner,
            username,
            password,
            st.session_state.get("token", ""),
            ejercicios_str,
            origenes_str,
        ]

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process = subprocess.Popen(
        args,
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )
    process.wait()  # Esperamos a que termine el proceso antes de continuar
    return process


# --------------------------------------------------
def render() -> None:

    mis_filtros = [
        {
            "label": "Elija los ejercicios a consultar",
            "options": get_ejercicios(),
            "query_param": "ejercicio",
            "key": "ejercicios_" + REPORTE,
            "default": get_ejercicios()[-1],
        },
        {
            "label": "Elija el/los origen/es",
            "options": ORIGENES,
            "query_param": "origen",
            "key": "origenes_" + REPORTE,
            "default": ORIGENES,
        },
    ]

    report_template(
        key=REPORTE,
        title="Reporte " + REPORTE.replace("_", " ").title(),
        endpoint=ENDPONT,
        description="",
        filters_config=mis_filtros,
        update_func=lambda: request_sgf_credentials_modal(run_automation, key=REPORTE),
    )

    if st.session_state.get(f"{REPORTE}_automation_success"):
        # Limpiamos el flag para que no entre en bucle infinito
        st.session_state[f"{REPORTE}_automation_success"] = False

        # Incrementamos el trigger de forma síncrona y segura
        actual = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)
        st.session_state[f"{REPORTE}_uploader_iteration"] = actual + 1

        # Forzamos el recálculo total de la página con el nuevo trigger
        st.rerun()

    # Capturamos el filtro del session_state (que el fragmento actualizó)
    filtro_actual = st.session_state.get(f"{REPORTE}_advanced_filter", "")
    trigger = st.session_state.get(f"{REPORTE}_uploader_iteration", 0)

    # 1. Inicializamos df con un DataFrame vacío para evitar el UnboundLocalError
    df = pd.DataFrame()

    try:
        df = get_sgf_resumen_rend_prov(
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
        first_cols = ["ejercicio", "mes", "fecha"]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col for col in df.columns if col not in first_cols
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_sgf_resumen_rend_prov",
            column_order=orden_dinamico,
        )
