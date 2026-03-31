import os
import subprocess
import sys
from typing import List

import numpy as np
import pandas as pd
from playwright.async_api import async_playwright

from src.automation.analysis.siif_unified import get_siif_rci02_unified_cta_cte
from src.automation.analysis.sscc_unified import get_banco_invico_unified_cta_cte
from src.automation.siif.rci02 import Rci02
from src.constants.endpoints import Endpoints
from src.services.api_client import post_request


# --------------------------------------------------
def sync_control_recursos_from_sscc(
    sscc_username: str, sscc_password: str, token: str, ejercicios: List[int]
) -> None:

    modulo_runner = "src.automation.sscc.banco_invico_runner"
    ejercicios_str = ",".join(map(str, ejercicios))

    # Aseguramos que el PYTHONPATH sea la raíz actual
    env = os.environ.copy()
    env["PYTHONPATH"] = os.getcwd()

    process_sscc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            modulo_runner,
            sscc_username,
            sscc_password,
            token,
            ejercicios_str,
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        env=env,
    )

    # Esperamos que el SSCC termine antes de devolver el control a Streamlit
    process_sscc.wait()
    print("✅ SSCC Finalizado.")


# --------------------------------------------------
async def sync_control_recursos_from_siif(
    siif_username: str, siif_password: str, ejercicios: List[int]
) -> List[str]:

    async with async_playwright() as p:
        siif = Rci02()
        await siif.login(
            username=siif_username,
            password=siif_password,
            playwright=p,
            headless=False,
        )
        await siif.go_to_reports()

        results = []
        for ej in ejercicios:
            df_clean = await siif.download_and_process_report(ejercicio=ej)
            if df_clean is not None and not df_clean.empty:
                # Send to backend
                json_data = df_clean.to_dict(orient="records")
                response = post_request(Endpoints.SIIF_RCI02.value, json_body=json_data)
                results.append(f"Ejercicio {ej}: {response}")

        await siif.logout()

        print("✅ SIIF Finalizado")
        return results


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
def generate_siif_comprobantes_recursos(ejercicio: int = None) -> pd.DataFrame:
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
def generate_banco_invico(ejercicio: int = None) -> pd.DataFrame:
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
