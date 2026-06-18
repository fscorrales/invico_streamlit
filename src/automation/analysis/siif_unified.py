__all__ = [
    "get_siif_rci02_unified_cta_cte",
    "get_siif_desc_pres",
    "get_siif_comprobantes_gtos_joined",
    "get_siif_comprobantes_gtos_unified_cta_cte",
    "get_siif_comprobantes_honorarios",
]

import datetime as dt
from typing import List, Union

import pandas as pd
import streamlit as st

from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, get_ctas_ctes


# --------------------------------------------------
def get_siif_rci02_unified_cta_cte(ejercicio: int = None) -> pd.DataFrame:
    """
    Get the rci02 data from API.
    """
    params = {"ejercicio": ejercicio} if ejercicio else None
    params["limit"] = 0
    df = fetch_dataframe(Endpoints.SIIF_RCI02.value, params=params)
    # df.reset_index(drop=True, inplace=True)
    ctas_ctes = get_ctas_ctes(
        update_trigger=st.session_state.ctas_ctes_uploader_iteration
    )
    map_to = ctas_ctes.loc[:, ["map_to", "siif_recursos_cta_cte"]]
    df = pd.merge(
        df, map_to, how="left", left_on="cta_cte", right_on="siif_recursos_cta_cte"
    )
    df["cta_cte"] = df["map_to"]
    df.drop(["map_to", "siif_recursos_cta_cte"], axis="columns", inplace=True)
    return df


# --------------------------------------------------
def get_siif_desc_pres(
    ejercicio_to: Union[int, List] = int(dt.datetime.now().year),
) -> pd.DataFrame:
    """
    Get the rf610 data from the repository.
    """

    # trigger = st.session_state.get("siif_desc_pres_uploader_iteration", 0)
    if ejercicio_to is None:
        # df = get_siif_rf610(update_trigger=trigger + 1)
        df = fetch_dataframe(Endpoints.SIIF_RF610.value, params={"limit": 0})
    elif isinstance(ejercicio_to, list):
        # params = params_preparation(
        #     selections=[("ejercicio", ejercicio_to)],
        # )
        # df = get_siif_rf610(params=params, update_trigger=trigger + 1)
        df = fetch_dataframe(
            Endpoints.SIIF_RF610.value,
            params={"limit": 0, "ejercicio": ", ".join(ejercicio_to)},
        )
    else:
        # params = params_preparation(
        #     filtro_avanzado=f"ejercicio<={ejercicio_to}",
        # )
        # df = get_siif_rf610(params=params, update_trigger=trigger + 1)
        df = fetch_dataframe(
            Endpoints.SIIF_RF610.value,
            params={"limit": 0, "queryFilter": f"ejercicio<={ejercicio_to}"},
        )

    df.sort_values(
        by=["ejercicio", "estructura"], inplace=True, ascending=[False, True]
    )
    # Programas únicos
    df_prog = df.loc[:, ["programa", "desc_programa"]]
    df_prog.drop_duplicates(subset=["programa"], inplace=True, keep="first")
    # Subprogramas únicos
    df_subprog = df.loc[:, ["programa", "subprograma", "desc_subprograma"]]
    df_subprog.drop_duplicates(
        subset=["programa", "subprograma"], inplace=True, keep="first"
    )
    # Proyectos únicos
    df_proy = df.loc[:, ["programa", "subprograma", "proyecto", "desc_proyecto"]]
    df_proy.drop_duplicates(
        subset=["programa", "subprograma", "proyecto"], inplace=True, keep="first"
    )
    # Actividades únicos
    # Reemplazar los NaN por una cadena vacía en la columna 'desc_actividad'
    df["desc_actividad"] = df["desc_actividad"].fillna("")

    df_act = df.loc[
        :,
        [
            "estructura",
            "programa",
            "subprograma",
            "proyecto",
            "actividad",
            "desc_actividad",
        ],
    ]

    df_act.drop_duplicates(subset=["estructura"], inplace=True, keep="first")
    # Merge all
    df = df_act.merge(df_prog, how="left", on="programa")
    df = df.merge(df_subprog, how="left", on=["programa", "subprograma"])
    df = df.merge(df_proy, how="left", on=["programa", "subprograma", "proyecto"])
    df["desc_programa"] = df.programa + " - " + df.desc_programa
    df["desc_subprograma"] = df.subprograma + " - " + df.desc_subprograma
    df["desc_proyecto"] = df.proyecto + " - " + df.desc_proyecto
    df["desc_actividad"] = df.actividad + " - " + df.desc_actividad
    df.drop(
        labels=["programa", "subprograma", "proyecto", "actividad"],
        axis=1,
        inplace=True,
    )
    return df


