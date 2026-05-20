__all__ = [
    "get_rf602",
]

import pandas as pd
import streamlit as st

from src.constants import Endpoints
from src.services.api_client import fetch_dataframe


# --------------------------------------------------
@st.cache_data(show_spinner="Consultando base de datos...", ttl=3600)
def get_rf602(filtro_avanzado: str = "", update_trigger: int = 0):
    df = pd.DataFrame()

    params_peticion = {
        "limit": 0,
        "queryFilter": filtro_avanzado,
    }

    # Tabla Certificados
    df = fetch_dataframe(Endpoints.SIIF_RF602.value, params=params_peticion)
    # if not df.empty:
    #     df = df.loc[df["id_carga"] == ""]
    #     df = df.sort_values(
    #         ["beneficiario", "desc_obra", "nro_certificado"],
    #         ascending=True,
    #     )

    return df
