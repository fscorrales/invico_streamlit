import datetime as dt
from typing import List

import numpy as np
import pandas as pd
import streamlit as st
from playwright.async_api import async_playwright

from src.automation.analysis.siif_unified import get_siif_rci02_unified_cta_cte
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
from src.services import (
    get_grupos_partidas_siif_list,
    post_request,
)


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
        GRUPOS = get_grupos_partidas_siif_list(
            update_trigger=st.session_state.grupos_partidas_siif_uploader_iteration
        )
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


# # --------------------------------------------------
# def sync_control_icaros_from_icaro() -> None:
#     # Capturamos el filtro del session_state (que el fragmento actualizó)
#     trigger = st.session_state.get("icaro_carga_uploader_iteration", 0)
#     try:
#         get_icaro_carga(
#             update_trigger=trigger
#             + 1,  # Incrementamos el trigger para forzar la actualización en get_icaro_carga
#         )
#         print("✅ Sync ICARO Carga Finalizado.")
#     except APIConnectionError as e:
#         st.error(f"⚠️ Error de conexión: {e}")
#     except APIResponseError as e:
#         st.error(f"⚠️ Error de API: {e}")


# --------------------------------------------------
def compute_control_recursos(ejercicios: List[int]) -> None:
    for ejercicio in ejercicios:
        try:
            group_by = ["ejercicio", "mes", "cta_cte", "grupo"]
            siif = generate_siif_comprobantes_recursos(ejercicio=int(ejercicio))
            siif = siif.loc[~siif["es_invico"]]
            siif = siif.loc[~siif["es_remanente"]]
            siif = siif.groupby(group_by)["importe"].sum()
            siif = siif.reset_index(drop=False)
            siif = siif.rename(columns={"importe": "recursos_siif"})
            sscc = generate_banco_invico(ejercicio=int(ejercicio))
            sscc = sscc.groupby(group_by)["importe"].sum()
            sscc = sscc.reset_index(drop=False)
            sscc = sscc.rename(columns={"importe": "depositos_banco"})
            df = pd.merge(siif, sscc, how="outer")
            df = df.fillna(0)
            json_data = df.to_dict(orient="records")
            response = post_request(
                Endpoints.CONTROL_RECURSOS.value, json_body=json_data
            )
            # results.append(f"Ejercicio {ej}: {response}")

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
