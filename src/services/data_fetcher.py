__all__ = [
    "get_siif_rf602",
    "get_siif_rog01",
    "get_siif_rvicon03",
    "get_siif_ri102",
    "get_siif_rci02",
    "get_siif_rfp_p605b",
    "get_siif_rf610",
    "get_siif_rcg01_uejp",
    "get_siif_gto_rpa03g",
    "get_siif_rfondo07tp",
    "get_siif_rfondos04",
]

import pandas as pd
import streamlit as st

from src.constants import Endpoints
from src.services.api_client import fetch_dataframe


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rf602(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RF602.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rog01(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_ROG01.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["partida"],
            ascending=[True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rvicon03(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RVICON03.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cta_contable"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_ri102(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RI102.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "cod_recurso", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rci02(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RCI02.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_entrada"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfp_p605b(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFP_P605B.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura", "fuente"],
            ascending=[False, True, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rf610(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RF610.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "estructura"],
            ascending=[False, True],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rcg01_uejp(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RCG01_UEJP.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_comprobante"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_gto_rpa03g(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_GTO_RPA03G.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "nro_comprobante"],
            ascending=[False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfondo07tp(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFONDO07TP.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "tipo_comprobante", "nro_comprobante"],
            ascending=[False, False, False, False],
        )

    return df


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl="1d")
def get_siif_rfondos04(params: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    df = fetch_dataframe(Endpoints.SIIF_RFONDS04.value, params=params)
    if not df.empty:
        df = df.sort_values(
            ["ejercicio", "fecha", "tipo_comprobante", "nro_comprobante"],
            ascending=[False, False, False, False],
        )

    return df
