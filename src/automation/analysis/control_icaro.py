import datetime as dt
from typing import List

import numpy as np
import pandas as pd
from playwright.async_api import async_playwright

from src.automation.analysis.siif_unified import (
    get_siif_comprobantes_gtos_joined,
    get_siif_desc_pres,
    get_siif_rci02_unified_cta_cte,
)
from src.automation.analysis.sscc_unified import get_banco_invico_unified_cta_cte
from src.automation.siif import (
    GtoRpa03g,
    Rcg01Uejp,
    Rf602,
    Rf610,
    Rfondo07tp,
    login,
    logout,
)
from src.constants.endpoints import Endpoints
from src.services import fetch_dataframe, post_request
from src.utils import sanitize_dataframe_for_json


# --------------------------------------------------
async def sync_control_icaro_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:

    async with async_playwright() as p:
        connect_siif = await login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )

        results = []
        # 🔹 RF602
        rf602 = Rf602(siif=connect_siif)
        await rf602.go_to_reports()
        for ej in ejercicios:
            df_clean = await rf602.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF602.value, json_body=json_data)
                results.append(f"RF602 Ejercicio {ej}: {response}")

        # 🔹 RF610
        rf610 = Rf610(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rf610.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RF610.value, json_body=json_data)
                results.append(f"RF610 Ejercicio {ej}: {response}")

        # 🔹 Rcg01Uejp
        rcg01uejp = Rcg01Uejp(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rcg01uejp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RCG01_UEJP.value, json_body=json_data
                )
                results.append(f"Rcg01Uejp Ejercicio {ej}: {response}")

        # 🔹 Rfondo07tp
        rfondo07tp = Rfondo07tp(siif=connect_siif)
        for ej in ejercicios:
            df_clean = await rfondo07tp.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(
                    Endpoints.SIIF_RFONDO07TP.value, json_body=json_data
                )
                results.append(f"Rfondo07tp Ejercicio {ej}: {response}")

        # 🔹 GtoRpa03g
        gto_rpa03g = GtoRpa03g(siif=connect_siif)
        # GRUPOS = get_grupos_partidas_siif_list(
        #     update_trigger=st.session_state.grupos_partidas_siif_uploader_iteration
        # )
        GRUPOS = ["1", "2", "3", "4"]
        for ej in ejercicios:
            for grupo in GRUPOS:
                df_clean = await gto_rpa03g.download_and_process_report(
                    ejercicio=ej, grupo_partida=grupo
                )
                if df_clean is not None and not df_clean.empty:
                    # Send to backend
                    json_data = df_clean.to_dict(orient="records")
                    response = post_request(
                        Endpoints.SIIF_GTO_RPA03G.value, json_body=json_data
                    )
                    results.append(f"GtoRpa03g Ejercicio {ej}: {response}")

        await logout(connect=connect_siif)

        print("✅ SIIF Finalizado")
        return results


# --------------------------------------------------
def get_siif_comprobantes(ejercicio: int = None) -> pd.DataFrame:
    df = get_siif_comprobantes_gtos_joined(ejercicio=ejercicio)
    df = df.loc[
        (df["partida"].isin(["421", "422"]))
        | (
            (df["partida"] == "354")
            & (~df["cuit"].isin(["30500049460", "30632351514", "20231243527"]))
        )
    ]
    return df


