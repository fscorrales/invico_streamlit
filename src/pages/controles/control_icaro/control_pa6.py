"""
Author: Fernando Corrales <fscpython@gmail.com>
Purpose: Icaro vs SIIF budget execution
Data required:
    - Icaro
    - SIIF rf602
    - SIIF rf610
    - SIIF gto_rpa03g
    - SIIF rcg01_uejp
    - SIIF rfondo07tp
    - SSCC ctas_ctes (manual data)
"""

from typing import Any, Optional

import pandas as pd
import streamlit as st

from src.components import dataframe
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ejercicios_list
from src.utils import (
    APIConnectionError,
    APIResponseError,
)
from src.utils.transform_data import formato_moneda_ar, parse_moneda_ar
from src.views import (
    report_template,
    request_siif_credentials_modal,
)

ENDPOINT = Endpoints.CONTROL_ICARO.value
REPORTE = "control_icaro_pa6"
URL_SHEET = "https://docs.google.com/spreadsheets/d/1KKeeoop_v_Nf21s7eFp4sS6SmpxRZQ9DPa1A5wVqnZ0"
# Columnas del DataFrame que NO se muestran en la grilla (id interno de
# Mongo / correlativo SQL). Se excluyen de ``column_order``, lo que hace
# que Streamlit las oculte sin perderlas del DataFrame.
CAMPOS_OCULTOS: tuple[str, ...] = ("id", "_id")


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_control_icaro_pa6(
    params: dict[str, Any] | None = None, update_trigger: int = 0
):
    df = pd.DataFrame()

    # Lee el snapshot persistido (POST posterior a /computeControlPA6)
    # en la colección control_icaro_pa6, igual que el resto de los
    # controles. El cómputo on-demand vive en /control/controlIcaro/
    # computeControlPA6, al que solo llama
    # compute_control_icaro_pa6() (Ejecutar u Omitir).
    df = fetch_dataframe(Endpoints.CONTROL_ICARO_PA6.value, params=params)
    # if not df.empty:
    #     df = df.sort_values(
    #         ["ejercicio", "mes", "grupo", "cta_cte"],
    #         ascending=[False, True, True, True],
    #     )

    return df


# --------------------------------------------------
def render(
    automation_func: Optional[Any] = None,
    skip_func: Optional[Any] = None,
) -> None:

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
        title=REPORTE.replace("_", " ").title(),
        endpoint=ENDPOINT,
        description=f"La automatización y la exportación impactan en los 3 subreportes/pestañas. Datos exportados en [Google Sheet]({URL_SHEET}).",
        filters_config=mis_filtros,
        update_func=lambda: request_siif_credentials_modal(
            automation_func,
            key=REPORTE,
            downloaded_info="SIIF's rf602, rf610, gto_rpa03g, rcg01_uejp y rfondo07tp",
            skip_callback=(lambda: skip_func(REPORTE)) if skip_func else None,
        ),
        export_endpoint=Endpoints.CONTROL_ICARO.value + "/export",
        max_selections=1,
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
        df = get_control_icaro_pa6(
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
        # Formato moneda AR ($ 1.234,56) para los importes visibles de la
        # grilla. ``parse_moneda_ar`` (franja de totales) es el inverso de
        # ``formato_moneda_ar`` y acepta tanto el número crudo de la API
        # como la cadena ya formateada, por lo que los totales siguen
        # cuadrando con lo que muestra la grilla. El df proviene de
        # ``@st.cache_data`` (copia deserializada por llamada), por lo que
        # mutarlo en el lugar es seguro. Los nulos quedan en blanco y la
        # pasada extra por ``parse_moneda_ar`` hace el formateo idempotente
        # ante cadenas ya formateadas.
        for columna_moneda in (
            "siif_importe_pa6",
            "icaro_importe_pa6",
            "siif_importe_reg",
            "icaro_importe_reg",
        ):
            if columna_moneda in df.columns:
                df[columna_moneda] = df[columna_moneda].apply(
                    lambda valor: (
                        formato_moneda_ar(parse_moneda_ar(valor))
                        if pd.notna(valor)
                        else ""
                    )
                )

        # Definimos las columnas que NO queremos mostrar
        first_cols = [
            "ejercicio",
        ]

        # Generamos el orden dinámico: todas las del DF que no estén en la lista negra
        orden_dinamico = first_cols + [
            col
            for col in df.columns
            if col not in first_cols and col not in CAMPOS_OCULTOS
        ]

        dataframe(
            df,
            key=f"{REPORTE}_df_control_icaro_pa6",
            column_order=orden_dinamico,
        )


if __name__ == "__main__":
    render()