# --------------------------------------------------
def get_siif_comprobantes_gtos_joined(
    ejercicio: int = None, partidas: list = []
) -> pd.DataFrame:
    """
    Join gto_rpa03g (gtos_gpo_part) with rcg01_uejp (gtos)
    """
    params = {"limit": 0}
    if ejercicio is None:
        docs_gtos_gpo_part = fetch_dataframe(
            Endpoints.SIIF_GTO_RPA03G.value, params=params
        )
        docs_gtos = fetch_dataframe(Endpoints.SIIF_RCG01_UEJP.value, params=params)
    else:
        params["ejercicio"] = ejercicio
        docs_gtos = fetch_dataframe(Endpoints.SIIF_RCG01_UEJP.value, params=params)
        if len(partidas) > 0:
            pass
            # params["queryFilter"] = f"partidas={','.join(partidas)}"
            # params.update(
            #     {
            #         "queryFilter": f"partidas={','.join(partidas)}",
            #     }
            # )
        docs_gtos_gpo_part = fetch_dataframe(
            Endpoints.SIIF_GTO_RPA03G.value, params=params
        )
    df_gtos_gpo_part = pd.DataFrame(docs_gtos_gpo_part)
    df_gtos = pd.DataFrame(docs_gtos)
    df_gtos_filtered = df_gtos[
        [
            "nro_comprobante",
            "nro_fondo",
            "fuente",
            "cta_cte",
            "cuit",
            "clase_reg",
            "clase_mod",
            "clase_gto",
            "es_comprometido",
            "es_verificado",
            "es_aprobado",
            "es_pagado",
        ]
    ]
    df = pd.merge(
        left=df_gtos_gpo_part,
        right=df_gtos_filtered,
        on=["nro_comprobante"],
        how="left",
    )
    return df


# --------------------------------------------------
def get_siif_comprobantes_gtos_unified_cta_cte(
    ejercicio: int = None, partidas: list = []
) -> pd.DataFrame:
    """
    Get the comprobantes gtos joined data from the repository.
    """
    df = get_siif_comprobantes_gtos_joined(ejercicio=ejercicio, partidas=partidas)
    if not df.empty:
        ctas_ctes = fetch_dataframe(Endpoints.CTAS_CTES.value, params={"limit": 0})
        map_to = ctas_ctes.loc[:, ["map_to", "siif_gastos_cta_cte"]]
        df = pd.merge(
            df,
            map_to,
            how="left",
            left_on="cta_cte",
            right_on="siif_gastos_cta_cte",
        )
        df["cta_cte"] = df["map_to"]
        df.drop(["map_to", "siif_gastos_cta_cte"], axis="columns", inplace=True)
        # logger.info(f"df.shape: {df.shape} - df.head: {df.head()}")
    return df


# --------------------------------------------------
def get_siif_comprobantes_honorarios(
    ejercicio: str = None,
) -> pd.DataFrame:
    """
    Get comprobantes honorarios factureros data from the repository.
    """
    df = get_siif_comprobantes_gtos_unified_cta_cte(ejercicio=ejercicio)
    df = df.loc[df["cuit"] == "30632351514"]
    df = df.loc[df["grupo"] == "300"]
    df = df.loc[df["partida"] != "384"]
    df = df.loc[df["cta_cte"].isin(["130832-05", "130832-07"])]
    keep = ["HONOR", "RECON", "LOC"]
    df = df.loc[df.glosa.str.contains("|".join(keep))]
    df = df.reset_index(drop=True)
    return df