# --------------------------------------------------
def compute_control_anual(ejercicios: List[int]) -> None:
    for ejercicio in ejercicios:
        try:
            group_by = ["ejercicio", "estructura", "fuente"]
            # params = params_preparation(
            #     selections=[("ejercicio", [ejercicio])], filtro_avanzado="tipo!=PA6"
            # )
            # trigger = st.session_state.get("icaro_carga_uploader_iteration", 0) + 1
            # icaro = get_icaro_carga(
            #     params=params,
            #     update_trigger=trigger,
            # )
            params = {"limit": 0, "ejercicio": ejercicio, "queryFilter": "tipo!=PA6"}
            icaro = fetch_dataframe(Endpoints.ICARO_CARGA.value, params=params)
            icaro["estructura"] = icaro.actividad + "-" + icaro.partida
            icaro = icaro.groupby(group_by)["importe"].sum()
            icaro = icaro.reset_index(drop=False)
            icaro = icaro.rename(columns={"importe": "ejecucion_icaro"})
            # params = params_preparation(
            #     selections=[("ejercicio", [ejercicio])],
            #     filtro_avanzado="partida~42[1-2]",
            # )
            # trigger = st.session_state.get("siif_rf602_uploader_iteration", 0) + 1
            # siif_obras = get_siif_rf602(
            #     params=params,
            #     update_trigger=trigger,
            # )
            params = {
                "limit": 0,
                "ejercicio": ejercicio,
                "queryFilter": "partida~42[1-2]",
            }
            siif_obras = fetch_dataframe(Endpoints.SIIF_RF602.value, params=params)
            # params = params_preparation(
            #     selections=[("ejercicio", [ejercicio])],
            #     filtro_avanzado="estructura~01-00-00-03-354",
            # )
            # siif_autoseg = get_siif_rf602(
            #     params=params,
            #     update_trigger=trigger + 1,
            # )
            params = {
                "limit": 0,
                "ejercicio": ejercicio,
                "queryFilter": "estructura=01-00-00-03-354",
            }
            siif_autoseg = fetch_dataframe(Endpoints.SIIF_RF602.value, params)
            siif = pd.concat([siif_obras, siif_autoseg], ignore_index=True)
            siif = siif.loc[:, group_by + ["ordenado"]]
            siif = siif.rename(columns={"ordenado": "ejecucion_siif"})
            df = pd.merge(siif, icaro, how="outer", on=group_by, copy=False)
            df = df.fillna(0)
            df["diferencia"] = df["ejecucion_siif"] - df["ejecucion_icaro"]

            df = df.merge(
                get_siif_desc_pres(ejercicio_to=ejercicio),
                how="left",
                on="estructura",
                copy=False,
            )
            df = df.loc[(df["diferencia"] < -0.2) | (df["diferencia"] > 0.2)]
            df = df.reset_index(drop=True)
            df["fuente"] = pd.to_numeric(df["fuente"], errors="coerce")
            df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce")
            json_data = sanitize_dataframe_for_json(df).to_dict(orient="records")
            response = post_request(
                Endpoints.CONTROL_ICARO_ANUAL.value, json_body=json_data
            )
        except Exception as e:
            print(f"Error in compute_control_anual for ejercicio {ejercicio}: {e}")


