import datetime as dt

import streamlit as st

from src.constants.endpoints import Endpoints
from src.services.api_client import fetch_data


@st.cache_data
# --------------------------------------------------
def get_ejercicios_list() -> list[int]:
    return list(range(2010, dt.date.today().year + 1))


@st.cache_data
# --------------------------------------------------
def get_tipos_comprobantes_siif_list() -> list[str]:
    return fetch_data(Endpoints.SIIF.value + "/tiposComprobantes")


@st.cache_data
# --------------------------------------------------
def get_grupos_partidas_siif_list() -> list[str]:
    return fetch_data(Endpoints.SIIF.value + "/gruposPartidas")


@st.cache_data
# --------------------------------------------------
def get_partidas_principales_siif_list() -> list[str]:
    return fetch_data(Endpoints.SIIF.value + "/partidasPrincipales")
