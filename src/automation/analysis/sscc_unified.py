import pandas as pd
import streamlit as st

from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ctas_ctes


# --------------------------------------------------
def get_banco_invico_unified_cta_cte(ejercicio: int = None) -> pd.DataFrame:
    """
    Get the Banco INVICO data from API.
    """
    params = {"ejercicio": ejercicio} if ejercicio else None
    params["limit"] = 0
    df = fetch_dataframe(Endpoints.SSCC_BANCO_INVICO.value, params=params)
    df.reset_index(drop=True, inplace=True)
    if not df.empty:
        # logger.info(f"df.shape: {df.shape} - df.head: {df.head()}")
        ctas_ctes = get_ctas_ctes(
            update_trigger=st.session_state.ctas_ctes_uploader_iteration
        )
        map_to = ctas_ctes.loc[:, ["map_to", "sscc_cta_cte"]]
        df = pd.merge(
            df, map_to, how="left", left_on="cta_cte", right_on="sscc_cta_cte"
        )
        df["cta_cte"] = df["map_to"]
        df.drop(["map_to", "sscc_cta_cte"], axis="columns", inplace=True)
        # logger.info(f"df.shape: {df.shape} - df.head: {df.head()}")
    return df
