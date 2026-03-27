import os
from pathlib import Path

import streamlit as st

from src.automation.sscc.banco_invico import BancoINVICO
from src.automation.sscc.connect_sscc import login
from src.constants.endpoints import Endpoints
from src.constants.options import get_ejercicios_list
from src.services.api_client import post_request
from src.utils.handling_path import get_download_sscc_path
from src.views.aux_tables import report_template
from src.views.modals import request_sscc_credentials_modal

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

    # save_path = st.session_state.get("save_path", None)
    # if save_path is None:
    #     st.error("No se ha seleccionado una carpeta de descarga.")
    #     return

    save_path = Path(os.path.join(get_download_sscc_path(), "Banco INVICO"))

    # Verifica si la carpeta NO existe, y la crea
    if not os.path.exists(save_path):
        # exist_ok=True evita errores si la carpeta se creó justo un milisegundo antes
        os.makedirs(save_path, exist_ok=True)

    with login(username, password) as conn:
        banco_invico = BancoINVICO(sscc=conn)
        results = []
        for ejercicio in ejercicios:
            banco_invico.download_report(dir_path=save_path, ejercicios=str(ejercicio))
            filename = str(ejercicio) + "-bancoINVICO.csv"
            banco_invico.read_csv_file(Path(os.path.join(save_path, filename)))
            banco_invico.process_dataframe()
            df_clean = banco_invico.clean_df
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(ENDPONT, json_body=json_data)
                results.append(f"Ejercicio {ejercicio}: {response}")

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
        title="SSCC - Reporte " + REPORTE,
        endpoint=ENDPONT,
        description="",
        filters_config=mis_filtros,
        on_update=lambda: request_sscc_credentials_modal(run_automation),
    )