# --------------------------------------------------
def compute_control_comprobantes(ejercicios: List[int]) -> None:
    for ejercicio in ejercicios:
        try:
            select = [
                "ejercicio",
                "nro_comprobante",
                "fuente",
                "importe",
                "mes",
                "cta_cte",
                "cuit",
                "partida",
            ]
            siif = get_siif_comprobantes(ejercicio=ejercicio)
            siif.loc[
                (siif.clase_reg == "REG") & (siif.nro_fondo.isnull()), "clase_reg"
            ] = "CYO"
            siif = siif.loc[:, select + ["clase_reg"]]
            siif = siif.rename(
                columns={
                    "nro_comprobante": "siif_nro",
                    "clase_reg": "siif_tipo",
                    "fuente": "siif_fuente",
                    "importe": "siif_importe",
                    "mes": "siif_mes",
                    "cta_cte": "siif_cta_cte",
                    "cuit": "siif_cuit",
                    "partida": "siif_partida",
                }
            )
            # params = params_preparation(
            #     selections=[("ejercicio", [ejercicio])], filtro_avanzado="tipo!=PA6"
            # )
            # trigger = st.session_state.get("icaro_carga_uploader_iteration", 0) + 1
            # icaro = get_icaro_carga(
            #     params=params,
            #     update_trigger=trigger,
            # )
            params = {"limit": 0, "ejercicio": ejercicio, "queryFilter": "tipo!=PA6"}
            icaro = fetch_dataframe(Endpoints.ICARO_CARGA.value, params=params)
            icaro = icaro.loc[:, select + ["tipo"]]
            icaro = icaro.rename(
                columns={
                    "nro_comprobante": "icaro_nro",
                    "tipo": "icaro_tipo",
                    "fuente": "icaro_fuente",
                    "importe": "icaro_importe",
                    "mes": "icaro_mes",
                    "cta_cte": "icaro_cta_cte",
                    "cuit": "icaro_cuit",
                    "partida": "icaro_partida",
                }
            )
            df = pd.merge(
                siif,
                icaro,
                how="outer",
                left_on=["ejercicio", "siif_nro"],
                right_on=["ejercicio", "icaro_nro"],
            )
            df["err_nro"] = df.siif_nro != df.icaro_nro
            df["err_tipo"] = df.siif_tipo != df.icaro_tipo
            df["err_mes"] = df.siif_mes != df.icaro_mes
            df["err_partida"] = df.siif_partida != df.icaro_partida
            df["err_fuente"] = df.siif_fuente != df.icaro_fuente
            df["siif_importe"] = df["siif_importe"].fillna(0)
            df["icaro_importe"] = df["icaro_importe"].fillna(0)
            df["err_importe"] = (df.siif_importe - df.icaro_importe).abs()
            df["err_importe"] = df["err_importe"] > 0.1
            df["err_cta_cte"] = df.siif_cta_cte != df.icaro_cta_cte
            df["err_cuit"] = df.siif_cuit != df.icaro_cuit
            df = df.loc[
                (
                    df.err_nro
                    + df.err_tipo
                    + df.err_mes
                    + df.err_partida
                    + df.err_fuente
                    + df.err_importe
                    + df.err_cta_cte
                    + df.err_cuit
                )
                > 0
            ]

            json_data = sanitize_dataframe_for_json(df).to_dict(orient="records")
            response = post_request(
                Endpoints.CONTROL_ICARO_COMPROBANTES.value, json_body=json_data
            )
        except Exception as e:
            print(f"Error in compute_control_recursos: {e}")


# --------------------------------------------------
def generate_siif_comprobantes_recursos(
    ejercicio: int = dt.datetime.now().year,
) -> pd.DataFrame:
    df = get_siif_rci02_unified_cta_cte(
        ejercicio=ejercicio,
    )
    df = df.loc[df["es_verificado"]]
    df = df.loc[~df["es_remanente"]]
    if not df.empty:
        keep = ["MACRO"]
        df.loc[df.glosa.str.contains("|".join(keep)), "cta_cte"] = "Macro"
        df["grupo"] = np.where(
            df["cta_cte"] == "10270",
            "FONAVI",
            np.where(
                df["cta_cte"].isin(["130832-12", "334", "Macro", "Patagonia"]),
                "RECUPEROS",
                "OTROS",
            ),
        )
        df.reset_index(drop=True, inplace=True)
    return df


# --------------------------------------------------
def generate_banco_invico(ejercicio: int = dt.datetime.now().year) -> pd.DataFrame:
    df = get_banco_invico_unified_cta_cte(ejercicio=ejercicio)
    dep_transf_int = ["034", "004"]
    dep_pf = ["214", "215"]
    dep_otros = ["003", "055", "005", "013"]
    dep_cert_neg = ["18"]
    df = df.loc[df["movimiento"] == "DEPOSITO"]
    df = df.loc[
        ~df["cod_imputacion"].isin(dep_transf_int + dep_pf + dep_otros + dep_cert_neg)
    ]
    if not df.empty:
        df["grupo"] = np.where(
            df["cta_cte"] == "10270",
            "FONAVI",
            np.where(
                df["cta_cte"].isin(["130832-12", "334", "Macro", "Patagonia"]),
                "RECUPEROS",
                "OTROS",
            ),
        )
        df.reset_index(drop=True, inplace=True)
    return df
