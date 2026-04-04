import pandas as pd

from src.constants.endpoints import Endpoints
from src.constants.options import get_ctas_ctes_df
from src.services.api_client import fetch_dataframe


# --------------------------------------------------
def get_siif_rci02_unified_cta_cte(ejercicio: int = None) -> pd.DataFrame:
    """
    Get the rci02 data from API.
    """
    params = {"ejercicio": ejercicio} if ejercicio else None
    params["limit"] = 0
    df = fetch_dataframe(Endpoints.SIIF_RCI02.value, params=params)
    # df.reset_index(drop=True, inplace=True)
    ctas_ctes = get_ctas_ctes_df()
    map_to = ctas_ctes.loc[:, ["map_to", "siif_recursos_cta_cte"]]
    df = pd.merge(
        df, map_to, how="left", left_on="cta_cte", right_on="siif_recursos_cta_cte"
    )
    df["cta_cte"] = df["map_to"]
    df.drop(["map_to", "siif_recursos_cta_cte"], axis="columns", inplace=True)
    return df
